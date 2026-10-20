"""Companion protocol, persistence and single-owner integration regressions."""
import json
import os
import queue
import select
import socket
import struct
import threading
import time
import pytest
from tank import meshcore_protocol as wire
from tank.client import Client
from tank.demo import RX
from tank.protocol import ProtocolError, StreamFrames, frame, bridge_command_allowed, mesh_message
from tank.radio import RadioSession
from tank.radio_store import RadioHistory
from tank.store import Store
from tank.bridge import relay, public_response
from tank.transport import TCPTransport, SerialTransport
from tools.radio_peer import MeshRadio, PEER, REPEATER, SECRET, contact_packet, direct_message, channel_message


@pytest.fixture
def setup(tmp_path):
    peer=MeshRadio();store=Store(tmp_path/'radio.sqlite');events=[]
    client=Client(peer,store,events.append,token=1);client.connect()
    radio=RadioSession(client,events.append)
    radio.schedule_refresh()
    while radio.tasks:client.poll();radio.step()
    yield peer,store,client,radio,events
    radio.close();client.close();store.close()


def test_wire_contact_paths_keep_zero_hop_hash_and_full_identity():
    packet=contact_packet(path=b'\0\xaa')
    item=wire.contact(packet)
    assert item['key']==PEER and item['path']=='00aa' and len(packet)==148
    changed=wire.contact_update(item,name='New 🐟',flags=1)
    assert changed[1:33]==bytes.fromhex(PEER)
    assert changed[36:100]==packet[36:100] and changed[132:]==packet[132:]
    assert wire.contact(b'\x03'+changed[1:])['name']=='New 🐟'
    with pytest.raises(ProtocolError):wire.contact(packet[:40])
    invalid=bytearray(packet);invalid[35]=127  # 63 two-byte hops do not fit 64 bytes
    with pytest.raises(ProtocolError):wire.contact(bytes(invalid))
    with pytest.raises(ValueError):wire.contact_update(item,path='00aa',path_width=3)


def test_native_firmware_cli_type_and_signed_dm_parse():
    message=direct_message(text='diagnostic reply',text_type=1)
    result=mesh_message(message)
    assert result['text']=='diagnostic reply' and result['text_type']==1 and result['timestamp']==1700000010
    signed=message[:11]+b'\x02'+message[12:16]+bytes(4)+b'room text'
    assert mesh_message(signed)['text']=='room text'
    assert wire.allowed_command(b'\x02\x03\0'+bytes(10)+b'x',True)
    assert not wire.allowed_command(b'\x02\x04\0'+bytes(10)+b'x',True)


def test_refresh_interleaves_fish_and_does_not_transmit_rf(setup):
    peer,store,client,radio,events=setup
    assert radio.loaded and radio.info['key']==RX and len(radio.contacts)==2
    assert len(radio.channels)==8 and radio.channels[1]['name']=='#loragotchi-dx'
    assert len(store.roster())==3 and {1,3,5}<=peer.acked
    assert not any(p[0] in (2,3,7,9,11,12,14,15,16,26,27,32,38,39,52) for p in peer.commands)
    serialized=json.dumps([e for e in events if isinstance(e,dict)])
    assert SECRET.hex() not in serialized and '123456' not in json.dumps(radio.device)
    assert 'raw' not in next(e for e in events if isinstance(e,dict) and e.get('contacts'))['contacts'][0]


def test_channel_and_direct_sends_persist_distinct_delivery_states(setup):
    peer,store,client,radio,events=setup
    radio.send_message('channel',1,'The fish say hello 🐟')
    ch=radio.conversation_channel(1)
    assert radio.history.messages(RX,ch)[0]['status']=='sent'
    radio.send_message('direct',PEER,'Hello direct')
    mid=next(iter(radio.pending));ack=bytes.fromhex(radio.pending[mid]['ack'])
    assert radio.history.messages(RX,'dm:'+PEER[:12])[0]['status']=='pending'
    peer.replies.put(b'\x82'+ack+struct.pack('<I',81))
    client.poll()
    assert radio.history.messages(RX,'dm:'+PEER[:12])[0]['status']=='delivered'
    assert not radio.pending and peer.tx_count==2


