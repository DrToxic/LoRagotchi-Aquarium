"""LRX-only endpoint negotiation; stock companion sessions stay unchanged."""
import socket
import threading
import pytest
from tank.client import Client
from tank.radio import RadioSession
from tank.protocol import MAGIC
from tank.simulator import SimulatedRadio
from tank.store import Store
from tank.bridge import relay
from tank.transport import TCPTransport


class Repeater(SimulatedRadio):
    def __init__(self, links):
        super().__init__(2)
        self.links=links
    def send(self, payload):
        assert payload.startswith(MAGIC), 'An LRX-only repeater must never receive companion commands'
        super().send(payload)
        if payload[4]==0:
            result=bytearray(self.replies.get_nowait())
            result[7]=self.links | 0x80
            self.replies.put(bytes(result))


@pytest.mark.parametrize('link',[1,2,4])
def test_repeater_lrx_only_keeps_durable_intake_and_disables_companion(tmp_path,link):
    transport=Repeater(link);store=Store(tmp_path/'tank.sqlite');client=Client(transport,store,token=3)
    try:
        caps=client.connect()
        assert caps['transports']==link|0x80 and client.lrx_only
        events=[];radio=RadioSession(client,events.append,network=link==4)
        assert not radio.supported and not radio.writable
        assert events[-1]['lrx_only']
        before=len(transport.commands);client.poll_messages();radio.step()
        assert len(transport.commands)==before
        with pytest.raises(ValueError,match='Repeater tank'):radio.schedule_refresh()
        with pytest.raises(ValueError,match='intake only'):radio.request(b'\x16\x0e',(13,))
        while client.poll():pass
        assert len(store.roster())==2
        # Upload ACKs still follow Store.save, exactly as for ordinary RX.
        assert transport.acked==set(transport.events)
    finally:client.close();store.close()


def test_repeater_uses_existing_authenticated_tcp_contract(tmp_path):
    radio=Repeater(4);token=b'k'*32;stop=threading.Event();errors=[]
    server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1)
    def peer():
        sock,_=server.accept()
        with sock:
            try:relay(sock,radio,token,stop)
            except (ConnectionError,OSError):pass
            except Exception as exc:errors.append(exc)
    worker=threading.Thread(target=peer);worker.start()
    store=Store(tmp_path/'tcp.sqlite')
    transport=TCPTransport('127.0.0.1',server.getsockname()[1],token)
    client=Client(transport,store,token=4)
    try:
        client.connect();session=RadioSession(client,lambda event:None,network=True)
        client.poll_messages();assert not session.supported
        while client.poll():pass
        assert len(store.roster())==2
    finally:
        client.close();store.close();stop.set();worker.join(3);server.close()
    assert not errors and not worker.is_alive()
