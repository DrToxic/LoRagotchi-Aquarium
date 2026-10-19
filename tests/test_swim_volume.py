import math
import random
from tank.demo import visitors
from tank.simulation import Simulation
from tank.swim_volume import SwimVolume
from tank.habitat import TANK_LIMITS


def test_visible_goals_follow_wide_and_offset_view_regions():
    volume=SwimVolume();rng=random.Random(37)
    for aspect,regions in [(16/9,((-1,1,-1,1),)),(4480/1440,((-1,.14,-1,1),(.14,1,-.75,.75)))]:
        volume.configure(volume.origin,volume.right,volume.forward,volume.up,
                         math.tan(math.pi/6),math.tan(math.pi/6)/aspect,regions)
        points=[volume.candidate(rng,1.1) for _ in range(100)]
        assert all(point is not None for point in points)
        for point in points:
            u,v=volume.project(point)
            assert -.91<u<.91 and -.87<v<.91
            assert any(left<=u<=right and bottom<=v<=top for left,right,bottom,top in regions)
            assert all(low+1.1<=p<=high-1.1 for p,(low,high) in zip(point,TANK_LIMITS))


def test_view_change_replans_without_teleport_or_identity_reset():
    sim=Simulation();sim.roster(visitors(32));before=sim.step(0)
    bodies=dict(sim.physics.bodies)
    volume=sim.volume
    sim.set_view(volume.origin,volume.right,volume.forward,volume.up,
                 volume.tan_x,volume.tan_x/3.1,((-1,1,-1,1),))
    assert sim.step(0)==before and sim.physics.bodies==bodies


def test_roaming_populates_edges_and_upper_water_after_warmup():
    sim=Simulation();sim.roster(visitors(128));samples=[]
    for i in range(450):
        poses=sim.step(.1)
        if i>=200 and i%10==0:samples.extend(poses.values())
    assert sum(abs(p.x)>10 for p in samples)/len(samples)>.20
    assert sum(p.z>9 for p in samples)/len(samples)>.12
    assert len(sim.physics.bodies)==128
