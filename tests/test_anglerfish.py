"""Existing RX Water wire -> durable snapshot -> explicitly selected native art."""
from dataclasses import asdict, replace
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import pytest
from tank.demo import visitors as demo_visitors, RX
from tank.protocol import Snapshot, ProtocolError, encode_event, decode_event, MAGIC, bridge_command_allowed
from tank.store import Store
from tank.art import fish_model, colour, tint565
from tank.anglerfish import is_anglerfish, colours, genetic_colour, animate


def visitors(count=1):
    # Explicit legacy wire fixtures, independent of the all-species demo default.
    return (replace(f,species_id=0,species_present=False) for f in demo_visitors(count))


def sample(**kw):
    return replace(next(visitors(1)), stage=2, species_id=14, species_present=True, **kw)


def mesh_hash(root):
    digest=hashlib.sha256()
    for node in root.findAllMatches('**/+GeomNode'):
        for index in range(node.node().getNumGeoms()):
            data=node.node().getGeom(index).getVertexData()
            for array in range(data.getNumArrays()):
                digest.update(data.getArray(array).getHandle().getData())
    return digest.hexdigest()


def test_existing_water_wire_offsets_and_presence():
    seed=next(visitors(1))
    # Independently constructed RX kind3, no dependence on candidate encoder.
    raw=b'\x03'+encode_event(seed)[1:]+struct.pack('<BHBBBB',7,14,8,148,6,2)
    fish=decode_event(RX,raw)
    assert len(raw)==84
    assert (fish.owner,fish.fish_id,fish.tx_id)==(seed.owner,seed.fish_id,seed.tx_id)
    assert (fish.species_id,fish.body_gene,fish.scales_gene,fish.eyes_gene,fish.panel)==(14,8,148,6,2)
    assert is_anglerfish(fish) and encode_event(fish)==raw
    for pos,value in ((77,8),(77,6),(80,7),(82,255),(83,3)):
        bad=bytearray(raw);bad[pos]=value
        with pytest.raises(ProtocolError):decode_event(RX,bad)
    with pytest.raises(ProtocolError):decode_event(RX,raw[:-1])
    assert not is_anglerfish(decode_event(RX,encode_event(seed)))
    assert not is_anglerfish(replace(fish,species_present=False))


def test_metadata_upgrade_preserves_replay_expiry_hide(tmp_path):
    path=tmp_path/'fish.sqlite';clock=[1000.]
    store=Store(path,clock=lambda:clock[0]);old=next(visitors(1))
    # Simulate JSON from before optional metadata existed.
    store.save(old)
    legacy={k:v for k,v in asdict(old).items() if k not in ('species_id','species_present','genes_present','panel_present','body_gene','scales_gene','eyes_gene','panel')}
    store.db.execute('UPDATE events SET body=?',(json.dumps(legacy,sort_keys=True),));store.db.commit()
    store.remove(old.owner);clock[0]=2000
    rich=replace(old,species_id=14,species_present=True)
    assert store.save(rich)
    assert not store.roster() and store.collection()==[]
    assert store.db.execute('SELECT updated FROM fish').fetchone()[0].startswith('1970-01-01T00:16:40')
    assert not store.save(old)
    with pytest.raises(ProtocolError):store.save(replace(rich,species_id=13))
    store.save(replace(old,event_id=20))
    assert store.roster()[0].species_id==14
    store.save(replace(old,event_id=21,fish_id=9999))
    assert not store.roster()[0].species_present
    store.close();store=Store(path)
    assert not store.roster()[0].species_present;store.close()


