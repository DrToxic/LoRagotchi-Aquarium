import math
from types import SimpleNamespace
import pytest
from tank.collision import CollisionWorld, body_dimensions
from tank.demo import visitors
from tank.simulation import Simulation
from tank.habitat import reef_rocks


def swimmer(x,y,z,heading=0):
    return SimpleNamespace(x=x,y=y,z=z,heading=heading,bank=0,vz=0,speed=1.)


def deepest(world, a, b):
    result=world.world.contactTestPair(a.node(),b.node())
    return min((c.getManifoldPoint().getDistance() for c in result.getContacts()),default=0.)


@pytest.mark.parametrize('stages',[(0,0),(2,2),(0,3)])
def test_head_on_bodies_do_not_pass_through_each_other(stages):
    world=CollisionWorld(reefs=False)
    fish={'a':swimmer(-3,0,7),'b':swimmer(3,0,7,math.pi)}
    for key,stage in zip(fish,stages):
        s=fish[key];world.add(key,stage,(s.x,s.y,s.z),s.heading)
    for _ in range(240):
        world.advance(fish,{'a':(1.5,0,0),'b':(-1.5,0,0)},1/60)
        assert fish['a'].x<fish['b'].x
        assert deepest(world,world.bodies['a'],world.bodies['b'])>-.04
    assert fish['b'].x-fish['a'].x>sum(body_dimensions(stage)[0]+body_dimensions(stage)[1]/2 for stage in stages)-.03


def test_floor_wall_and_solid_reef_have_contacts():
    world=CollisionWorld()
    rock=reef_rocks()[0][0]
    assert not world.clear_at(2,rock)
    assert world.clear_at(2,(0,0,7))
    fish={'a':swimmer(0,0,2)};world.add('a',2,(0,0,2),0)
    for _ in range(120):world.advance(fish,{'a':(0,0,-2)},1/60)
    assert fish['a'].z>=.25+body_dimensions(2)[0]-.025
    fish['a'].x=20;fish['a'].z=7
    for _ in range(120):world.advance(fish,{'a':(3,0,0)},1/60)
    radius,length=body_dimensions(2)
    assert fish['a'].x<=22-radius-length/2+.025


def test_crossing_and_depth_separated_paths_are_three_dimensional():
    world=CollisionWorld(reefs=False)
    fish={'a':swimmer(-3,0,7),'b':swimmer(0,-3,7,math.pi/2)}
    for key,s in fish.items():world.add(key,2,(s.x,s.y,s.z),s.heading)
    for _ in range(180):
        world.advance(fish,{'a':(1.5,0,0),'b':(0,1.5,0)},1/60)
        assert deepest(world,world.bodies['a'],world.bodies['b'])>-.04
    fish={'a':swimmer(-3,0,5),'b':swimmer(3,0,8,math.pi)}
    for key,s in fish.items():world.add(key,2,(s.x,s.y,s.z),s.heading)
    for _ in range(180):world.advance(fish,{'a':(1.5,0,0),'b':(-1.5,0,0)},1/60)
    assert fish['a'].x>fish['b'].x  # projected overlap at different depths is valid


def test_roster_refresh_resize_and_removal_keep_physics_in_sync():
    from dataclasses import replace
    sim=Simulation();fish=list(visitors(16));sim.roster(fish)
    state=sim.swimmers[fish[0].owner]
    original=sim.physics.bodies[fish[0].owner]
    sim.roster([replace(fish[0],name='new name'),*fish[1:]])
    assert sim.physics.bodies[fish[0].owner]==original
    sim.roster([replace(fish[0],stage=3),*fish[1:]])
    assert sim.swimmers[fish[0].owner] is state
    assert sim.physics.bodies[fish[0].owner]!=original
    sim.roster([])
    assert not sim.physics.bodies and not sim.swimmers


def test_dense_arrivals_start_without_body_intersections():
    sim=Simulation();sim.roster(visitors(256))
    keys=list(sim.swimmers)
    for i,key in enumerate(keys):
        a=sim.swimmers[key]
        for other in keys[i+1:]:
            b=sim.swimmers[other]
            if math.dist((a.x,a.y,a.z),(b.x,b.y,b.z))<3.:
                assert deepest(sim.physics,sim.physics.bodies[key],sim.physics.bodies[other])>-.001
