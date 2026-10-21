"""Real Bullet reservations and presentation lifecycle without a display server."""
from dataclasses import replace
import json
import pytest
from tank.deadzones import Deadzone, DisplayProfile
from tank.topology import WaterTopology
from tank.swim_volume import SwimVolume
from tank.travel import DURATION
from test_transitions import app, tick, populate


def volume(regions=((-1,1,-1,1),),zones=()):
    v=SwimVolume()
    v.configure(v.origin,v.right,v.forward,v.up,v.tan_x,v.tan_y,regions,zones,True)
    return v


@pytest.mark.parametrize('regions,count',[
    (((-1,0,-1,1),(0,1,-1,1)),1),
    (((-1,.1,-1,1),(-.1,1,-1,1)),1),
    (((-1,-.00001,-1,1),(.00001,1,-1,1)),2),
    (((-1,0,-1,0),(0,1,0,1)),2),
    (((-1,-.5,-1,1),(.5,1,-1,1),(-1,1,-1,-.8)),1),
])
def test_components_respect_seams_gaps_corners_and_u_shaped_layouts(regions,count):
    assert WaterTopology(volume(regions)).count==count


def test_split_window_thin_corridor_and_inverted_intersection():
    assert WaterTopology(volume(zones=[Deadzone(x=45,y=0,width=10,height=100)])).count==2
    # A very narrow real connection must not be erased by a coarse grid.
    assert WaterTopology(volume(zones=[Deadzone(x=45,y=.001,width=10,height=99.999)])).count==1
    v=volume(zones=[Deadzone('Ellipse',10,10,80,80,inverted=True),
                    Deadzone(x=45,y=0,width=10,height=100)])
    assert WaterTopology(v).count==2
    assert WaterTopology(volume(regions=())).count==0


def test_route_cannot_peek_into_an_unrelated_output():
    v=volume(((-1,-.5,-1,1),(-.2,.2,-1,1),(.5,1,-1,1)))
    topology=WaterTopology(v)
    area=topology.component(v.point(-.75,0,32))
    assert topology.count==3
    assert not topology.passage((-.8,.8,-.1,.1),area)
    assert topology.passage((-1.2,-.8,-.1,.1),area)


def prepare(app):
    old=populate(app)
    app.settings.fish_animations=False
    app.roster=[replace(old,stage=0)];app.sync_models()
    app.settings.fish_animations=True
    v=app.sim.volume
    app.sim.set_view(v.origin,v.right,v.forward,v.up,v.tan_x,v.tan_y,
                     ((-1,-.13,-1,1),(.13,1,-1,1)))
    s=app.sim.swimmers[old.owner]
    s.x,s.y,s.z=v.point(-.55,0,32)
    s.parked=False;s.heading=0
    app.sim.physics.bodies[old.owner].setPos(s.x,s.y,s.z)
    app.sim._layout_dirty=False
    app.display.transfers='Frequent';app.update_fish(0)
    return app.roster[0],app.transitions.travel


def test_transfer_preserves_identity_snapshot_and_body_and_releases_reservations(app):
    fish,travel=prepare(app);owner=fish.owner
    model=app.models[owner][0];s=app.sim.swimmers[owner];body=app.sim.physics.bodies[owner]
    original=(s.x,s.y,s.z)
    assert travel.start(owner)
    j=travel.active
    assert j.source.area!=j.target.area
    assert not travel.start(owner)
    tick(app,DURATION)
    assert travel.active.phase=='hidden' and model.isHidden()
    assert not travel.topology.visible(app.sim.volume.footprint(j.source.hidden,s.outline))
    tick(app,DURATION+.1)
    assert travel.completed==1 and travel.active is None
    assert app.models[owner][0]==model and app.sim.swimmers[owner] is s
    assert app.sim.physics.bodies[owner]==body
    assert app.roster==[fish] and app.transitions.shown[owner]==fish
    assert not s.arriving and not s.travelling and not body.node().isKinematic()
    assert j.reservation is None and not travel.start(owner)
    assert not app.sim.volume.path_clear(original,(s.x,s.y,s.z),s.outline)


def test_zero_delta_poses_and_unchanged_rosters_are_idempotent(app):
    fish,travel=prepare(app);assert travel.start(fish.owner);tick(app,1.)
    model=app.models[fish.owner][0];pose=model.getTransform();state=travel.active
    for _ in range(5):app.sync_models();app.update_fish(0)
    assert model.getTransform()==pose and travel.active is state
    assert not app.transitions.departures and not app.transitions.arrivals
    before=travel.solve_count;tick(app,1.)
    assert travel.solve_count==before