def test_ack_arrives_before_send_response_and_unknown_zero_ack(setup):
    peer,store,client,radio,events=setup
    peer.ack_early=True;radio.send_message('direct',PEER,'Early ack')
    assert radio.history.messages(RX,'dm:'+PEER[:12])[-1]['status']=='delivered'
    assert not radio.pending
    peer.ack_early=False;radio.send_message('direct',PEER,'No ack')
    mid=next(iter(radio.pending));radio.pending[mid]['deadline']=0;radio.expire()
    assert radio.history.messages(RX,'dm:'+PEER[:12])[-1]['status']=='unconfirmed'
    assert peer.tx_count==2


def test_outbound_timestamp_survives_same_clock_reconnect(setup,monkeypatch):
    peer,store,client,radio,events=setup
    monkeypatch.setattr('tank.radio.time.time',lambda:1700000100)
    radio.send_message('direct',PEER,'First')
    first=radio.history.messages(RX,'dm:'+PEER[:12])[-1]['timestamp']
    radio.close()
    new=RadioSession(client,events.append);new.schedule_refresh()
    while new.tasks:client.poll();new.step()
    new.send_message('direct',PEER,'Second')
    assert new.history.messages(RX,'dm:'+PEER[:12])[-1]['timestamp']==first+1
    new.close()


def test_rejected_send_and_timeout_preserve_drafts_no_automatic_retry(setup):
    peer,store,client,radio,events=setup
    peer.reject_next=2
    with pytest.raises(wire.RadioRejected):radio.send_message('direct',PEER,'Rejected')
    assert radio.history.messages(RX,'dm:'+PEER[:12])[-1]['status']=='failed'
    original=peer.receive
    def lost(timeout=2):
        while not peer.replies.empty():peer.replies.get_nowait()
        raise TimeoutError('lost command reply')
    peer.receive=lost
    with pytest.raises(TimeoutError):radio.send_message('direct',PEER,'Unknown outcome')
    peer.receive=original
    assert radio.history.messages(RX,'dm:'+PEER[:12])[-1]['status']=='unconfirmed'
    assert peer.tx_count==1


def test_text_is_utf8_byte_limited_never_truncated_and_prefix_collision_fails_closed(setup):
    peer,store,client,radio,events=setup
    before=len(peer.commands)
    for route,target,text in [('direct',PEER,'🐟'*41),('channel',1,'a'*149),('direct',PEER,'abc\0def')]:
        with pytest.raises(ValueError):radio.send_message(route,target,text)
    collision=PEER[:12]+'ff'*26
    radio.contacts[collision]=wire.contact(contact_packet(key=collision))
    with pytest.raises(ValueError,match='Ambiguous'):radio.send_message('direct',PEER,'Must not send')
    assert len(peer.commands)==before


def test_real_inbox_persists_unicode_deduplicates_and_separates_channel_reuse(setup):
    peer,store,client,radio,events=setup
    old=radio.conversation_channel(1)
    peer.inbox.extend([channel_message(),channel_message(),direct_message()])
    for _ in range(3):client.poll_messages()
    assert len(radio.history.messages(RX,old))==1
    assert radio.history.messages(RX,'dm:'+PEER[:12])[0]['text']=='Hello from the mesh 🐟'
    radio.execute('channel',dict(index=1,name='#changed',secret=''))
    while radio.tasks:radio.step()
    new=radio.conversation_channel(1)
    assert new!=old and not radio.history.messages(RX,new)
    assert len(radio.history.messages(RX,old))==1


def test_contact_edits_preserve_paths_and_channel_writes_only_on_action(setup):
    peer,store,client,radio,events=setup
    radio.execute('save_contact',dict(key=PEER,name='Harbor 🐟',flags=1))
    while radio.tasks:radio.step()
    assert radio.contacts[PEER]['name']=='Harbor 🐟' and radio.contacts[PEER]['path']=='00aa'
    radio.execute('save_contact',dict(key=PEER,path='00aabbcc',path_width=2))
    while radio.tasks:radio.step()
    assert radio.contacts[PEER]['path_length']==66 and radio.contacts[PEER]['path']=='00aabbcc'
    radio.execute('reset_path',dict(key=PEER))
    while radio.tasks:radio.step()
    assert radio.contacts[PEER]['path_length']==255
    radio.execute('remove_contact',dict(key=PEER))
    while radio.tasks:radio.step()
    assert PEER not in radio.contacts
    radio.execute('channel',dict(index=3,name='Private',secret='fe'*16))
    while radio.tasks:radio.step()
    assert radio.channels[3]['name']=='Private' and 'secret' not in radio.channels[3]
    assert peer.channel_records[3][1]==b'\xfe'*16
    radio.execute('clear_channel',dict(index=3))
    while radio.tasks:radio.step()
    assert not radio.channels[3]['occupied']


