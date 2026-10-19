"""Real serial, TCP stream and BLE GATT adapters. No adapter writes radio DMs."""
import asyncio
import collections
import concurrent.futures
import contextlib
import hashlib
import hmac
import os
import queue
import socket
import threading
import time
from .protocol import StreamFrames, frame, ProtocolError

class StreamTransport:
    supports_mesh_messages = True
    def __init__(self):
        self.parser = StreamFrames()
        self.pending = collections.deque()

    def receive(self, timeout=2):
        end = time.monotonic()+timeout
        while time.monotonic()<end:
            if self.pending:
                return self.pending.popleft()
            data=self.read()
            if data:
                self.pending.extend(self.parser.feed(data))
        raise TimeoutError("RX response timeout")

    def send(self, payload):
        self.write(frame(payload))

class SerialTransport(StreamTransport):
    def __init__(self, port, baud=115200):
        super().__init__()
        import serial
        self.serial=serial.Serial(port, baud, timeout=.1, write_timeout=2, exclusive=(True if os.name=="posix" else None))
    def read(self): return self.serial.read(max(1,min(self.serial.in_waiting,1024)))
    def write(self,data): self.serial.write(data)
    def close(self): self.serial.close()


def recv_exact(sock, size):
    data=bytearray()
    while len(data)<size:
        block=sock.recv(size-len(data))
        if not block: raise ConnectionError("Connection closed")
        data.extend(block)
    return bytes(data)

class TCPTransport(StreamTransport):
    def __init__(self, host, port, token=None):
        super().__init__()
        self.socket=socket.create_connection((host,port),timeout=3)
        try:
            self.socket.settimeout(3)
            challenge=recv_exact(self.socket,36)
            if challenge[:4]!=b"LRXB":raise ProtocolError("Not an authenticated LRX bridge")
            if token is None:raise ProtocolError("Bridge token required")
            proof=hmac.new(token,challenge[4:],hashlib.sha256).digest()
            self.socket.sendall(proof)
            if recv_exact(self.socket,2)!=b"OK":raise PermissionError("Bridge authentication rejected")
            self.socket.settimeout(.1)
        except BaseException:
            self.socket.close();raise
    def read(self):
        try:
            data=self.socket.recv(1024)
            if not data: raise ConnectionError("Bridge disconnected")
            return data
        except socket.timeout:return b""
    def write(self,data):self.socket.sendall(data)
    def close(self):self.socket.close()

class BLETransport:
    """Nordic UART service: each write/notification is one companion frame.

    LRX events use application-level pull fragments <=20 bytes, not a stream
    chopped across writes. Stock mesh message notifications can still require
    a negotiated larger MTU; never concatenate their packets speculatively.
    """
    RX="6e400002-b5a3-f393-e0a9-e50e24dcca9e"
    TX="6e400003-b5a3-f393-e0a9-e50e24dcca9e"
    def __init__(self,address,cancel=None):
        from bleak import BleakClient
        self.events=queue.Queue(maxsize=256)
        self.loop=asyncio.new_event_loop()
        self.thread=threading.Thread(target=self.loop.run_forever,daemon=True)
        self.thread.start()
        self.client=None;self.closed=False
        async def connect():
            self.client=BleakClient(address,timeout=20)
            await self.client.connect()
            self.supports_mesh_messages=self.client.mtu_size>=179
            def notify(_,data):
                try:self.events.put_nowait(bytes(data))
                except queue.Full:pass  # request timeout triggers a durable replay
            await self.client.start_notify(self.TX,notify)
        future=asyncio.run_coroutine_threadsafe(connect(),self.loop)
        deadline=time.monotonic()+25
        try:
            while True:
                if cancel and cancel():raise ConnectionAbortedError('Connection cancelled')
                if time.monotonic()>deadline:raise TimeoutError('Bluetooth connection timed out')
                try:future.result(.1);break
                except concurrent.futures.TimeoutError:
                    if future.done():raise
        except Exception:
            future.cancel()
            with contextlib.suppress(Exception):self.close()
            raise
    def send(self,payload):
        if len(payload)>20: raise ProtocolError("LRX writes must fit default BLE MTU")
        asyncio.run_coroutine_threadsafe(self.client.write_gatt_char(self.RX,payload,response=True),self.loop).result(5)
    def receive(self,timeout=2):
        try:return self.events.get(timeout=timeout)
        except queue.Empty:raise TimeoutError("BLE response timeout") from None
    def close(self):
        if self.closed:return
        self.closed=True
        async def cleanup():
            if self.client is not None:await self.client.disconnect()
        future=asyncio.run_coroutine_threadsafe(cleanup(),self.loop)
        try:future.result(5)
        finally:
            future.cancel()
            self.loop.call_soon_threadsafe(self.loop.stop);self.thread.join(2)
            if not self.thread.is_alive():self.loop.close()


def open_transport(uri,token=None,cancel=None):
    if uri.startswith("serial:"):return SerialTransport(uri[7:])
    if uri.startswith("ble:"):return BLETransport(uri[4:],cancel)
    if uri.startswith("tcp:"):
        host,port=uri[4:].rsplit(":",1)
        return TCPTransport(host.strip('[]'),int(port),token)
    raise ValueError("Connection must be serial:PORT, ble:ADDRESS or tcp:HOST:PORT")