def test_both_routes_reserved_and_solid_obstacle_prevents_departure(app):
    fish,travel=prepare(app);assert travel.start(fish.owner)
    j=travel.active;s=app.sim.swimmers[fish.owner]
    assert not app.sim.physics.clear_at(s.stage,j.target.landing)
    # A real static obstruction, not merely the target point, blocks a route.
    travel.finish();travel.cooldowns.clear()
    app.sim.physics.replace_boxes('sealed', [((0,0,8),(60,40,30),(0,0,0))])
    assert not travel.start(fish.owner)
    assert not s.arriving and travel.active is None


@pytest.mark.parametrize('phase_time',[1.,4.,5.])
def test_real_removal_cancels_entry_and_leaks_nothing(app,phase_time):
    fish,travel=prepare(app);assert travel.start(fish.owner);tick(app,phase_time)
    j=travel.active;app.roster=[];app.sync_models();tick(app,.1)
    assert not app.models and not app.sim.swimmers and not app.sim.physics.bodies
    assert travel.active is None and j.reservation is None
    assert not app.transitions.shown


def test_updates_coalesce_while_hidden_and_entry_updates_wait(app):
    fish,travel=prepare(app);assert travel.start(fish.owner)
    model=app.models[fish.owner][0];swimmer=app.sim.swimmers[fish.owner]
    tick(app,1.)
    latest=replace(fish,body=5,name='Latest',event_id=900)
    app.roster=[latest];app.sync_models()
    assert app.models[fish.owner][0]==model and app.transitions.shown[fish.owner]==fish
    tick(app,3.1)
    assert app.transitions.shown[fish.owner]==latest
    assert app.models[fish.owner][0]!=model and app.sim.swimmers[fish.owner] is swimmer
    tick(app,.2)
    assert travel.active.phase=='entry'
    newer=replace(latest,body=3,event_id=901)
    app.roster=[newer];app.sync_models()
    assert app.transitions.shown[fish.owner]==latest
    tick(app,4.)
    assert fish.owner in app.transitions.departures
    tick(app,11.)
    assert app.transitions.shown[fish.owner]==newer
    assert travel.active is None and not app.sim.swimmers[fish.owner].arriving


def test_disable_scheduler_finishes_but_animation_optout_releases_now(app):
    fish,travel=prepare(app);assert travel.start(fish.owner);tick(app,1.)
    app.display.transfers='Off';tick(app,8.)
    assert travel.completed==1 and travel.active is None
    app.display.transfers='Frequent';travel.cooldowns.clear()
    assert travel.start(fish.owner);tick(app,2.)
    app.settings.fish_animations=False;app.sync_models();tick(app,.1)
    assert not travel.active and not app.sim.swimmers[fish.owner].arriving
    assert not app.sim.swimmers[fish.owner].travelling
    assert app.sim.volume.allows(tuple(app.models[fish.owner][0].getPos()),app.sim.swimmers[fish.owner].outline)


def test_close_every_view_and_reopen_recovers_without_losing_fish(app):
    fish,travel=prepare(app);assert travel.start(fish.owner);tick(app,2.)
    v=app.sim.volume;views=app.views;regions=v.regions
    app.views=[];app.sim.set_view(v.origin,v.right,v.forward,v.up,v.tan_x,v.tan_y,())
    tick(app,1.)
    assert travel.active.phase=='parked' and app.models[fish.owner][0].isHidden()
    app.views=views;app.sim.set_view(v.origin,v.right,v.forward,v.up,v.tan_x,v.tan_y,regions)
    tick(app,6.)
    assert travel.active is None and not app.sim.swimmers[fish.owner].parked
    assert app.transitions.shown[fish.owner]==fish


def test_blackout_portal_but_not_nonblackout_mask(app):
    fish,travel=prepare(app);s=app.sim.swimmers[fish.owner];v=app.sim.volume
    # An interior central keep-out divides a single output. Its opaque version
    # can hide a complete juvenile, its transparent version cannot.
    zone=Deadzone(x=35,y=0,width=30,height=100,blackout=True)
    app.sim.set_view(v.origin,v.right,v.forward,v.up,v.tan_x,v.tan_y,((-1,1,-1,1),),(zone,))
    travel.refresh();travel._owner=fish.owner
    hidden=v.point(0,0,32)
    assert not travel.topology.visible(v.footprint(hidden,s.outline))
    assert travel.topology.passage(v.footprint(hidden,s.outline),0)
    app.sim.set_view(v.origin,v.right,v.forward,v.up,v.tan_x,v.tan_y,((-1,1,-1,1),),(replace(zone,blackout=False),))
    travel.refresh()
    assert travel.topology.visible(v.footprint(hidden,s.outline))
    assert not travel.topology.passage(v.footprint(hidden,s.outline),0)