@pytest.mark.parametrize('stage',range(4))
@pytest.mark.parametrize('style',('classic','rounded','faceted'))
def test_genes_immutable_joints_bounded_mesh_and_lure(stage,style):
    fish=replace(sample(),stage=stage,genes_present=True,body_gene=8,scales_gene=148,eyes_gene=6)
    before=asdict(fish);root,tail,fins=fish_model(fish,64,style)
    assert root.getTag('fish-species')=='14' and root.getTag('fish-style')==style
    assert tail.getParent()==root and all(f.getParent()==root for f in fins)
    low,high=root.getTightBounds(root)
    assert low.x>=-1.53 and high.x<=1.0 and low.z>=-.74 and high.z<=.87
    data_hash=mesh_hash(root)
    count=root.findAllMatches('**/+GeomNode').getNumPaths()
    for phase in (0.,.8,4.,100.,-40.):
        animate(root,phase)
        assert mesh_hash(root)==data_hash
        assert root.findAllMatches('**/+GeomNode').getNumPaths()==count
        assert all(math.isfinite(v) for v in root.find('angler-lure-joint').getHpr())
    assert asdict(fish)==before
    assert count<=12
    root.removeNode()


@pytest.mark.parametrize('stage',range(4))
@pytest.mark.parametrize('tint',(0,0xffff,0x8410))
def test_mono_and_age_expression(stage,tint):
    fish=replace(sample(),stage=stage,body=6,scales=6,eyes=6,tint=tint)
    assert colours(fish)[:2]==(tint565(tint),)*2
    if stage<2:assert colours(fish)[2]==(.90,.90,.90)
    else:assert colours(fish)[2]==tint565(tint)


@pytest.mark.parametrize('stage,bw,fw',((0,2,5),(1,5,6)))
def test_juvenile_weights_and_no_inferred_h1(stage,bw,fw):
    fish=replace(sample(),stage=stage,body=5,scales=3,eyes=2,body_gene=8,scales_gene=148)
    # Unflagged fields are not received H1 genes.
    assert genetic_colour(fish,'body')==(5,colour(5))
    body,fins,eyes=colours(fish);ivory=tint565(0xFFBC)
    for actual,gene,w in ((body,5,bw),(fins,5 if stage==0 else 3,fw)):
        assert actual==pytest.approx(tuple((colour(gene)[k]*w+ivory[k]*(8-w))/8 for k in range(3)))
    assert eyes==(.90,.90,.90)


def test_other_species_keep_published_remote_geometry():
    expected=json.loads((Path(__file__).parent/'fixtures/non_angler_geometry.json').read_text())
    for stage in range(4):
        for style in ('classic','rounded','faceted'):
            for species in (*range(14),15,256,65535):
                fish=replace(next(visitors(1)),stage=stage,species_id=species,species_present=True,
                             genes_present=True,body_gene=8,scales_gene=148,eyes_gene=6)
                root,_,_=fish_model(fish,18,style)
                assert not root.hasTag('fish-species')
                assert mesh_hash(root)==expected[f'{stage}-{style}-{species}']
                root.removeNode()
            fish=replace(next(visitors(1)),stage=stage,species_id=14,species_present=False)
            root,_,_=fish_model(fish,18,style)
            assert mesh_hash(root)==expected[f'{stage}-{style}-absent'];root.removeNode()


def test_bridge_permits_only_existing_water_negotiation_shape():
    assert bridge_command_allowed(MAGIC+b'\x07'+bytes(4)+b'\x01')
    assert not bridge_command_allowed(MAGIC+b'\x07'+bytes(4))
    assert not bridge_command_allowed(MAGIC+b'\x07'+bytes(4)+bytes(2))


@pytest.fixture(scope='module')
def production_binary(tmp_path_factory):
    import os
    root=Path(__file__).resolve().parents[2]
    dx=Path(os.getenv('ANGLER_DX_SOURCE',root/'loragotchi-dx-anglerfish'))/'examples/companion_radio'
    rx=Path(os.getenv('ANGLER_RX_SOURCE',root/'loragotchi-rx-current-ci'))/'examples/companion_radio'
    if not (dx/'LoRaFishCommit.h').exists() or not (rx/'LoRagotchiRX.h').exists():
        pytest.skip('production DX/RX sources not installed; cross-firmware gate NOT RUN')
    binary=tmp_path_factory.mktemp('angler-cpp')/'receiver'
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-I',str(dx),'-I',str(rx),
                    str(Path(__file__).parent/'fixtures/angler_receiver.cpp'),'-o',str(binary)],check=True,capture_output=True)
    return binary


