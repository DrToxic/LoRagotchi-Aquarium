import math
from tank.demo import visitors
from tank.simulation import Simulation
from tank.settings import Settings,PRESETS


def test_shared_world_deterministic_bounded_no_population_culling():
    a,b=Simulation(),Simulation();fish=list(visitors(64));a.roster(fish);b.roster(fish)
    for _ in range(120):
        left,right=a.step(1/30),b.step(1/30)
        assert left==right and len(left)==64
        assert all(math.isfinite(p.x) and abs(p.x)<=22 and -7<=p.y<=8 and .25<p.z<16 for p in left.values())


def test_graphics_settings_roundtrip_does_not_change_roster(tmp_path):
    settings=Settings()
    for preset in PRESETS:
        settings.apply(preset);settings.save(tmp_path/'settings.json')
        loaded=Settings.load(tmp_path/'settings.json');assert loaded==settings


def test_identity_refresh_keeps_motion_and_roster_order_does_not_change_it():
    from dataclasses import replace
    fish=list(visitors(16))
    a,b=Simulation(),Simulation();a.roster(fish);b.roster(reversed(fish))
    for _ in range(30):assert a.step(1/30)==b.step(1/30)
    before=a.swimmers[fish[0].owner]
    a.roster([replace(fish[0],name='Renamed'),*fish[1:]])
    assert a.swimmers[fish[0].owner] is before
    assert a.step(1/30)==b.step(1/30)
    a.roster(fish[1:])
    assert fish[0].owner not in a.swimmers


def test_dense_swimming_has_no_position_jumps_or_synchronised_orbit():
    sim=Simulation();sim.roster(visitors(256))
    old=sim.step(0)
    initial={key:(s.goal,s.pace) for key,s in sim.swimmers.items()}
    left=set();right=set();slow=set();fast=set()
    for _ in range(600):
        poses=sim.step(1/30)
        for key,p in poses.items():
            before=old[key]
            assert math.dist((p.x,p.y,p.z),(before.x,before.y,before.z)) < .15
            assert abs((p.heading-before.heading+180)%360-180) <= 1.7
            assert -22<=p.x<=22 and -7<=p.y<=8 and .25<=p.z<=16
            change=(p.heading-before.heading+180)%360-180
            if change<-.2:left.add(key)
            if change>.2:right.add(key)
            if p.speed<.3:slow.add(key)
            if p.speed>.8:fast.add(key)
        old=poses
    assert len(left & right)>200  # most fish turn both ways, not one shared orbit
    assert len(slow)>50 and len(fast)>50
    assert sum((s.goal,s.pace)!=initial[key] for key,s in sim.swimmers.items())>50