def test_transfer_preference_is_independent_and_old_profiles_default_off(tmp_path):
    path=tmp_path/'display.json'
    for value in ('Frequent','Occasional','Off',{},None,'broken'):
        path.write_text(json.dumps({'version':2,'constrain':False,'transfers':value}))
        profile=DisplayProfile.load(path)
        assert profile.transfers==(value if value in ('Frequent','Occasional','Off') else 'Off')
        assert not profile.constrain
    path.write_text(json.dumps({'version':1,'windows':[[0,0,640,480]]}))
    assert DisplayProfile.load(path).transfers=='Off'
    profile=DisplayProfile.load(path);profile.transfers='Frequent';profile.save(path)
    assert DisplayProfile.load(path).transfers=='Frequent'
    assert path.with_suffix('.v1.json').exists()


def test_hidden_stage_growth_replans_full_outline_and_preserves_swimmer(app):
    fish,travel=prepare(app);assert travel.start(fish.owner)
    s=app.sim.swimmers[fish.owner]
    app.roster=[replace(fish,stage=3,event_id=77)];app.sync_models();tick(app,10.)
    assert app.sim.swimmers[fish.owner] is s and s.stage==3
    assert not travel.active and not s.arriving and not s.travelling
    assert app.sim.volume.allows((s.x,s.y,s.z),s.outline)
    assert app.transitions.shown[fish.owner]==app.roster[0]


def test_mode_scheduling_and_reasons_are_bounded(app):
    fish,travel=prepare(app)
    travel.update(0)
    assert 20<=travel.next_attempt-travel.elapsed<=40
    before=travel.attempts;travel.update(.1)
    assert travel.attempts==before
    app.display.constrain=False
    assert not travel.start(fish.owner) and 'window-edge' in travel.reason()
    app.display.constrain=True;app.settings.fish_animations=False
    assert not travel.start(fish.owner) and 'animations' in travel.reason()
    app.settings.fish_animations=True;app.display.transfers='Off'
    travel.update(.1);assert travel.status=='Transfers off'


def test_destroy_releases_reservation_and_owned_hold(app):
    fish,travel=prepare(app);assert travel.start(fish.owner)
    j=travel.active;s=app.sim.swimmers[fish.owner]
    travel.destroy()
    assert j.reservation is None and travel.active is None
    assert not s.travelling and not s.arriving


def test_new_arrival_revalidates_reserved_route_before_relocation(app):
    fish,travel=prepare(app);assert travel.start(fish.owner);tick(app,.5)
    j=travel.active
    from tank.demo import visitors
    other=next(f for f in visitors(2) if f.owner!=fish.owner)
    app.roster=[fish,other];app.sync_models()
    # Model a dense incoming landing at the previously reserved destination.
    s=app.sim.swimmers[other.owner];s.x,s.y,s.z=j.target.landing
    app.sim.physics.bodies[other.owner].setPos(*j.target.landing)
    app.transitions._hold(other.owner,True)
    app.update_fish(.05)
    assert travel.active is None and j.reservation is None
    assert app.transitions.shown[fish.owner]==fish
    assert not app.sim.swimmers[fish.owner].travelling


def test_partial_exit_retreats_without_pose_snap_when_target_becomes_blocked(app):
    fish,travel=prepare(app);assert travel.start(fish.owner)
    s=app.sim.swimmers[fish.owner];model=app.models[fish.owner][0]
    for _ in range(79):
        app.update_fish(.05)
        if not app.sim.volume.allows(travel.active.position,s.outline):break
    j=travel.active
    assert j.phase=='exit' and travel.topology.visible(app.sim.volume.footprint(j.position,s.outline))
    before=model.getTransform()
    app.sim.physics.replace_boxes('new-target-obstacle',[(j.target.landing,(1,1,1),(0,0,0))])
    app.update_fish(0)
    assert travel.active.phase=='return' and model.getTransform()==before
    tick(app,4.)
    assert travel.active is None and travel.completed==0 and not s.arriving
    assert app.sim.volume.allows((s.x,s.y,s.z),s.outline)
