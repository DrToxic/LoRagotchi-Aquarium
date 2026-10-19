import math
import random
from dataclasses import replace
import pytest
from tank.deadzones import Deadzone, DisplayProfile, covered
from tank.swim_volume import SwimVolume
from tank.simulation import Simulation
from tank.demo import visitors


def configure(sim,regions,zones=(),constrain=True):
    v=sim.volume
    sim.set_view(v.origin,v.right,v.forward,v.up,v.tan_x,v.tan_x/(16/9),regions,zones,constrain)


def test_union_seams_allow_whole_fish_but_missing_corners_and_slivers_do_not():
    assert covered((-.1,.1,-.3,.3),[(-1,0,-1,1),(0,1,-1,1)])
    assert covered((-.2,.4,-.2,.4),[(-1,.1,-1,1),(0,1,-1,1)])
    assert not covered((-.2,.2,-.2,.2),[(-1,0,-1,1),(.00001,1,-1,1)])
    regions=[(-1,0,-1,0),(0,1,-.5,1)]
    assert not covered((-.1,.1,-.1,.1),regions)  # centre alone isn't sufficient
    assert covered((-.2,.2,-.4,-.2),regions)


@pytest.mark.parametrize('shape',['Rectangle','Rounded rectangle','Ellipse'])
def test_shapes_intersect_inside_and_edges_not_remote_water(shape):
    z=Deadzone(shape,25,25,50,50)
    assert z.intersects((-.1,.1,-.1,.1),16/9)
    assert z.intersects((.49,.6,-.1,.1),16/9)
    assert not z.intersects((.51,.6,-.1,.1),16/9)
    assert not replace(z,enabled=False).intersects((-.1,.1,-.1,.1))
    assert z.outline(16/9)[0]==pytest.approx(z.outline(16/9)[-1])
    assert z.intersects((.49,.5,.49,.5),16/9)==(shape=='Rectangle')


def test_profile_roundtrip_invalid_numbers_and_legacy_defaults(tmp_path):
    path=tmp_path/'display.json'
    assert DisplayProfile.load(path)==DisplayProfile()
    profile=DisplayProfile(False,[Deadzone('Ellipse',4,9,20,30,False)],[(-1920,-150,1920,1080),(0,0,2560,1440)])
    profile.save(path)
    assert DisplayProfile.load(path)==profile
    for text in ('{}','[]','{"version":1,"zones":[{"x":NaN}]}','{"version":1,"windows":[[0,0,-1,2]]}'):
        path.write_text(text)
        assert DisplayProfile.load(path)==DisplayProfile()
    for values in ((float('nan'),0,10,10),(0,0,float('inf'),10),(-1,0,10,10),(90,0,20,10),(0,0,0,10)):
        with pytest.raises(ValueError):Deadzone('Rectangle',*values)


def test_projected_sphere_encloses_sampled_surface_at_all_depths():
    v=SwimVolume();rng=random.Random(13)
    for _ in range(40):
        p=v.point(rng.uniform(-.9,.9),rng.uniform(-.8,.8),rng.uniform(24,42));r=rng.uniform(.4,2.1)
        x0,x1,y0,y1=v.footprint(p,r)
        for _ in range(100):
            direction=[rng.gauss(0,1) for i in range(3)];length=math.sqrt(sum(d*d for d in direction))
            u,w=v.project(tuple(a+r*b/length for a,b in zip(p,direction)))
            assert x0-1e-8<=u<=x1+1e-8 and y0-1e-8<=w<=y1+1e-8


def test_sweeps_block_tunneling_through_thin_gap_and_deadzones_at_depth():
    v=SwimVolume()
    v.configure(v.origin,v.right,v.forward,v.up,v.tan_x,v.tan_y,[(-1,-.001,-1,1),(.001,1,-1,1)])
    for depth in (25,32,40):
        a,b=v.point(-.5,0,depth),v.point(.5,0,depth)
        assert v.allows(a,.5) and v.allows(b,.5)
        assert not v.sweep_clear(a,b,.5) and not v.path_clear(a,b,.5)
    v.configure(v.origin,v.right,v.forward,v.up,v.tan_x,v.tan_y,[(-1,1,-1,1)],[Deadzone('Ellipse',40,40,20,20)])
    assert not v.path_clear(v.point(-.6,0,32),v.point(.6,0,32),.5)
    assert v.path_clear(v.point(-.6,.65,32),v.point(.6,.65,32),.5)