def test_device_actions_preserve_unedited_flags_and_validate_before_writing(setup):
    peer,store,client,radio,events=setup
    before=len(peer.commands)
    for action,data in [('power',dict(power=99)),('radio',dict(frequency='nan',bandwidth=250,sf=11,cr=5)),
                        ('location',dict(lat=91,lon=0)),('name',dict(name='🐟'*9))]:
        with pytest.raises(ValueError):radio.execute(action,data)
    assert len(peer.commands)==before
    radio.execute('name',dict(name='Harbor RX'))
    radio.execute('radio',dict(frequency=915.5,bandwidth=125,sf=10,cr=6))
    radio.execute('power',dict(power=-3))
    radio.execute('preferences',dict(manual_add=0,location_policy=2))
    while radio.tasks:radio.step()
    assert radio.info['name']=='Harbor RX' and radio.info['frequency']==915.5
    assert radio.info['power']==-3 and radio.info['location_policy']==2
    assert radio.info['multi_acks']==1 and radio.info['telemetry']==0


def test_remote_commands_use_firmware_types_and_do_not_save_passwords(setup):
    peer,store,client,radio,events=setup
    password='example-password-for-test'
    radio.execute('login',dict(key=REPEATER,password=password))
    radio.execute('command',dict(key=REPEATER,text='ver'))
    assert [p for p in peer.commands if p[0]==2][-1][1]==1
    radio.execute('command',dict(key=PEER,text='ver'))
    assert [p for p in peer.commands if p[0]==2][-1][1]==3
    assert password not in json.dumps(events,default=str)
    assert password not in json.dumps(radio.history.messages(RX,'dm:'+REPEATER[:12]))


def test_history_retention_pagination_restart_and_radio_identity_isolation(tmp_path,monkeypatch):
    import tank.radio_store as module
    monkeypatch.setattr(module,'MAX_HISTORY',80)
    store=Store(tmp_path/'history.sqlite');history=RadioHistory(store.db)
    for i in range(120):history.add(RX,'dm:a',dict(direction='out',text=f'message {i}',status='pending',timestamp=i))
    latest=history.messages(RX,'dm:a');older=history.messages(RX,'dm:a',before=latest[0]['id'])
    assert len(latest)==60 and len(older)==20 and older[-1]['id']<latest[0]['id']
    assert not history.messages('f'*64,'dm:a')
    store.close();store=Store(tmp_path/'history.sqlite');history=RadioHistory(store.db)
    assert all(m['status']=='unconfirmed' for m in history.messages(RX,'dm:a'))
    assert len(history.conversations(RX))==1;store.close()


def test_small_ble_mtu_no_long_commands_and_pending_cancel_before_send(setup):
    peer,store,client,radio,events=setup
    peer.max_payload=20;before=len(peer.commands)
    with pytest.raises(ValueError,match='MTU'):radio.send_message('direct',PEER,'a long chat message')
    assert len(peer.commands)==before
    radio.cancel=lambda:True
    with pytest.raises(ConnectionAbortedError):radio.request(b'\x14',(12,))
    assert len(peer.commands)==before


def test_telemetry_known_unknown_and_truncated_fields():
    assert wire.telemetry(bytes.fromhex('016700eb'))=='Ch 1 Temperature: 23.5'
    assert 'Unknown sensor type 250' in wire.telemetry(bytes.fromhex('01fa00'))
    with pytest.raises(ProtocolError):wire.telemetry(bytes.fromhex('016700'))
    with pytest.raises(ProtocolError):wire.remote_status(b'\x87'+bytes(30))
    packet=b'\x87\0'+bytes(6)+struct.pack('<HHhhIIII',4100,1,-110,-78,20,10,10,120)+bytes(28)
    assert 'RX 20 / TX 10' in wire.remote_status(packet)


