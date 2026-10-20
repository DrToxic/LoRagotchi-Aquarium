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
from .protocol import StreamFrames, frame, bridge_command_allowed
from .transport import open_transport, recv_exact
from .meshcore_protocol import BRIDGE_CAPS


def authenticate(sock, token):
    sock.settimeout(4)
    challenge=secrets.token_bytes(32)
    sock.sendall(b"LRXB"+challenge)
    proof=recv_exact(sock,32)
    okay=hmac.compare_digest(proof,hmac.new(token,challenge,hashlib.sha256).digest())
    sock.sendall(b"OK" if okay else b"NO")
    if not okay:raise PermissionError("Bridge authentication failed")
    sock.settimeout(.05)


def forward_command(sock,radio,payload,radio_control=False):
    if payload==BRIDGE_CAPS:
        sock.sendall(frame(BRIDGE_CAPS+bytes([int(radio_control)]),b'>'))
    elif bridge_command_allowed(payload,radio_control):radio.send(payload)
    else:
        # An explicit rejection keeps the LRX stream alive; never forward an
        # unapproved command or infer permission from possession of a token.
        sock.sendall(frame(b'\x01\x06',b'>'))


def public_response(payload):
    if payload[:1]==b'\x12' and len(payload)==50:
        # Preserve slot-identity changes without forwarding channel secrets.
        key=payload[34:]
        return payload[:34]+(hashlib.sha256(key).digest()[:16] if any(key) else bytes(16))
    if payload[:1]==b'\x0d' and len(payload)>=8:
        return payload[:4]+bytes(4)+payload[8:]  # no BLE PIN over LAN
    return payload


def relay(sock,radio,token,stop=None,radio_control=False):
    authenticate(sock,token)
    parser=StreamFrames(b"<")
    while stop is None or not stop.is_set():
        try:
            data=sock.recv(1024)
            if not data:return
            for payload in parser.feed(data):
                forward_command(sock,radio,payload,radio_control)
        except socket.timeout:pass
        try:sock.sendall(frame(public_response(radio.receive(.05)),b">"))
        except TimeoutError:pass


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radio",help="serial:/dev/ttyUSB0 or ble:ADDRESS")
    parser.add_argument("--bind",default="127.0.0.1")
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--token-file",type=Path,required=True)
    parser.add_argument("--init-token",action="store_true")
    parser.add_argument("--radio-control",action="store_true",help="Allow chat sends and supported radio settings for authenticated clients (trusted LAN/SSH tunnel only)")
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
                                forward_command(sock,radio,payload,args.radio_control)
                        except socket.timeout:pass
                        try:sock.sendall(frame(public_response(radio.receive(.05)),b">"))
                        except TimeoutError:pass
                except (ConnectionError,TimeoutError,OSError,PermissionError) as exc:
                    print(f"Bridge connection ended: {type(exc).__name__}")
                finally:
                    if radio:radio.close()

if __name__=="__main__":main()
