"""Run native Aquarium roster, animation, replacement and cleanup under Xvfb."""
from dataclasses import replace
from pathlib import Path
import argparse
import sys
import tempfile
import time


def exercise(app):
    end=time.monotonic()+15
    while len(app.roster)!=1 and time.monotonic()<end: app.taskMgr.step()
    assert len(app.roster)==1
    app.service.close();app.taskMgr.remove('aquarium-update')
    seed=app.roster[0]
    roster=[replace(seed,owner=f'{i+1:064x}',name=f'Water {i}',species_id=i,
                    species_present=True,stage=2,body=i%6,scales=(i+2)%6) for i in range(14)]
    app.settings.fish_animations=False;app.roster=roster;app.sync_models()
    assert len(app.models)==len(app.sim.swimmers)==14
    for i,fish in enumerate(roster):
        model=app.models[fish.owner][0]
        assert (model.getTag('water-species')==str(i)) if i else not model.hasTag('water-species')
    for frame in range(240):app.update_fish(1/30)
    for _ in range(4):app.graphicsEngine.renderFrame()
    assert app.aquarium_window.saveScreenshot(str(OUTPUT/'native-water-aquarium.png'))
    target=roster[9];new=replace(target,species_id=11,body_gene=88,genes_present=True,event_id=target.event_id+1)
    app.settings.fish_animations=True;app.settings.exit_styles={key:False for key in app.settings.exit_styles}
    app.roster=[new if f.owner==target.owner else f for f in roster];app.sync_models()
    assert target.owner in app.transitions.departures
    seen_old=seen_new=False
    for _ in range(600):
        app.update_fish(1/30)
        shown=app.transitions.shown[target.owner]
        model=app.models[target.owner][0]
        assert model.getTag('water-species')==str(shown.species_id)
        seen_old |= shown==target;seen_new |= shown==new
        if seen_new and target.owner not in app.transitions.arrivals:break
    assert seen_old and seen_new and target.owner not in app.transitions.departures and target.owner not in app.transitions.arrivals
    assert len(app.models)==len(app.sim.swimmers)==14
    app.settings.fish_animations=False;app.roster=[];app.sync_models()
    assert not app.models and not app.sim.swimmers
    print('PASS: 14 Water models, 240 native updates, animated species replacement and full removal')


def main():
    global OUTPUT
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    OUTPUT=args.output;OUTPUT.mkdir(parents=True,exist_ok=True)
    from tank.aquarium import Aquarium
    from tank.__main__ import main as run
    from tank.settings import Settings
    Aquarium.run=exercise
    with tempfile.TemporaryDirectory(prefix='water-app-') as temp:
        path=Path(temp)/'settings.json';settings=Settings();settings.apply('low');settings.vsync=False;settings.fish_animations=False;settings.save(path)
        sys.argv=['water-aquarium','--demo','1','--width','960','--height','540','--settings',str(path)]
        run()

if __name__=='__main__':main()
