"""UI-to-worker behavior with actual protocol/store and controlled radio peers."""
from dataclasses import replace
import json
from pathlib import Path
import queue
import socket
import threading
import time
from types import SimpleNamespace
import pytest
from tank.connection import ConnectionProfile
from tank.service import Service
from tank.simulator import SimulatedRadio
from tank.store import Store
from tank.bridge import relay


def args(tmp_path, **changes):
    return SimpleNamespace(**(dict(database=tmp_path/'demo.sqlite',live_database=tmp_path/'live.sqlite',
                                   session='test',demo=8,replay=None,connect=None,token_file=None,
                                   settings=tmp_path/'settings.json')|changes))


def wait_event(service, predicate, timeout=6):
    deadline=time.monotonic()+timeout
    seen=[]
    while time.monotonic()<deadline:
        try:event=service.events.get(timeout=.1)
        except queue.Empty:continue
        seen.append(event)
        if isinstance(event,dict) and predicate(event):return event
    raise AssertionError(f'Expected service event; observed {seen}')


def state(service,name):return wait_event(service,lambda e:e.get('state')==name)


def test_profile_validation_and_remembered_details_not_token_bytes(tmp_path):
    token=tmp_path/'pair.token';token.write_bytes(b'x'*32)
    p=ConnectionProfile(transport='tcp',host='[::1]',port='8765',token_file=str(token))
    assert p.uri()=='tcp:::1:8765' and p.token()==b'x'*32
    path=tmp_path/'prefs.json';p.save(path)
    assert ConnectionProfile.load(path)==p and 'x'*32 not in path.read_text()
    assert ConnectionProfile.from_uri('serial:COM4').uri()=='serial:COM4'
    for invalid in (replace(p,port='0'),replace(p,port='bad'),replace(p,host='http://radio'),
                    replace(p,token_file=''),ConnectionProfile(),ConnectionProfile(transport='ble')):
        with pytest.raises(ValueError):invalid.uri()
    path.write_text('{broken');assert ConnectionProfile.load(path)==ConnectionProfile()


def test_ui_connect_real_tcp_bridge_switches_store_and_disconnect_retains_fish(tmp_path):
    token=tmp_path/'pair.token';token.write_bytes(b'x'*32)
    radio=SimulatedRadio(2);stop=threading.Event();errors=[]
    server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1);server.settimeout(8)
    def peer():
        try:
            sock,_=server.accept()
            with sock:relay(sock,radio,b'x'*32,stop)
        except (ConnectionError,BrokenPipeError,ConnectionResetError):pass
        except Exception as exc:errors.append(exc)
    thread=threading.Thread(target=peer);thread.start()
    service=Service(args(tmp_path))
    try:
        demo=wait_event(service,lambda e:e.get('kind')=='roster');assert len(demo['fish'])==8
        service.connect(ConnectionProfile(transport='tcp',host='127.0.0.1',port=str(server.getsockname()[1]),token_file=str(token)))
        live=wait_event(service,lambda e:e.get('kind')=='roster' and e.get('mode')=='live');assert not live['fish']
        state(service,'connected')
        wait_event(service,lambda e:e.get('kind')=='roster' and len(e['fish'])==2)
        service.disconnect();state(service,'idle')
        for path,count in ((tmp_path/'demo.sqlite',8),(tmp_path/'live.sqlite',2)):
            db=Store(path,'test');assert len(db.roster())==count;db.close()
        assert {1,3} <= radio.acked  # Snapshot IDs; return-status events are also ACKed.
    finally:
        service.close();stop.set();thread.join(4);server.close()
    assert not service.thread.is_alive() and not thread.is_alive() and not errors


def test_retry_then_disconnect_stops_retries_and_reconnect_deduplicates(tmp_path,monkeypatch):
    radio=SimulatedRadio(1);calls=[]
    def open_radio(uri,token,cancel=None):
        calls.append(threading.get_ident())
        if len(calls)==1:raise OSError('radio unplugged')
        return radio
    monkeypatch.setattr('tank.service.open_transport',open_radio)
    service=Service(args(tmp_path))
    try:
        wait_event(service,lambda e:e.get('kind')=='roster')
        service.connect(ConnectionProfile(serial_port='COM4'));state(service,'retrying');state(service,'connected')
        wait_event(service,lambda e:e.get('kind')=='roster' and len(e['fish'])==1)
        service.disconnect();state(service,'idle');count=len(calls)
        time.sleep(.3);assert len(calls)==count and radio.lease is None
        service.connect(ConnectionProfile(serial_port='COM4'));state(service,'connected')
        service.disconnect();state(service,'idle')
        db=Store(tmp_path/'live.sqlite','test');assert len(db.roster())==1;db.close()
        assert all(t!=threading.get_ident() for t in calls)
    finally:service.close()


def test_cancel_pending_open_does_not_handshake_or_save(tmp_path,monkeypatch):
    entered=threading.Event();release=threading.Event();radio=SimulatedRadio(1)
    def opening(uri,token,cancel=None):
        entered.set();release.wait(3);return radio
    monkeypatch.setattr('tank.service.open_transport',opening)
    service=Service(args(tmp_path))
    try:
        wait_event(service,lambda e:e.get('kind')=='roster')
        service.connect(ConnectionProfile(serial_port='COM4'));assert entered.wait(2)
        service.disconnect();release.set();state(service,'idle')
        assert radio.lease is None and not radio.acked
        db=Store(tmp_path/'live.sqlite','test');assert not db.roster();db.close()
    finally:release.set();service.close()