@pytest.mark.parametrize('regions,zones',[
    ([(-1,-.03,-1,.3),(.03,1,-.4,1)],[]),
    ([(-1,0,-1,.1),(0,1,-.6,1)],[Deadzone('Rounded rectangle',55,36,18,25)]),
    ([(-1,1,-1,1)],[Deadzone('Rectangle',20,20,15,35),Deadzone('Ellipse',60,40,25,35)]),
])
def test_simulated_fish_and_whole_outlines_never_enter_hidden_water(regions,zones):
    sim=Simulation(reefs=False);configure(sim,regions,zones);sim.roster(visitors(32))
    first=None
    for i in range(130):
        sim.step(.1)
        sides={}
        for key,s in sim.swimmers.items():
            assert not s.parked
            assert sim.volume.allows((s.x,s.y,s.z),s.outline)
            sides[key]=sim.volume.project((s.x,s.y,s.z))[0]>0
        if first is None:first=sides
        if regions[0][1]<0:assert sides==first  # no crossing disconnected windows
    assert len(sim.swimmers)==len(sim.physics.bodies)==32


def test_layout_changes_recover_hidden_fish_and_impossible_layout_keeps_identities():
    sim=Simulation(reefs=False);sim.roster(visitors(12));ids=set(sim.swimmers)
    configure(sim,[(-1,1,-1,1)],[Deadzone('Rectangle',0,0,100,100)])
    sim.step(.1)
    assert all(s.parked for s in sim.swimmers.values())
    assert set(sim.swimmers)==set(sim.physics.bodies)==ids
    configure(sim,[(-1,1,-1,1)])
    sim.step(.1)
    assert all(not s.parked and sim.volume.allows((s.x,s.y,s.z),s.outline) for s in sim.swimmers.values())
    assert set(sim.swimmers)==ids
    before={k:(s.x,s.y,s.z) for k,s in sim.swimmers.items()}
    configure(sim,[(-1,-.05,-1,1)])
    sim.step(.1)
    assert all(not s.parked and sim.volume.allows((s.x,s.y,s.z),s.outline) for s in sim.swimmers.values())
    assert any(math.dist(before[k],(s.x,s.y,s.z))>2 for k,s in sim.swimmers.items())


def test_startup_with_all_water_blocked_parks_arrivals_and_unparks_on_edit():
    sim=Simulation(reefs=False)
    configure(sim,[(-1,1,-1,1)],[Deadzone('Rectangle',0,0,100,100)])
    sim.roster(visitors(32));sim.step(.1)
    assert all(s.parked for s in sim.swimmers.values())
    assert len(sim.swimmers)==len(sim.physics.bodies)==32
    configure(sim,[(-1,1,-1,1)])
    sim.step(.1)
    assert all(not s.parked and sim.volume.allows((s.x,s.y,s.z),s.outline) for s in sim.swimmers.values())


@pytest.mark.parametrize('shape',['Rectangle','Rounded rectangle','Ellipse'])
def test_inversion_keeps_entire_footprint_inside_not_just_its_centre(shape):
    zone=Deadzone(shape,20,20,60,60,inverted=True)
    assert not zone.blocks((-.1,.1,-.1,.1),16/9)
    assert zone.blocks((-.8,-.7,0,.1),16/9)
    assert zone.blocks((-.1,.7,-.1,.1),16/9)
    assert zone.blocks((.58,.6,.58,.6),16/9)==(shape!='Rectangle')
    assert not replace(zone,enabled=False).blocks((-1,1,-1,1),16/9)
    assert replace(zone,blackout=True).blocks((-.1,.7,-.1,.1),16/9)


def test_old_saved_zones_default_to_no_blackout_or_inversion(tmp_path):
    path=tmp_path/'display.json'
    path.write_text('{"version":1,"zones":[{"shape":"Ellipse","x":10,"y":20,"width":60,"height":50,"enabled":true}]}')
    profile=DisplayProfile.load(path)
    assert len(profile.zones)==1
    assert not profile.zones[0].blackout and not profile.zones[0].inverted
    profile.zones[0]=replace(profile.zones[0],blackout=True,inverted=True)
    profile.save(path);assert DisplayProfile.load(path)==profile
    with pytest.raises(ValueError):Deadzone(blackout='true')
    with pytest.raises(ValueError):Deadzone(inverted=1)


def test_inverted_ellipse_with_additional_exclusion_retains_whole_fish_and_recovers():
    sim=Simulation(reefs=False)
    zones=[Deadzone('Ellipse',12,6,76,88,inverted=True,blackout=True),
           Deadzone('Rectangle',40,42,15,15,blackout=True)]
    configure(sim,[(-1,1,-1,1)],zones);sim.roster(visitors(32))
    for _ in range(130):
        sim.step(.1)
        assert all(not s.parked and sim.volume.allows((s.x,s.y,s.z),s.outline) for s in sim.swimmers.values())
    ids=set(sim.swimmers)
    configure(sim,[(-1,1,-1,1)],[Deadzone('Ellipse',0,0,20,20,inverted=True),Deadzone('Ellipse',80,80,20,20,inverted=True)])
    sim.step(.1)
    assert all(s.parked for s in sim.swimmers.values())
    configure(sim,[(-1,1,-1,1)],zones)
    sim.step(.1)
    assert set(sim.swimmers)==ids and all(not s.parked for s in sim.swimmers.values())
