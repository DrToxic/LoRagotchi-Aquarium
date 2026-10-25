"""Prove juvenile mesh colours survive every pickup/arrival in the actual app."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time


def mesh_bytes(root):
    digest=hashlib.sha256()
    for node in root.findAllMatches('**/+GeomNode'):
        for index in range(node.node().getNumGeoms()):
            data=node.node().getGeom(index).getVertexData()
            for array in range(data.getNumArrays()):
                digest.update(data.getArray(array).getHandle().getData())
    return digest.hexdigest()


def exercise(app):
    from tank.art import fish_model
    from tank.transitions import STYLES
    end=time.monotonic()+15
    while len(app.roster)!=1 and time.monotonic()<end:app.taskMgr.step()
    assert len(app.roster)==1
    app.service.close();app.taskMgr.remove('aquarium-update')
    seed=app.roster[0];results=[]
    for stage in (0,1):
        for style in STYLES:
            old=replace(seed,stage=stage,body=5,scales=3,eyes=2,event_id=10)
            new=replace(old,body=0,scales=4,event_id=11)
            app.settings.fish_animations=False;app.roster=[old];app.sync_models()
            swimmer=app.sim.swimmers[old.owner]
            swimmer.x,swimmer.y,swimmer.z=0,-4,6;swimmer.heading=180
            app.sim.physics.bodies[old.owner].setPos(0,-4,6);app.update_fish(0)
            old_hash=mesh_bytes(app.models[old.owner][0])
            expected=fish_model(new,app.settings.detail,app.settings.fish_style)[0]
            new_hash=mesh_bytes(expected);expected.removeNode();assert old_hash!=new_hash
            app.settings.fish_animations=True;app.settings.exit_styles={key:key==style for key in STYLES}
            app.roster=[new];app.sync_models();assert old.owner in app.transitions.departures
            seen_old=seen_new=False
            for frame in range(510):
                app.update_fish(1/30)
                root,tail,fins=app.models[old.owner]
                shown=app.transitions.shown[old.owner]
                assert mesh_bytes(root)==(old_hash if shown==old else new_hash),(stage,style,frame)
                assert tail.getParent()==root and all(fin.getParent()==root for fin in fins)
                seen_old |= shown==old;seen_new |= shown==new
                if frame in (81,210):
                    for _ in range(2):app.graphicsEngine.renderFrame()
                    assert app.aquarium_window.saveScreenshot(str(OUTPUT/f'{stage}-{style}-{frame}.png'))
            assert seen_old and seen_new
            assert not app.transitions.departures and not app.transitions.arrivals
            results.append(dict(stage=stage,pickup=style,frames=510))
            print(f'PASS stage={stage} {style}: 510 moving frames, old/new colours and joints intact',flush=True)
    (OUTPUT/'lifecycle-report.json').write_text(json.dumps(dict(managed=getattr(app,'managed',False),cases=results),indent=2)+'\n')


def main():
    global OUTPUT
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--managed',action='store_true')
    args=parser.parse_args();OUTPUT=args.output;OUTPUT.mkdir(parents=True,exist_ok=True)
    from tank.aquarium import Aquarium
    from tank.__main__ import main as run
    from tank.settings import Settings
    Aquarium.run=exercise
    with tempfile.TemporaryDirectory(prefix='juvenile-lifecycle-') as temp:
        path=Path(temp)/'settings.json';settings=Settings();settings.apply('low');settings.vsync=False;settings.fish_animations=False;settings.save(path)
        sys.argv=['juvenile-lifecycle','--demo','1','--width','960','--height','540','--settings',str(path)]
        if args.managed:sys.argv+=['--managed-settings']
        run()


if __name__=='__main__':main()
