import json
from dataclasses import asdict
import pytest
from tank.settings import Settings, validate_setting
from tank.themes import apply, BUILTINS


def test_upgrade_defaults_and_explicit_classic_preserve_other_settings(tmp_path):
    path=tmp_path/'settings.json'
    raw={'plants':17,'fish_lifespan_hours':72,'decorations':{'pirate-ship':False},'future_key':42}
    path.write_text(json.dumps(raw))
    settings=Settings.load(path)
    assert settings.scene=='tidal-garden' and settings.plants==17
    assert json.loads(path.read_text())==raw
    settings.scene='classic';settings.scenery={'reef:study:rock:0':False,'reef:plant:2':False}
    settings.save(path);loaded=Settings.load(path)
    assert asdict(loaded)==asdict(settings)
    assert json.loads(path.read_text())['future_key']==42
    loaded.apply('low')
    themed=apply(loaded,BUILTINS['tropical'])
    assert themed.scene=='classic' and themed.scenery==settings.scenery
    assert themed.fish_lifespan_hours==72 and not themed.decorations['pirate-ship']


@pytest.mark.parametrize('key,value',[('scene','unknown'),('scene',False),('scenery',[]),('scenery',{'rock':'false'})])
def test_invalid_scene_settings_rejected(key,value):
    with pytest.raises(ValueError):validate_setting(key,value)
