"""Model/worker boundaries are exercised without UI or any radio connection."""
from dataclasses import asdict, replace
import json
import sqlite3
from types import SimpleNamespace

import pytest

from tank.demo import visitors
from tank.nursery import NurserySettings, NurseryStore, NurseryWorker, eligible_parent


def parents():
    return [replace(f,stage=2) for f in visitors(2)]


@pytest.mark.parametrize('stage',[0,1,4,-1,True,2.0,'2',None])
def test_ineligible_stages_cannot_bypass_model(stage):
    a,b=parents();a=replace(a,stage=stage)
    assert not eligible_parent(a)
    store=NurseryStore(':memory:','x',mode='demo')
    try:
        with pytest.raises((ValueError,TypeError,OverflowError)):
            store.create(a,b,NurserySettings(enabled=True))
        assert store.eggs()==[]
        assert store.db.execute('SELECT count(*) FROM nursery_cooldowns').fetchone()[0]==0
    finally:store.close()


def test_demo_founders_and_lineage_reload_without_changing_preview(tmp_path):
    a,b=parents();path=tmp_path/'demo.db'
    store=NurseryStore(path,'x',mode='demo')
    store.create(a,replace(b,stage=3),NurserySettings(enabled=True),egg_id='c'*32)
    egg=store.eggs()[0];store.close()
    assert egg['lineage']==dict(rule='demo-ancestry-v2',ancestry_depth=1,pet_generation=1)
    assert egg['preview']['rule']=='local-linear-srgb-v1'
    assert egg['preview']['firmware_genome'] is None
    store=NurseryStore(path,'x',mode='demo')
    try:assert store.eggs()==[egg]
    finally:store.close()


def test_old_schema_migration_does_not_reroll_or_relabel(tmp_path):
    path=tmp_path/'legacy.db';db=sqlite3.connect(path)
    db.execute('CREATE TABLE eggs(scope TEXT NOT NULL,id TEXT PRIMARY KEY,created REAL NOT NULL,parents TEXT NOT NULL,preview TEXT NOT NULL)')
    frozen=json.dumps([asdict(p) for p in parents()]);preview='{"rule":"local-linear-srgb-v1","fraction":0.123,"body_rgb":[1,0,0],"firmware_genome":null}'
    db.execute('INSERT INTO eggs VALUES(?,?,?,?,?)',('x','d'*32,100,frozen,preview));db.commit();db.close()
    store=NurseryStore(path,'x',mode='demo')
    try:
        assert store.db.execute('SELECT parents,preview FROM eggs').fetchone()==(frozen,preview)
        assert store.eggs()[0]['lineage'] is None
        assert len(list(store.db.execute('PRAGMA table_info(eggs)')))==5
        # Old versions can still use their unqualified five-column insert.
        store.db.execute('INSERT INTO eggs VALUES(?,?,?,?,?)',('x','0'*32,101,frozen,preview))
        store.db.commit();assert len(store.eggs())==2
    finally:store.close()


def test_synthetic_and_real_pairs_never_mix_in_live_or_demo_store():
    a,b=parents()
    real_a=replace(a,rx='e'*64,owner='a'*64);real_b=replace(b,rx='e'*64,owner='b'*64)
    settings=NurserySettings(enabled=True)
    for mode,invalid in [('live',[(a,b),(a,real_b),(real_a,b)]),('demo',[(real_a,real_b),(a,real_b)])]:
        store=NurseryStore(':memory:','x',mode=mode)
        try:
            for first,second in invalid:
                with pytest.raises(ValueError,match='Demo|demo'):store.create(first,second,settings)
            assert store.eggs()==[]
        finally:store.close()
    store=NurseryStore(':memory:','x')
    try:
        store.create(real_a,real_b,settings)
        assert len(store.eggs())==1 and store.eggs()[0]['lineage'] is None
    finally:store.close()


def test_duplicate_owner_or_fish_cannot_create_egg():
    a,b=parents();store=NurseryStore(':memory:','x',mode='demo')
    try:
        for second in (a,replace(b,owner=a.owner),replace(b,owner=a.owner.upper())):
            with pytest.raises(ValueError,match='different full owner'):store.create(a,second,NurserySettings(enabled=True))
        assert store.eggs()==[]
    finally:store.close()


def test_stale_worker_command_and_demo_live_switch_do_not_cross_stores(tmp_path):
    worker=NurseryWorker(SimpleNamespace(settings=tmp_path/'settings.json',database=tmp_path/'demo.db',session='x'))
    a,b=parents();values=dict(a=asdict(a),b=asdict(b),settings=asdict(NurserySettings(enabled=True)),id='e'*32)
    try:
        worker.submit('open',mode='demo',context=1);assert worker.events.get(timeout=3)['eggs']==[]
        worker.submit('create',context=1,**values);saved=worker.events.get(timeout=3)['eggs']
        worker.submit('open',mode='live',context=2);assert worker.events.get(timeout=3)['eggs']==saved
        worker.submit('create',context=1,**values);assert worker.events.get(timeout=3)['error']
        worker.submit('create',context=2,**values);assert worker.events.get(timeout=3)['error']
        worker.submit('open',mode='live',context=3);assert worker.events.get(timeout=3)['eggs']==saved
        worker.submit('open',mode='demo',context=4);assert worker.events.get(timeout=3)['eggs']==saved
    finally:worker.close()


def test_adoption_retains_egg_and_explicit_local_hatch_consumes_once(tmp_path):
    worker=NurseryWorker(SimpleNamespace(settings=tmp_path/'settings.json',database=tmp_path/'demo.db',session='x'))
    a,b=parents()
    try:
        worker.submit('open',mode='demo');worker.events.get(timeout=3)
        worker.submit('create',a=asdict(a),b=asdict(b),settings=asdict(NurserySettings(enabled=True)),id='f'*32)
        saved=worker.events.get(timeout=3)['eggs']
        worker.submit('adopt',id='f'*32);assert worker.events.get(timeout=3)['error']
        worker.submit('open',mode='demo');assert worker.events.get(timeout=3)['eggs']==saved
        worker.submit('hatch',id='f'*32);hatched=worker.events.get(timeout=3)
        assert not hatched['eggs'] and len(hatched['fish'])==1
        worker.submit('hatch',id='f'*32);assert worker.events.get(timeout=3)['fish']==hatched['fish']
    finally:worker.close()