def test_bad_bridge_token_and_storage_failure_preserve_demo(tmp_path,monkeypatch):
    service=Service(args(tmp_path));opened=[]
    monkeypatch.setattr('tank.service.open_transport',lambda *a,**kw:opened.append(True))
    try:
        wait_event(service,lambda e:e.get('kind')=='roster')
        bad=tmp_path/'bad.token';bad.write_bytes(b'not32bytes')
        service.connect(ConnectionProfile(transport='tcp',token_file=str(bad)))
        assert '32 bytes' in state(service,'error')['text']
        # A file where the live database's parent directory should be.
        obstruction=tmp_path/'blocked';obstruction.write_text('keep')
        service.args.live_database=obstruction/'live.sqlite'
        service.connect(ConnectionProfile(serial_port='COM4'));state(service,'error')
        db=Store(tmp_path/'demo.sqlite','test');assert len(db.roster())==8;db.close()
        assert not (tmp_path/'live.sqlite').exists() and not opened
    finally:service.close()


def test_discovery_is_on_worker_and_does_not_open_radio(tmp_path,monkeypatch):
    threads=[]
    def discover(kind):threads.append(threading.get_ident());return [('COM7','COM7 · USB radio')]
    monkeypatch.setattr('tank.service.discover',discover)
    monkeypatch.setattr('tank.service.open_transport',lambda *a,**k:pytest.fail('scan must not connect'))
    service=Service(args(tmp_path))
    try:
        service.commands.put(('scan','serial'))
        event=wait_event(service,lambda e:e.get('kind')=='devices')
        assert event['devices'][0][0]=='COM7' and threads!=[threading.get_ident()]
    finally:service.close()


def test_failed_capability_handshake_closes_adapter_and_can_retry(tmp_path,monkeypatch):
    class StockRadio:
        supports_mesh_messages=False
        closed=False
        def send(self,payload):pass
        def receive(self,timeout=2):raise TimeoutError('RX extension not available')
        def close(self):self.closed=True
    radio=StockRadio()
    monkeypatch.setattr('tank.service.open_transport',lambda *a,**k:radio)
    service=Service(args(tmp_path))
    try:
        service.connect(ConnectionProfile(serial_port='COM7'))
        assert 'RX extension' in state(service,'retrying')['text']
        assert radio.closed
        service.disconnect();state(service,'idle')
    finally:service.close()


def test_startup_storage_error_is_terminal_and_explained(tmp_path):
    obstruction=tmp_path/'blocked';obstruction.write_text('keep')
    service=Service(args(tmp_path,database=obstruction/'demo.sqlite'))
    try:
        event=state(service,'fatal')
        assert 'restart' in event['text']
        service.thread.join(1);assert not service.thread.is_alive()
    finally:service.close()


def test_explicit_cli_live_database_is_preserved(tmp_path,monkeypatch):
    radio=SimulatedRadio(1)
    monkeypatch.setattr('tank.service.open_transport',lambda *a,**k:radio)
    chosen=tmp_path/'chosen.sqlite'
    service=Service(args(tmp_path,demo=None,database=chosen,connect='serial:COM7'))
    try:
        state(service,'connected')
        wait_event(service,lambda e:e.get('kind')=='roster' and len(e['fish'])==1)
        service.disconnect();state(service,'idle')
        db=Store(chosen,'test');assert len(db.roster())==1;db.close()
        assert not (tmp_path/'live.sqlite').exists()
    finally:service.close()


def test_radio_operations_share_worker_and_stale_ui_sends_do_not_cross_reconnect(tmp_path,monkeypatch):
    from tools.radio_peer import MeshRadio,PEER
    radio=MeshRadio();threads=[];opens=[]
    original_send=radio.send
    def send(payload):threads.append(threading.get_ident());original_send(payload)
    radio.send=send
    def opening(*a,**kw):opens.append(threading.get_ident());return radio
    monkeypatch.setattr('tank.service.open_transport',opening)
    service=Service(args(tmp_path))
    try:
        wait_event(service,lambda e:e.get('kind')=='roster')
        service.connect(ConnectionProfile(serial_port='COM7'));state(service,'connected')
        service.radio_request('refresh')
        wait_event(service,lambda e:e.get('kind')=='radio_state' and e.get('loaded'))
        mid=service.radio_request('send',route='direct',target=PEER,text='Shared owner test')
        result=wait_event(service,lambda e:e.get('kind')=='radio_result' and e.get('id')==mid)
        assert result['ok'] and radio.tx_count==1
        # A queued old-generation operation can never be issued to a new radio.
        stale=service.radio_request('send',route='direct',target=PEER,text='Never resend after connection change')
        service.disconnect()
        result=wait_event(service,lambda e:e.get('kind')=='radio_result' and e.get('id')==stale)
        assert not result['ok']
        state(service,'idle')
        service.radio_request('history',conversation='dm:'+PEER[:12])
        history=wait_event(service,lambda e:e.get('kind')=='radio_history')
        assert history['messages'][-1]['text']=='Shared owner test'
        service.connect(ConnectionProfile(serial_port='COM7'));state(service,'connected')
        assert radio.tx_count==1 and len(opens)==2
        assert len(set(threads+opens))==1 and threads[0]!=threading.get_ident()
    finally:service.close()