def test_h1_all_240_hues_match_actual_dx(production_binary):
    raw=subprocess.check_output([str(production_binary),'colours'],text=True)
    for gene,rgb in (map(int,line.split()) for line in raw.splitlines()):
        fish=replace(sample(),genes_present=True,body_gene=gene,scales_gene=6,eyes_gene=6)
        assert genetic_colour(fish,'body')[1]==tint565(rgb)


@pytest.mark.parametrize('species',(14,65535))
def test_real_dx_to_rx_fragments_sqlite_to_render(production_binary,tmp_path,species):
    import os,select
    from tank.transport import StreamTransport
    from tank.client import Client
    process=subprocess.Popen([str(production_binary),str(species)],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    class Pipe(StreamTransport):
        def read(self):
            return os.read(process.stdout.fileno(),1024) if select.select([process.stdout],[],[],.1)[0] else b''
        def write(self,data):process.stdin.write(data);process.stdin.flush()
        def close(self):process.stdin.close()
    store=Store(tmp_path/'production.sqlite');client=Client(Pipe(),store,token=45)
    try:
        client.connect();assert client.water
        count=0
        while client.poll():count+=1
        assert count==8
        roster=store.roster();assert len(roster)==4
        assert {f.stage for f in roster}==set(range(4))
        assert len({f.owner for f in roster})==4
        for fish in roster:
            assert fish.species_present and fish.species_id==species
            assert (fish.body_gene,fish.scales_gene,fish.eyes_gene,fish.panel)==(8,148,6,2)
            root,_,_=fish_model(fish,10)
            assert (root.getTag('fish-species')=='14')==(species==14)
            root.removeNode()
    finally:
        client.close();process.wait(timeout=3);store.close()
    assert process.returncode==0


def test_old_metadata_enrichment_never_repopulates_or_replaces_session(tmp_path):
    path=tmp_path/'sessions.sqlite';old=next(visitors(1))
    first=Store(path,session='first');first.save(old);first.close()
    second=Store(path,session='second')
    assert not second.save(replace(old,species_id=14,species_present=True))
    assert not second.roster();second.close()
    first=Store(path,session='first')
    # Different RX, same owner: previous old rich replay is not a new share.
    later=replace(old,rx='ab'*32,event_id=2,name='new snapshot')
    first.save(later)
    assert not first.save(replace(old,species_id=14,species_present=True,
                                  genes_present=True,body_gene=8,scales_gene=148,eyes_gene=6))
    assert first.roster()[0].rx==later.rx
    assert not first.roster()[0].genes_present
    first.close()


@pytest.mark.parametrize('status',(2,3))
def test_negotiation_only_falls_back_for_explicit_unsupported_command(status,tmp_path):
    from tank.client import Client, CommandError
    from tank.simulator import SimulatedRadio
    class Unhealthy(SimulatedRadio):
        def send(self,payload):
            if payload.startswith(MAGIC) and payload[4]==7:
                self.replies.put(MAGIC+bytes([7,status]));return
            super().send(payload)
    store=Store(tmp_path/'unhealthy.sqlite');client=Client(Unhealthy(0),store,token=45)
    with pytest.raises(CommandError) as caught:client.connect()
    assert caught.value.status==status
    assert not store.roster();store.close()


def test_invalid_rich_snapshot_is_not_acknowledged(tmp_path):
    from tank.client import Client
    from tank.simulator import SimulatedRadio
    radio=SimulatedRadio(0)
    raw=bytearray(encode_event(sample()));raw[77]=8
    radio.events={1:bytes(raw)}
    store=Store(tmp_path/'bad.sqlite');client=Client(radio,store,token=45);client.connect()
    with pytest.raises(ProtocolError):client.poll()
    assert not radio.acked and not store.roster();client.close();store.close()
