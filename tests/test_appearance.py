from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import pytest
from tank.appearance import Appearance, evaluate, scene_scale
from tank.settings import Settings
from tank.bubble_columns import Surface, place_emitters, surfaces


def test_old_settings_migrate_individually_and_roundtrip_unknown_fields(tmp_path):
    path=tmp_path/'settings.json'
    raw=dict(preset='low',plants=7,lighting=False,decorations={'anchor':True},
             fps='bad',future_setting={'value':3},appearance={'brightness':.6,'fog_density':float('nan'),'future':True})
    path.write_text(json.dumps(raw));before=path.read_bytes()
    s=Settings.load(path)
    assert path.read_bytes()==before
    assert s.plants==7 and not s.lighting and s.decorations=={'anchor':True}
    assert s.fps==45 and s.appearance.brightness==.6 and s.appearance.fog_density==.012
    assert len(s.load_warnings)==2 and s.schema_version==2
    s.save(path);new=json.loads(path.read_text())
    assert path.with_name('settings.json.pre-migration.bak').read_bytes()==before
    assert new['future_setting']==raw['future_setting'] and new['appearance']['future'] is True
    assert Settings.load(path)==s


def test_corrupt_settings_preserved_on_explicit_save(tmp_path):
    path=tmp_path/'settings.json';path.write_text('{broken')
    previous=path.with_name('settings.json.pre-migration.bak');previous.write_text('older backup')
    settings=Settings.load(path)
    assert path.read_text()=='{broken'
    settings.save(path);settings.save(path)
    assert previous.read_text()=='older backup'
    assert path.with_name('settings.json.pre-migration.1.bak').read_text()=='{broken'
    assert len(list(tmp_path.glob('*.bak')))==2


@pytest.mark.parametrize('change',[{'brightness':float('nan')},{'column_count':True},
    {'column_particles':2.5},{'column_count':17},{'timezone':'not/a/zone'},
    {'day_start':'7:00'},{'night_start':'07:00'},{'fog_enabled':1},
    {'background_top':'red'},{'new_setting':True},{'column_width':0}])
def test_bad_appearance_rejected(change):
    with pytest.raises(ValueError):Appearance.from_dict(change)


def test_schedule_ramps_midnight_and_dst():
    p=Appearance(mode='clock',timezone='UTC',day_start='22:00',night_start='06:00')
    for hour,minute,expected in ((21,59,0),(22,0,0),(22,30,.5),(23,0,1),(0,0,1),(6,30,.5),(7,0,0)):
        weight,_=evaluate(p,datetime(2026,10,21,hour,minute,tzinfo=timezone.utc))
        assert weight==pytest.approx(expected)
    p=replace(p,timezone='America/New_York',day_start='07:00',night_start='19:00',transition_minutes=0)
    # Spring DST and fall repeated hour use the selected local wall clock.
    for stamp,expected in [('2026-03-08T10:59:00+00:00',0),('2026-03-08T11:00:00+00:00',1),
                          ('2026-11-01T06:30:00+00:00',0),('2026-11-01T12:00:00+00:00',1)]:
        assert evaluate(p,datetime.fromisoformat(stamp))[0]==expected


def test_ha_sun_stale_invalid_and_timezone_fallback():
    now=datetime(2026,10,21,12,tzinfo=timezone.utc)
    p=Appearance(mode='ha_sun',timezone='ha',transition_minutes=0)
    env=dict(online=True,observed_at=now.timestamp(),elevation=0,timezone='Europe/London')
    assert evaluate(p,now,env)==(.5,'Home Assistant sun')
    for change in ({'observed_at':now.timestamp()-121},{'online':False},{'elevation':float('nan')},
                   {'elevation':True},{'observed_at':now.timestamp()+60}):
        weight,status=evaluate(p,now,{**env,**change})
        assert weight==1 and 'clock fallback' in status
    assert 'UTC' in evaluate(p,now,{})[1]
    assert scene_scale(Appearance(),1)==(1,1,1)
    assert evaluate(p,now,{},preview=0)==(0.,'Night preview')


def test_quality_changes_do_not_reset_appearance():
    s=Settings();s.appearance.brightness=.5
    s.apply('ultra')
    assert s.appearance.brightness==.5


def test_seeded_columns_floor_shelves_mixed_and_existing_anchors():
    boxes=(((0,5,5),(10,6,1),(0,0,0)),)
    p=Appearance(column_count=4,column_placement='mixed')
    available=surfaces(boxes,p.column_placement)
    placed=place_emitters(p,available,lambda *args:True)
    assert len(placed)==4 and {item[0] for item in placed}=={'floor','shelf-0'}
    assert placed==place_emitters(p,available,lambda *args:True)
    assert placed==place_emitters(p,available,lambda *args:True,placed)
    assert placed!=place_emitters(replace(p,column_seed=42),available,lambda *args:True)
    assert not place_emitters(p,available,lambda *args:False)
    assert not place_emitters(replace(p,column_count=0),available,lambda *args:True)
    assert not place_emitters(p,surfaces((),'shelves'),lambda *args:True)
    assert len(place_emitters(replace(p,column_particles=2),available,lambda *args:True))==2
    # Removing a shelf retains valid floor anchors; no unsupported floating bases.
    moved=place_emitters(p,surfaces((),'mixed'),lambda *args:True,placed)
    assert moved[0]==placed[0] and all(item[0]=='floor' for item in moved)
