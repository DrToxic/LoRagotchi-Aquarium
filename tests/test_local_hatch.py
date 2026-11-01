"""Permanent local fry: storage atomicity and renderer/service separation."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
import json
import sqlite3
from types import SimpleNamespace

import pytest
from tank.demo import visitors
from tank.nursery import NurseryStore, NurserySettings, NurseryWorker, local_fry, eligible_parent


def seed(store, ident='a'*32, now=0):
    a,b=[replace(f,stage=2) for f in visitors(2)]
    store.create(a,b,NurserySettings(enabled=True),now=now,egg_id=ident)
    return a,b


def test_hatch_reload_forever_preview_and_no_rebreed(tmp_path):
    path=tmp_path/'local.db';store=NurseryStore(path,'x','demo')
    parents=seed(store);egg=store.eggs()[0]
    store.hatch(egg['id']);saved=store.fish();f=local_fry(saved[0])
    assert f.stage==0 and f.generation==1 and f.lifetime_hours==0
    assert len(bytes.fromhex(f.owner))==32 and f.rx=='local-nursery'
    assert tuple(egg['preview']['body_rgb'])==f.local_body_rgb
    assert not eligible_parent(f) and not eligible_parent(replace(f,stage=2))
    with pytest.raises(ValueError):store.create(replace(f,stage=2),parents[1],NurserySettings(enabled=True))
    # Exact consumed egg, parents and preview remain archived; delayed retries
    # cannot recreate either an egg or a second fish.
    store.create(*parents,NurserySettings(enabled=True),now=10000,egg_id=egg['id'])
    assert not store.eggs();store.close()
    store=NurseryStore(path,'x','demo')
    assert store.fish()==saved
    store.hatch(egg['id'],now=10**12);assert store.fish()==saved
    assert store.db.execute('SELECT parents,preview FROM nursery_hatched_eggs').fetchone()
    store.remove_fry(f.owner);store.hatch(egg['id']);assert not store.fish()
    store.close()


def test_hatch_rollback_keeps_egg_and_preview(tmp_path):
    store=NurseryStore(tmp_path/'x.db','x','demo');seed(store);egg=store.eggs()
    store.db.execute("CREATE TRIGGER reject_hatch BEFORE DELETE ON eggs BEGIN SELECT RAISE(ABORT,'test power boundary'); END")
    with pytest.raises(sqlite3.IntegrityError):store.hatch(egg[0]['id'])
    assert store.eggs()==egg and not store.fish()
    assert not list(store.db.execute('SELECT * FROM nursery_hatched_eggs'))
    store.close()


def test_concurrent_hatch_is_exactly_once(tmp_path):
    path=tmp_path/'x.db';s=NurseryStore(path,'x','demo');seed(s);s.close()
    def hatch(_):
        s=NurseryStore(path,'x','demo')
        try:s.hatch('a'*32);return s.fish()
        finally:s.close()
    with ThreadPoolExecutor(4) as pool:values=list(pool.map(hatch,range(4)))
    assert all(v==values[0] for v in values) and len(values[0])==1


def test_fry_cap_failure_retains_egg_and_delete_reopens_slot(tmp_path,monkeypatch):
    import tank.nursery as nursery
    monkeypatch.setattr(nursery,'LOCAL_FRY_CAPACITY',1)
    s=NurseryStore(tmp_path/'x.db','x','demo');seed(s);s.hatch('a'*32)
    seed(s,'b'*32,now=10000);egg=s.eggs()
    with pytest.raises(ValueError,match='full'):s.hatch('b'*32)
    assert s.eggs()==egg
    first=s.fish()[0]['owner'];s.remove_fry(first);s.hatch('b'*32)
    assert len(s.fish())==1 and s.fish()[0]['owner']!=first
    s.close()


def test_old_db_import_once_preserves_bytes_cooldown_and_old_lineage(tmp_path):
    old=tmp_path/'nursery-demo.sqlite3';s=NurseryStore(old,'x','demo');seed(s)
    legacy=dict(rule='demo-founders-v1',parent_generations=[1,1],generation=2)
    s.db.execute('UPDATE nursery_lineage SET metadata=?',(json.dumps(legacy),));s.db.commit()
    payload=s.db.execute('SELECT * FROM eggs').fetchone();s.close();before=old.read_bytes()
    args=SimpleNamespace(settings=tmp_path/'settings.json',database=':memory:',session='x')
    def open_worker(mode):
        w=NurseryWorker(args);w.submit('open',mode=mode,context=1);return w,w.events.get(timeout=5)
    w,event=open_worker('live')
    assert event['eggs'][0]['lineage']['pet_generation']==1
    assert event['eggs'][0]['lineage']['legacy_metadata']==legacy
    w.submit('hatch',id='a'*32,context=1);hatched=w.events.get(timeout=5);w.close()
    w,event=open_worker('demo');assert event['fish']==hatched['fish'] and not event['eggs'];w.close()
    assert old.read_bytes()==before
    s=NurseryStore(tmp_path/'nursery-local.sqlite3','x:demo','demo')
    archived=s.db.execute('SELECT * FROM nursery_hatched_eggs').fetchone()
    assert archived[1:]==payload[1:]
    with pytest.raises(ValueError,match='resting'):seed(s,'b'*32,now=1)
    s.close()


def test_source_switch_restart_scope_replay_and_stale_hatch(tmp_path):
    args=SimpleNamespace(settings=tmp_path/'settings.json',database=':memory:',session='x')
    w=NurseryWorker(args);a,b=[replace(f,stage=2) for f in visitors(2)]
    w.submit('open',mode='demo',context=1);w.events.get(timeout=5)
    w.submit('create',a=asdict(a),b=asdict(b),settings=asdict(NurserySettings(enabled=True)),id='a'*32,context=1)
    eggs=w.events.get(timeout=5)['eggs']
    w.submit('open',mode='live',context=2);assert w.events.get(timeout=5)['eggs']==eggs
    w.submit('hatch',id='a'*32,context=1);assert w.events.get(timeout=5)['error']
    w.submit('hatch',id='a'*32,context=2);f=w.events.get(timeout=5)['fish'];w.close()
    w=NurseryWorker(args)
    w.submit('open',mode='live',context=3);assert w.events.get(timeout=5)['fish']==f
    w.submit('open',mode='replay',context=4);assert not w.events.get(timeout=5)['fish']
    w.submit('open',mode='demo',context=5);assert w.events.get(timeout=5)['fish']==f
    w.close()


def test_live_egg_local_hatch_keeps_live_parent_data(tmp_path):
    s=NurseryStore(tmp_path/'x.db','live','live')
    a,b=[replace(f,stage=2,rx='e'*64,owner=owner*64) for f,owner in zip(visitors(2),'ab')]
    s.create(a,b,NurserySettings(enabled=True));egg=s.eggs()[0]
    assert egg['lineage'] is None
    s.hatch(egg['id']);assert s.fish()[0]['generation']==1
    assert json.loads(s.db.execute('SELECT parents FROM nursery_hatched_eggs').fetchone()[0])==egg['parents']
    s.close()


def test_renderer_merge_and_remove_never_send_local_to_service():
    from tank.aquarium import Aquarium
    import queue
    f=SimpleNamespace(owner='local',kind='local_fry');v=SimpleNamespace(owner='live',kind='snapshot')
    calls=[];a=SimpleNamespace(visitor_roster=[v],nursery=SimpleNamespace(fish=[f],remove_fry=lambda owner:calls.append(owner)),selected=100,sync_models=lambda:None,service=SimpleNamespace(commands=queue.Queue()))
    Aquarium.merge_local_fish(a);assert a.roster==[v,f] and a.selected==0
    a.selected=1;Aquarium.remove_selected(a);assert calls==['local'] and a.service.commands.empty()
    a.selected=0;Aquarium.remove_selected(a);assert a.service.commands.get()==('remove','live')


def test_genetic_preview_expression_is_exact_without_quantisation(tmp_path):
    from tank.art import juvenile_colours,tint565
    s=NurseryStore(tmp_path/'x.db','x','demo');seed(s);rgb=s.eggs()[0]['preview']['body_rgb'];s.hatch('a'*32)
    f=local_fry(s.fish()[0]);ivory=tint565(0xFFBC)
    assert juvenile_colours(f)==tuple(tuple((rgb[k]*w+ivory[k]*(8-w))/8 for k in range(3)) for w in (2,5))
    s.close()
