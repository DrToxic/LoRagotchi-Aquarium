import os
import select
import socket
import threading
import time
import pytest
from tank.bridge import relay,authenticate
from tank.protocol import StreamFrames,frame
from tank.transport import SerialTransport,TCPTransport
from tank.simulator import SimulatedRadio
from tank.client import Client
from tank.store import Store


def test_tcp_loopback_authenticated_bridge_real_io(tmp_path):
    token=b'x'*32
    radio=SimulatedRadio(3,{3:'#loragotchi-DX'},
                         [b'\x08\x03\xff\0'+bytes(4)+b'Nickel: Hello via bridge'])
    stop=threading.Event();errors=[]
    server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1)
    def run():
        sock,_=server.accept()
        with sock:
            try:relay(sock,radio,token,stop)
            except (ConnectionError,BrokenPipeError,ConnectionResetError):pass
            except Exception as exc:errors.append(exc)
    worker=threading.Thread(target=run);worker.start()
    transport=TCPTransport('127.0.0.1',server.getsockname()[1],token)
    store=Store(tmp_path/'tcp.sqlite');client=Client(transport,store,token=123);client.connect()
    while client.poll():pass
    client.poll_messages();assert len(store.roster())==3
    assert client.messages[-1]['channel_name']=='#loragotchi-DX'
    assert client.messages[-1]['text']=='Nickel: Hello via bridge'
    client.close();stop.set();worker.join(3);server.close();store.close()
    assert not errors and not worker.is_alive()


def test_bridge_rejects_wrong_token():
    left,right=socket.socketpair();errors=[]
    def auth():
        try:authenticate(left,b'a'*32)
        except PermissionError:errors.append('rejected')
        finally:left.close()
    t=threading.Thread(target=auth);t.start()
    assert len(right.recv(36))==36
    right.sendall(b'z'*32);assert right.recv(2)==b'NO';right.close();t.join()
    assert errors==['rejected']

@pytest.mark.skipif(os.name!='posix',reason='POSIX pseudoterminal integration test')
def test_serial_pseudoterminal_real_io(tmp_path):
    import pty
    master,slave=pty.openpty();port=os.ttyname(slave);stop=threading.Event()
    radio=SimulatedRadio(2,{5:'#loragotchi-DX'},
                         [b'\x08\x05\xff\0'+bytes(4)+b'Nickel: Hello via USB'])
    transport=SerialTransport(port);parser=StreamFrames(b'<');errors=[]
    def peer():
        try:
            while not stop.is_set():
                ready,_,_=select.select([master],[],[],.1)
                if not ready:continue
                for payload in parser.feed(os.read(master,1024)):
                    radio.send(payload);wire=frame(radio.receive(),b'>')
                    # Actual serial I/O, deliberately split each response header.
                    os.write(master,wire[:2]);os.write(master,wire[2:])
        except OSError:
            if not stop.is_set():errors.append('unexpected pty close')
    t=threading.Thread(target=peer);t.start()
    store=Store(tmp_path/'serial.sqlite');client=Client(transport,store,token=456);client.connect()
    while client.poll():pass
    assert len(store.roster())==2
    client.poll_messages()
    assert client.messages[-1]['channel_name']=='#loragotchi-DX'
    assert client.messages[-1]['text']=='Nickel: Hello via USB'
    client.close();stop.set();t.join(2);os.close(master);os.close(slave);store.close()
    assert not errors and not t.is_alive()


def test_windows_serial_does_not_request_unsupported_nonexclusive_mode(monkeypatch):
    import types,serial
    import tank.transport as adapters
    captured={}
    def fake_serial(*args,**kwargs):captured.update(kwargs);return object()
    monkeypatch.setattr(adapters,'os',types.SimpleNamespace(name='nt'))
    monkeypatch.setattr(serial,'Serial',fake_serial)
    SerialTransport('COM4')
    # serialwin32 rejects False; None keeps its inherently exclusive behavior.
    assert captured['exclusive'] is None


def test_tcp_incomplete_handshake_closes_socket(monkeypatch):
    class BrokenSocket:
        closed=False
        def settimeout(self,seconds):pass
        def recv(self,size):return b''
        def close(self):self.closed=True
    sock=BrokenSocket()
    monkeypatch.setattr(socket,'create_connection',lambda *a,**k:sock)
    with pytest.raises(ConnectionError):TCPTransport('127.0.0.1',1234,b'x'*32)
    assert sock.closed


def test_ble_connect_cancellation_cleans_private_loop(monkeypatch):
    import asyncio
    import bleak
    from tank.transport import BLETransport
    clients=[];loops=[]
    new_loop=asyncio.new_event_loop
    def loop_factory():
        loop=new_loop();loops.append(loop);return loop
    class SlowBLE:
        disconnected=False
        def __init__(self,*args,**kw):clients.append(self)
        async def connect(self):await asyncio.sleep(20)
        async def disconnect(self):self.disconnected=True
    monkeypatch.setattr(bleak,'BleakClient',SlowBLE)
    monkeypatch.setattr(asyncio,'new_event_loop',loop_factory)
    started=time.monotonic()
    with pytest.raises(ConnectionAbortedError):
        BLETransport('AA:BB:CC:DD:EE:FF',cancel=lambda:time.monotonic()-started>.15)
    assert time.monotonic()-started<2
    assert clients[0].disconnected and loops[0].is_closed()
    assert not asyncio.all_tasks(loops[0])
