"""Single-consumer authenticated LAN bridge to an actual serial/BLE RX radio.

No on-radio Wi-Fi claim. Default bind is loopback. The HMAC handshake authenticates
but does not encrypt: use a trusted LAN or an SSH tunnel, not an exposed WAN port.
"""
import argparse
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import socket
import time
from .protocol import MAGIC, StreamFrames, frame
from .transport import open_transport, recv_exact


def authenticate(sock, token):
    sock.settimeout(4)
    challenge=secrets.token_bytes(32)
    sock.sendall(b"LRXB"+challenge)
    proof=recv_exact(sock,32)
    okay=hmac.compare_digest(proof,hmac.new(token,challenge,hashlib.sha256).digest())
    sock.sendall(b"OK" if okay else b"NO")
    if not okay:raise PermissionError("Bridge authentication failed")
    sock.settimeout(.05)


def relay(sock,radio,token,stop=None):
    authenticate(sock,token)
    parser=StreamFrames(b"<")
    while stop is None or not stop.is_set():
        try:
            data=sock.recv(1024)
            if not data:return
            for payload in parser.feed(data):
                # Read-only ordinary inbox plus the RX extension; never arbitrary
                # companion commands (private keys, RF settings, reboot, etc.).
                if payload!=b"\x0a" and not payload.startswith(MAGIC):
                    raise PermissionError("Command is not permitted through this bridge")
                radio.send(payload)
        except socket.timeout:pass
        try:sock.sendall(frame(radio.receive(.05),b">"))
        except TimeoutError:pass


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radio",help="serial:/dev/ttyUSB0 or ble:ADDRESS")
    parser.add_argument("--bind",default="127.0.0.1")
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--token-file",type=Path,required=True)
    parser.add_argument("--init-token",action="store_true")
    args=parser.parse_args()
    if args.init_token:
        args.token_file.parent.mkdir(parents=True,exist_ok=True)
        fd=os.open(args.token_file,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"wb") as f:f.write(secrets.token_bytes(32))
        print(f"Created bridge token file: {args.token_file}")
        return
    if not args.radio or not args.radio.startswith(("serial:","ble:")):
        parser.error("--radio must identify a real serial or BLE RX connection")
    token=args.token_file.read_bytes()
    if len(token)!=32:parser.error("Token file must contain 32 random bytes")
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        server.bind((args.bind,args.port));server.listen(1)
        print(f"RX bridge listening on {args.bind}:{args.port}; one consumer; authenticated, not encrypted")
        while True:
            sock,_=server.accept()
            with sock:
                radio=None
                try:
                    # Only acquire the radio for a successful authenticated client.
                    authenticate(sock,token)
                    radio=open_transport(args.radio)
                    parser_stream=StreamFrames(b"<")
                    while True:
                        try:
                            data=sock.recv(1024)
                            if not data:break
                            for payload in parser_stream.feed(data):
                                if payload!=b"\x0a" and not payload.startswith(MAGIC):raise PermissionError("Command not allowed")
                                radio.send(payload)
                        except socket.timeout:pass
                        try:sock.sendall(frame(radio.receive(.05),b">"))
                        except TimeoutError:pass
                except (ConnectionError,TimeoutError,OSError,PermissionError) as exc:
                    print(f"Bridge connection ended: {type(exc).__name__}")
                finally:
                    if radio:radio.close()

if __name__=="__main__":main()
