from dataclasses import asdict, replace
import json
from pathlib import Path
import pytest
from tank.appearance import Appearance
from tank.settings import Settings
from tank.themes import BUILTINS,FIELDS,ThemeLibrary,apply,decode,encode,from_settings,manifest,resolve


def test_theme_does_not_touch_schedule_budgets_or_collection():
    settings=Settings(fish_lifespan_hours=24,fish_animations=False,detail=8,plants=0,bubbles=0,lighting=False,caustics=False)
    settings.appearance=Appearance(mode='clock',timezone='Europe/London',day_start='03:00',fog_enabled=False,shafts='off',column_count=9,column_particles=15)
    for raw in BUILTINS.values():
        result=apply(settings,raw)
        for key,value in asdict(settings).items():
            if key not in ('appearance','theme_id','fish_style'):assert asdict(result)[key]==value
        for key,value in asdict(settings.appearance).items():
            if key not in FIELDS:assert getattr(result.appearance,key)==value
        assert asdict(settings.appearance)['background_style']=='classic'
    assert resolve(BUILTINS['classic'])=={k:getattr(Appearance(),k) for k in FIELDS}


def test_roundtrip_and_collision_safe_write(tmp_path):
    library=ThemeLibrary(tmp_path)
    raw=from_settings(Settings(fish_style='rounded'),'my-lagoon','My lagoon')
    library.save(raw);assert library.read('my-lagoon')==raw
    assert decode(encode(raw))==raw
    changed={**raw,'name':'New name'}
    with pytest.raises(ValueError):library.save(changed)
    revision=library.revision(raw);library.save(changed,revision)
    with pytest.raises(ValueError):library.save(raw,revision)
    with pytest.raises(ValueError):library.save(BUILTINS['classic'])
    assert not list(tmp_path.glob('.theme-*'))
    assert set(json.loads(encode(raw)))=={'id','name','extends','schema_version','appearance','fish_style'}


@pytest.mark.parametrize('patch',[{'schema_version':True},{'schema_version':2},{'id':'../outside'},
    {'id':'a/b'},{'id':'A'},{'name':'\nname'},{'extends':'custom'},{'extends':['classic']},
    {'fish_style':'script'},{'assets':['https://example.test']},{'appearance':{'column_count':100}},
    {'appearance':{'brightness':float('nan')}},{'appearance':{'fog_colour':'red'}},
    {'appearance':{'brightness':True}},{'appearance':{'brightness':3}}])
def test_invalid_manifests(patch):
    with pytest.raises(ValueError):manifest({**BUILTINS['classic'],**patch})


def test_bad_theme_does_not_reset_settings_and_symlink_is_not_read(tmp_path):
    (tmp_path/'broken.json').write_text('{bad')
    outside=tmp_path/'secret';outside.write_text('not a theme')
    (tmp_path/'link.json').symlink_to(outside)
    library=ThemeLibrary(tmp_path);found,warnings=library.list()
    assert len(found)==6 and len(warnings)==2
    with pytest.raises(ValueError):library.read('link')
    with pytest.raises(ValueError):decode(b' '*16385)
    with pytest.raises(ValueError):library.read('../secret')
    settings=Settings(fish_style='faceted',theme_id='my-theme');path=tmp_path/'settings.json';settings.save(path)
    loaded=Settings.load(path);assert loaded.fish_style=='faceted' and loaded.theme_id=='my-theme'
    path.write_text(json.dumps({'fish_style':'bogus','fish_lifespan_hours':72,'appearance':{'mode':'clock'}}))
    loaded=Settings.load(path);assert loaded.fish_style=='classic' and loaded.fish_lifespan_hours==72 and loaded.appearance.mode=='clock'
