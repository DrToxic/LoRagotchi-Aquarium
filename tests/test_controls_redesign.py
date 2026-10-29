"""Headless behavioral checks for real editor methods, no GL/radio required."""
from copy import deepcopy
from types import SimpleNamespace
from tank.appearance_panel import AppearancePanel, GROUPS
from tank.appearance_editor import QUALITY
from tank.settings import Settings
from tank.controls_shell import NAVIGATION

class Field:
    def __init__(self,value):self.value=str(value);self.options={'items':[str(value)]}
    def get(self):return self.value
    def enterText(self,v):self.value=str(v)
    def set(self,v,**kw):self.value=str(v)
    def __getitem__(self,key):return self.options[key]
    def __setitem__(self,key,value):self.options[key]=value
    def resetFrameSize(self):pass
    def hide(self):pass
    def show(self):pass

def editor():
    p=AppearancePanel.__new__(AppearancePanel);p.app=SimpleNamespace(settings=Settings())
    keys={key for items in GROUPS.values() for key,_ in items}|{'fish_style'}
    p.fields={key:(Field(p.value(key)),False) for key in keys}
    for key in ('fog_enabled','lighting','caustics','vsync','bubble_collisions','bubble_dynamics'):
        p.fields[key][0].value='on' if p.value(key) else 'off'
    p.baseline={key:w.get() for key,(w,_) in p.fields.items()};p.active='Theme'
    p.dirty_label=Field('');p.note=Field('');p.reset_button=Field('');p.cancel_button=Field('');p.confirming=False
    p.theme_menu=Field('');return p

def test_all_features_have_stable_primary_routes():
    assert list(NAVIGATION)==['Overview','Appearance','Scenery & motion','Fish & nursery','Windows & layout','Radio & chat','Games','Performance']
    routes=[r for group in NAVIGATION.values() for r in group]
    assert len(routes)==len(set(routes))==12

def test_draft_scopes_and_external_changes_are_not_lost():
    p=editor();p.fields['brightness'][0].enterText('0.73')
    p.fields['fps'][0].enterText('44')
    p.app.settings.chat_bubbles=False;p.app.settings.nursery.capacity=7
    p.app.settings.appearance.background_top='#123456'
    candidate=p.candidate(False)
    assert candidate.appearance.brightness==.73 and candidate.fps==p.app.settings.fps
    assert candidate.chat_bubbles is False and candidate.nursery.capacity==7
    assert candidate.appearance.background_top=='#123456'
    candidate=p.candidate(True)
    assert candidate.fps==44 and candidate.appearance.brightness==p.app.settings.appearance.brightness
    assert p.app.settings.fps!=44

def test_invalid_draft_does_not_change_settings():
    p=editor();old=deepcopy(p.app.settings);p.fields['night_start'][0].enterText('not-a-time')
    import pytest
    with pytest.raises(ValueError):p.candidate(False)
    assert p.app.settings==old

def test_reset_requires_confirmation_and_cancel_retains_edits():
    p=editor();p.fields['brightness'][0].enterText('0.81');old=deepcopy(p.app.settings)
    p.reset();assert p.confirming and p.fields['brightness'][0].get()=='0.81'
    p.cancel_reset();assert not p.confirming and p.fields['brightness'][0].get()=='0.81'
    p.reset();p.reset();assert not p.confirming and not p.dirty and p.app.settings==old

def test_untouched_fields_rebase_without_replacing_drafts():
    p=editor();p.fields['brightness'][0].enterText('0.73')
    p.app.settings.appearance.fog_density=.025;p.update_dirty()
    assert p.fields['fog_density'][0].get()=='0.025'
    assert p.fields['brightness'][0].get()=='0.73'
    assert set(p.changes())=={'brightness'}

def test_classic_default_is_draft_only_and_preserves_other_scopes():
    p=editor();p.app.settings.appearance.brightness=.5;p.refresh();before=deepcopy(p.app.settings)
    p.draft_defaults();assert p.app.settings==before and p.dirty
    assert p.fields['brightness'][0].get()=='1.0'
    assert not p.changes(True)


def test_entry_focus_uses_live_native_state_not_stale_option():
    from tank.options import OptionsPanel
    panel=OptionsPanel.__new__(OptionsPanel)
    panel._close_dialog=None
    panel.entries=[SimpleNamespace(guiItem=SimpleNamespace(getFocus=lambda:True))]
    assert panel.editing()
    panel.entries=[];panel._close_dialog=object()
    assert panel.editing()