def test_bridge_allowlist_and_response_redaction():
    for payload in (b'\x17',b'\x18'+bytes(64),b'\x13reboot',b'\x33reset',b'\x42get pin',b'\x09'+bytes(35),b'\x20\0'):
        assert not bridge_command_allowed(payload,True)
    assert bridge_command_allowed(wire.BRIDGE_CAPS)
    assert bridge_command_allowed(b'\x04')
    assert not bridge_command_allowed(b'\x03\0\0'+bytes(4)+b'hello')
    assert bridge_command_allowed(b'\x03\0\0'+bytes(4)+b'hello',True)
    payload=b'\x12\x01'+b'#private'.ljust(32,b'\0')+SECRET
    response=public_response(payload)
    assert response[:34]==payload[:34] and response[34:]!=SECRET and len(response)==50
    assert public_response(response[:34]+bytes(16))[34:]==bytes(16)


@pytest.mark.parametrize('write',[False,True])
def test_actual_tcp_bridge_supports_stock_queries_and_opt_in_writes(tmp_path,write):
    peer=MeshRadio();stop=threading.Event();errors=[]
    server=socket.socket();server.bind(('127.0.0.1',0));server.listen(1)
    def run():
        sock,_=server.accept()
        with sock:
            try:relay(sock,peer,b'x'*32,stop,radio_control=write)
            except (ConnectionError,OSError):pass
            except Exception as exc:errors.append(exc)
    thread=threading.Thread(target=run);thread.start()
    transport=TCPTransport('127.0.0.1',server.getsockname()[1],b'x'*32)
    store=Store(tmp_path/'network.sqlite');client=Client(transport,store,token=1)
    try:
        client.connect();radio=RadioSession(client,lambda _:None,network=True);radio.schedule_refresh()
        while radio.tasks:client.poll();radio.step()
        assert radio.loaded and radio.writable==write and len(store.roster())==3
        if write:radio.send_message('channel',1,'Via shared LAN connection')
        else:
            with pytest.raises(ValueError,match='read-only'):radio.send_message('channel',1,'Not permitted')
        assert peer.tx_count==int(write)
        # Rejected arbitrary writes don't kill the fish connection.
        transport.send(b'\x17');assert transport.receive()==b'\x01\x06'
        client.poll()
    finally:client.close();store.close();stop.set();thread.join(3);server.close()
    assert not errors and not thread.is_alive()


@pytest.mark.skipif(os.name!='posix',reason='POSIX PTY integration')
def test_one_real_serial_port_carries_fish_contacts_messages_and_ack(tmp_path):
    import pty
    master,slave=pty.openpty();transport=SerialTransport(os.ttyname(slave));stop=threading.Event();errors=[]
    peer=MeshRadio(contact_count=35);peer.ack_early=True;parser=StreamFrames(b'<')
    def run():
        try:
            while not stop.is_set():
                if not select.select([master],[],[],.05)[0]:continue
                for payload in parser.feed(os.read(master,4096)):
                    peer.send(payload)
                    while not peer.replies.empty():
                        packet=frame(peer.replies.get_nowait(),b'>');os.write(master,packet[:2]);os.write(master,packet[2:])
        except OSError:
            if not stop.is_set():errors.append('unexpected PTY close')
    thread=threading.Thread(target=run);thread.start();store=Store(tmp_path/'serial.sqlite')
    client=Client(transport,store,token=1)
    try:
        client.connect();radio=RadioSession(client,lambda _:None);radio.schedule_refresh()
        while radio.tasks:client.poll();radio.step()
        assert len(radio.contacts)==35 and len(store.roster())==3
        radio.send_message('direct',PEER,'USB shared session 🐟')
        assert radio.history.messages(RX,'dm:'+PEER[:12])[-1]['status']=='delivered'
        peer.inbox.append(channel_message());client.poll_messages()
        assert radio.history.messages(RX,radio.conversation_channel(1))[-1]['direction']=='in'
    finally:client.close();store.close();stop.set();thread.join(3);os.close(master);os.close(slave)
    assert not errors and not thread.is_alive()
