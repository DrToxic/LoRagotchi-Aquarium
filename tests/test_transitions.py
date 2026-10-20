"""Real scene nodes, models and Bullet simulation; no display server required."""
from dataclasses import replace
import random
from types import MethodType, SimpleNamespace

import pytest
from panda3d.core import Filename, Loader, LoaderOptions, NodePath, Point2
from tank.aquarium import Aquarium
from tank.demo import events
from tank.protocol import Snapshot
from tank.framing import aim_at_sand
from tank.settings import Settings
from tank.simulation import Simulation
from tank.transitions import FishTransitions, STYLES, MAX_EXITS
from tank.views import desktop_lenses


class NativeLoader:
    def loadModel(self,path):
        return NodePath(Loader.getGlobalPtr().loadSync(Filename(path),LoaderOptions()))


@pytest.fixture
def app():
    render=NodePath("render")
    scene=render.attachNewNode("aquarium")
    camera=render.attachNewNode("camera");camera.setPos(0,-32,12)
    lens=desktop_lenses([(0,0,1280,720)])[0];aim_at_sand(camera,render,lens)
    app=SimpleNamespace(render=render,scene=scene,camera=camera,water_lens=lens,
        settings=Settings(detail=8),models={},_model_snapshots={},sim=Simulation(reefs=False),
        roster=[],loader=NativeLoader(),views=[SimpleNamespace(names=SimpleNamespace(sync=lambda fish:None))])
    app.transitions=FishTransitions(app,random.Random(1234))
    for name in ("sync_models","_sync_fish_nodes","update_fish"):
        setattr(app,name,MethodType(getattr(Aquarium,name),app))
    yield app
    app.transitions.destroy();render.removeNode()


def tick(app,seconds):
    for _ in range(round(seconds*20)):
        app.update_fish(.05)


def populate(app,count=1):
    app.roster=[f for f in events(count) if isinstance(f,Snapshot)]
    app.sync_models();tick(app,4.3)
    assert not app.transitions.arrivals
    return app.roster[0]


def test_arrival_comes_from_above_and_hands_over_without_teleport(app):
    app.roster=[f for f in events(1) if isinstance(f,Snapshot)];app.sync_models()
    owner=app.roster[0].owner
    app.transitions.arrivals[owner].time=0
    app.update_fish(0)
    node=app.models[owner][0];point=Point2()
    app.water_lens.project(app.camera.getRelativePoint(app.render,node.getPos()),point)
    assert point.y>1
    tick(app,2.)
    assert node.getZ()>app.sim.swimmers[owner].z
    tick(app,1.4)
    s=app.sim.swimmers[owner]
    assert (node.getPos()-app.sim.physics.bodies[owner].getPos()).length()<.001
    assert owner not in app.transitions.arrivals


def test_same_frame_reconciliation_does_not_accumulate_arrival_tilt(app):
    app.roster=[f for f in events(3) if isinstance(f,Snapshot)]
    app.sync_models();tick(app,1.)
    before={owner:tuple(model.getHpr()) for owner,(model,_,_) in app.models.items()}
    for _ in range(3):app.transitions.update(0)
    assert {owner:tuple(model.getHpr()) for owner,(model,_,_) in app.models.items()}==before


@pytest.mark.parametrize("style",STYLES)
def test_update_keeps_old_snapshot_until_exit_then_enters_latest(app,style):
    old=populate(app)
    app.settings.exit_styles={s:s==style for s in STYLES}
    model=app.models[old.owner][0]
    changed=replace(old,stage=3,body=4,name="Updated fish",event_id=old.event_id+1)
    app.roster=[changed];app.sync_models()
    assert app.models[old.owner][0]==model
    assert app.transitions.shown[old.owner]==old
    assert app.transitions.departures[old.owner].style==style
    assert old.owner not in app.sim.swimmers
    tick(app,3.8)
    assert app.transitions.shown[old.owner]==old
    # Late update is coalesced, not a second ghost or a restarted animation.
    latest=replace(changed,body=2,event_id=changed.event_id+1)
    app.roster=[latest];app.sync_models()
    assert len(app.transitions.departures)==1
    tick(app,2.7)
    assert app.transitions.shown[old.owner]==latest
    assert app.models[old.owner][0]!=model
    assert len(app.models)==1 and old.owner in app.transitions.arrivals
    tick(app,4.3)
    assert not app.transitions.departures and not app.transitions.arrivals
    assert len(app.sim.physics.bodies)==len(app.models)==1
    assert app.transitions.root.getNumChildren()==0


def test_identical_roster_does_not_replay_and_transport_refresh_does(app):
    old=populate(app);model=app.models[old.owner][0]
    for _ in range(5):app.sync_models()
    assert not app.transitions.departures and not app.transitions.arrivals
    assert app.models[old.owner][0]==model
    app.roster=[replace(old,event_id=old.event_id+1)]
    app.sync_models()
    assert old.owner in app.transitions.departures


def test_updates_during_entry_finish_entry_then_exit(app):
    old=[f for f in events(1) if isinstance(f,Snapshot)][0]
    app.roster=[old];app.sync_models();tick(app,.5)
    app.roster=[replace(old,body=5,event_id=old.event_id+1)]
    app.sync_models()
    assert not app.transitions.departures
    assert app.transitions.shown[old.owner]==old
    tick(app,3.8)
    assert old.owner in app.transitions.departures


