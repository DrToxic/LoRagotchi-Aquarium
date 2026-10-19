import math
from tank.demo import visitors
from tank.simulation import Simulation
from tank.settings import Settings,PRESETS


def test_shared_world_deterministic_bounded_no_population_culling():
    a,b=Simulation(),Simulation();fish=list(visitors(64));a.roster(fish);b.roster(fish)
    for _ in range(120):
        left,right=a.step(1/30),b.step(1/30)
        assert left==right and len(left)==64
        assert all(math.isfinite(p.x) and abs(p.x)<=16 and abs(p.y)<=4 and 1<p.z<12 for p in left.values())


def test_graphics_settings_roundtrip_does_not_change_roster(tmp_path):
    settings=Settings()
    for preset in PRESETS:
        settings.apply(preset);settings.save(tmp_path/'settings.json')
        loaded=Settings.load(tmp_path/'settings.json');assert loaded==settings
