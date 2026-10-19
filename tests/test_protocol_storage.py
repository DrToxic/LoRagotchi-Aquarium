from dataclasses import replace
import json
from pathlib import Path
import subprocess
import pytest
from tank.protocol import (StreamFrames,frame,decode_event,encode_event,ProtocolError,ReturnStatus,mesh_message)
from tank.demo import visitors, RX
from tank.store import Store
from tank.simulator import SimulatedRadio
from tank.client import Client

@pytest.mark.parametrize("chunk",[1,2,3,7,64])
def test_partial_and_coalesced_stream_frames(chunk):
    parser=StreamFrames();wire=b"boot text\r\n"+frame(b"hello",b">")+frame(b"world",b">")
    output=[]
    for i in range(0,len(wire),chunk):output+=parser.feed(wire[i:i+chunk])
    assert output==[b"hello",b"world"]


def test_invalid_length_resynchronises_and_bounded():
    parser=StreamFrames();assert parser.feed(b">\xff\xff"+b"garbage"+frame(b"ok",b">"))==[b"ok"]
    assert len(parser.buffer)<=175


def test_roundtrip_and_validation():
    for v in visitors(12):assert decode_event(RX,encode_event(v))==v
    damaged=bytearray(encode_event(next(visitors())));damaged[45]=9
    with pytest.raises(ProtocolError):decode_event(RX,damaged)
    with pytest.raises(ProtocolError):decode_event(RX,b"\x01")


def test_save_before_ack_crash_replay(tmp_path):
    radio=SimulatedRadio(1);store=Store(tmp_path/'test.sqlite');client=Client(radio,store,token=100);client.connect()
    radio.fail_after_save=True
    with pytest.raises(ConnectionError):client.poll()
    assert len(store.roster())==1 and not radio.acked
    store.close();store=Store(tmp_path/'test.sqlite');radio.close()
    client=Client(radio,store,token=101);client.connect();assert client.poll()
    assert len(store.roster())==1 and radio.acked=={1}
    assert client.poll();assert len(store.roster())==1
    assert store.db.execute('SELECT status FROM returns').fetchone()[0]=='delivery-confirmed'
    assert not client.poll();store.close()


def test_identity_reshare_and_colour_preservation(tmp_path):
    store=Store(tmp_path/'test.sqlite');first,second=list(visitors(2))
    second=replace(second,name=first.name,fish_id=first.fish_id,tx_id=first.tx_id)
    store.save(first);store.save(second);assert len(store.roster())==2
    store.save(replace(first,event_id=20,tx_id=30,appearance=False,body=6,scales=6,eyes=6))
    updated=next(f for f in store.roster() if f.owner==first.owner)
    assert updated.body==first.body and updated.appearance is False
    store.save(replace(first,event_id=19,body=5))
    assert next(f for f in store.roster() if f.owner==first.owner).event_id==20
    store.remove(first.owner);assert len(store.roster())==1
    store.save(replace(first,event_id=21));assert len(store.roster())==2
    store.end_session();assert not store.roster()
    store.save(first);assert not store.roster() # reconnect replay must not undo removal
    store.close()


def test_conflicting_event_id_rejected(tmp_path):
    store=Store(tmp_path/'test.sqlite');first=next(visitors());store.save(first)
    with pytest.raises(ProtocolError):store.save(replace(first,name='corrupt replay'))
    assert store.roster()[0].name==first.name


def test_real_mesh_messages_separate_from_fish_events():
    packet=b'\x07'+bytes.fromhex('010203040506')+b'\xff\0'+b'\0'*4+b'hello mesh'
    message=mesh_message(packet)
    assert message['text']=='hello mesh' and message['sender_prefix']=='010203040506'
    assert mesh_message(b'\x70RX\x01\x02\0') is None


def test_production_firmware_golden_event(tmp_path):
    root=Path(__file__).resolve().parents[2]/'LoRagotchi-RX'
    if not (root/'test/rx/check_receiver.cpp').exists():pytest.skip('isolated firmware source not installed')
    binary=tmp_path/'receiver';golden=tmp_path/'event.bin'
    subprocess.run(['g++','-std=c++17','-I',str(root),str(root/'test/rx/check_receiver.cpp'),'-o',str(binary)],check=True)
    result=subprocess.run([str(binary),str(golden)],check=True,capture_output=True,text=True)
    event=decode_event('03'+'00'*31,golden.read_bytes())
    assert (event.owner,event.fish_id,event.tx_id,event.stage,event.body,event.scales,event.eyes)==('01'+'00'*31,8,7,2,1,3,5)
    assert encode_event(event)==golden.read_bytes()
    assert 'production-core scenarios passed' in result.stdout


def test_client_against_production_cpp_receiver(tmp_path):
    """The PC client speaks real READ fragments/ACKs to the production C++ core."""
    import os,select
    from tank.transport import StreamTransport
    root=Path(__file__).resolve().parents[2]/'LoRagotchi-RX'
    if not (root/'examples/companion_radio/LoRagotchiRX.h').exists():pytest.skip('isolated firmware source not installed')
    fixture=Path(__file__).parent/'fixtures/host_receiver.cpp'
    binary=tmp_path/'host_receiver'
    subprocess.run(['g++','-std=c++17','-I',str(root),str(fixture),'-o',str(binary)],check=True)
    process=subprocess.Popen([str(binary)],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    class Pipe(StreamTransport):
        def read(self):
            if select.select([process.stdout],[],[],.1)[0]:return os.read(process.stdout.fileno(),1024)
            return b''
        def write(self,data):process.stdin.write(data);process.stdin.flush()
        def close(self):process.stdin.close()
    transport=Pipe();store=Store(tmp_path/'cpp.sqlite');client=Client(transport,store,token=45)
    try:
        assert client.connect()==dict(capacity=4,transports=1,storage_ok=True)
        count=0
        while client.poll():count+=1
        assert count==4 and len(store.roster())==2
        assert store.db.execute('SELECT COUNT(*) FROM returns WHERE status="delivery-confirmed"').fetchone()[0]==2
        assert all(f.body==1 and f.scales==3 and f.eyes==5 for f in store.roster())
        client.poll_messages()
    finally:client.close();process.wait(timeout=3);store.close()
    assert process.returncode==0