def test_removal_cancels_pending_reentry(app):
    old=populate(app)
    app.roster=[replace(old,stage=3)];app.sync_models()
    tick(app,1.)
    app.roster=[];app.sync_models()
    tick(app,6.)
    assert not app.models and not app.sim.swimmers and not app.sim.physics.bodies
    assert not app.transitions.shown and app.transitions.root.getNumChildren()==0


def test_removed_owner_reshared_during_exit_reenters_once(app):
    old=populate(app)
    app.roster=[];app.sync_models();tick(app,2.)
    app.roster=[replace(old,name="Returned",event_id=99)];app.sync_models()
    tick(app,9.)
    assert len(app.models)==len(app.sim.swimmers)==1
    assert app.transitions.shown[old.owner].name=="Returned"
    assert not app.transitions.departures


def test_exit_queue_is_bounded_and_drains_with_no_ghosts(app):
    populate(app,12)
    app.roster=[];app.sync_models()
    assert len(app.transitions.departures)==MAX_EXITS
    assert len(app.sim.swimmers)==12-MAX_EXITS
    for _ in range(400):
        app.update_fish(.05)
        assert len(app.transitions.departures)<=MAX_EXITS
        assert app.transitions.root.getNumChildren()<=MAX_EXITS
    assert not app.models and not app.sim.physics.bodies and not app.transitions.shown


def test_disabling_mid_exit_applies_latest_and_releases_actors(app):
    old=populate(app);new=replace(old,body=5)
    app.roster=[new];app.sync_models();tick(app,3.)
    app.settings.fish_animations=False;app.sync_models();app.update_fish(.05)
    assert app.transitions.shown[old.owner]==new
    assert app.transitions.root.getNumChildren()==0
    assert not app.transitions.arrivals and not app.transitions.departures
    assert not app.models[old.owner][0].isHidden()


def test_all_styles_off_uses_upward_swim_and_settings_roundtrip(app,tmp_path):
    old=populate(app)
    app.settings.exit_styles={s:False for s in STYLES}
    app.settings.save(tmp_path/"settings.json")
    loaded=Settings.load(tmp_path/"settings.json")
    assert loaded.fish_animations and loaded.exit_styles==app.settings.exit_styles
    app.roster=[];app.sync_models()
    assert app.transitions.departures[old.owner].style=="swim"
    before=app.models[old.owner][0].getZ();tick(app,4.)
    assert app.models[old.owner][0].getZ()>before
    tick(app,3.)
    assert not app.models


def test_rebuilding_models_preserves_old_snapshot_and_sequence_clock(app):
    old=populate(app)
    app.roster=[replace(old,stage=3)];app.sync_models();tick(app,2.)
    state=app.transitions.departures[old.owner]
    for model,_,_ in app.models.values():model.removeNode()
    app.models={};app._model_snapshots={}
    app.settings.detail=12;app.sync_models();app.update_fish(0)
    assert app.transitions.departures[old.owner] is state
    assert state.time==pytest.approx(2.)
    assert app._model_snapshots[old.owner]==old
    tick(app,9.)
    assert app._model_snapshots[old.owner].stage==3


def test_no_views_hide_arrivals_and_parked_removal_does_not_make_a_pickup(app):
    old=populate(app)
    app.views=[]
    app.roster=[];app.sync_models()
    assert not app.models and not app.transitions.departures
    app.roster=[old];app.sync_models();tick(app,8.)
    assert old.owner in app.transitions.arrivals and app.models[old.owner][0].isHidden()


def test_same_names_remain_separate_owners(app):
    populate(app,2)
    first,second=app.roster
    app.roster=[replace(first,name="Same"),replace(second,name="Same")]
    app.sync_models();tick(app,11.)
    assert len(app.models)==2
    assert app.models[first.owner][0]!=app.models[second.owner][0]


def test_shelf_below_entry_requires_an_open_descent_column(app):
    app.roster=[f for f in events(1) if isinstance(f,Snapshot)];app.sync_models()
    owner=app.roster[0].owner
    s=app.sim.swimmers[owner];s.x,s.y,s.z=0,0,3
    app.sim.physics.bodies[owner].setPos(0,0,3)
    app.sim.physics.replace_boxes("test-shelf",[((0,0,8),(6,4,.6),(0,0,0))])
    app.transitions.arrivals[owner].time=0
    app.update_fish(0)
    state=app.transitions.arrivals[owner]
    assert state.landing is not None
    assert state.landing!=(0,0,3)
    assert app.transitions._clear_column(s,state.landing)
    tick(app,3.4)
    assert not s.arriving and not app.sim.physics.bodies[owner].node().isKinematic()


def test_all_exit_styles_are_reachable_with_seeded_randomness(app):
    seen=set()
    old=populate(app)
    for i in range(40):
        app.roster=[replace(old,event_id=100+i)]
        app.sync_models()
        seen.add(app.transitions.departures[old.owner].style)
        tick(app,11.)
    assert seen==set(STYLES)
