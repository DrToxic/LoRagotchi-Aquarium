"""Actual Aquarium app: Anglerfish replacements, layouts, lighting and cleanup.

All state is synthetic and temporary. --managed exercises HA's read-only path.
"""
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
            for array in range(data.getNumArrays()):digest.update(data.getArray(array).getHandle().getData())
    return digest.hexdigest()


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--managed',action='store_true')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    from tank.aquarium import Aquarium
    from tank.__main__ import main as run
    from tank.settings import Settings
    from tank.art import fish_model
    from tank.transitions import STYLES
    from panda3d.core import ClockObject, WindowProperties

    def exercise(app):
        end=time.monotonic()+15
        while len(app.roster)!=16 and time.monotonic()<end:app.taskMgr.step()
        assert len(app.roster)==16
        assert sum(f.species_present and f.species_id==14 for f in app.roster)==4
        app.service.close();app.taskMgr.remove('aquarium-update')
        ClockObject.getGlobalClock().setMode(ClockObject.MNormal)
        def capture(name,window=None):
            for _ in range(3):app.graphicsEngine.renderFrame()
            app.graphicsEngine.syncFrame()
            texture=(window or app.aquarium_window).getScreenshot();assert texture
            assert texture.write(str(args.output/(name+'.png')))
            return bytes(texture.getRamImage())
        for _ in range(300):app.update_fish(1/30)
        capture('demo-16-native')
        if hasattr(app,'controls'):capture('native-controls',app.win)
        seed=app.roster[-1];results=[]
        for stage in range(4):
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
                app.settings.fish_animations=True
                app.settings.exit_styles={key:key==style for key in STYLES}
                app.roster=[new];app.sync_models();assert old.owner in app.transitions.departures
                seen_old=seen_new=False;lure_angles=set()
                for frame in range(510):
                    app.update_fish(1/30)
                    root,tail,fins=app.models[old.owner]
                    shown=app.transitions.shown[old.owner]
                    assert mesh_bytes(root)==(old_hash if shown==old else new_hash),(stage,style,frame)
                    assert root.getTag('fish-species')=='14'
                    assert tail.getParent()==root and all(fin.getParent()==root for fin in fins)
                    lure_angles.add(round(root.find('angler-lure-joint').getH(),3))
                    seen_old|=shown==old;seen_new|=shown==new
                    if stage==2 and frame in (81,210):capture(f'adult-{style}-{frame}')
                assert seen_old and seen_new and len(lure_angles)>20
                assert not app.transitions.departures and not app.transitions.arrivals
                results.append(dict(stage=stage,pickup=style,frames=510,lure_angles=len(lure_angles)))
                print(f'PASS stage={stage} {style}: 510 frames, genes/joints/lure + replacement',flush=True)
        # Mesh-only restyle and scenery rebuild retain the shown full identity.
        app.settings.fish_animations=False;app.sync_models()
        owner=app.roster[0].owner
        for style in ('rounded','faceted','classic'):
            app.settings.fish_style=style;app.restyle_fish();app.update_fish(.05)
            assert set(app.models)=={owner} and app.models[owner][0].getTag('fish-species')=='14'
        app.rebuild_scene();app.update_fish(.05)
        assert set(app.models)=={owner}
        # Actual appearance and native output setup, not a separate scene mock.
        p=app.settings.appearance;p.mode='static';p.day_brightness=.2
        app.appearance.update(0,force=True);capture('night-lure')
        p.day_brightness=0;app.appearance.update(0,force=True);capture('blackout')
        p.day_brightness=1;app.appearance.update(0,force=True)
        before=app.models[owner][0].node()
        props=WindowProperties();props.setSize(840,540);app.aquarium_window.requestProperties(props)
        for _ in range(3):app.graphicsEngine.renderFrame()
        app.setup_output();capture('resized')
        if not getattr(app,'managed',False):
            app.add_window((1100,40,640,480));app.setup_output();app.update_fish(.05)
            capture('second-output',app.views[-1].window)
            app.close_view(app.views[0]);capture('survivor-output')
            for _ in range(3):
                app.add_window((1100,40,640,480));app.close_view(app.views[-1])
            assert len(app.views)==1
        assert app.models[owner][0].node()==before
        app.roster=[];app.sync_models()
        assert not app.models and not app.sim.swimmers
        assert not app.scene.findAllMatches('**/angler-lure-joint').getNumPaths()
        app.roster=[seed];app.sync_models();app.update_fish(.05)
        assert len(app.models)==1
        report=dict(managed=getattr(app,'managed',False),renderer=app.aquarium_window.getGsg().getDriverRenderer(),
                    cases=results,rebuild_restyle=True,resize=True,secondary_lifecycle=not args.managed,
                    removal_and_reentry=True,nursery_enabled=app.settings.nursery.enabled)
        (args.output/'lifecycle-report.json').write_text(json.dumps(report,indent=2)+'\n')
    Aquarium.run=exercise
    with tempfile.TemporaryDirectory(prefix='angler-lifecycle-') as temporary:
        path=Path(temporary)/'settings.json';settings=Settings();settings.apply('low')
        settings.vsync=False;settings.fish_animations=False;settings.save(path)
        sys.argv=['anglerfish-lifecycle','--demo','16','--width','960','--height','540','--settings',str(path)]
        if args.managed:sys.argv+=['--managed-settings']
        run()


if __name__=='__main__':main()
