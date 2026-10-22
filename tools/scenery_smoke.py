"""Native default-scene, checkbox, persistence and collision regression."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import time


def graph_stats(node):
    from panda3d.core import SceneGraphAnalyzer
    stats=SceneGraphAnalyzer();stats.addNode(node.node())
    return dict(geom_batches=stats.getNumGeoms(),vertices=stats.getNumVertices(),
                triangles=stats.getNumTris(),nodes=stats.getNumNodes())


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--quality',default='balanced')
    parser.add_argument('--managed',action='store_true')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    from tank.aquarium import Aquarium
    from tank.settings import Settings
    from tank.__main__ import main as run
    from tank.demo import visitors
    from tank.decoration_panel import scenery_category
    from panda3d.core import PNMImage

    def exercise(app):
        end=time.monotonic()+15
        while len(app.roster)!=12 and time.monotonic()<end:app.taskMgr.step()
        assert len(app.roster)==12
        app.taskMgr.remove('aquarium-update')
        objects=getattr(app,'placement',None) or app.scenery_objects
        assert app.settings.scene=='tidal-garden'
        assert len(app.plants)==app.settings.plants
        assert len([k for k,v in app.sim.physics.groups.items() if k.startswith('reef:') and v])==24
        assert not any(p.getName() in ('reef-rock','coral') for p in app.sim.physics.statics)
        def shot(name):
            for _ in range(3):app.graphicsEngine.renderFrame()
            app.graphicsEngine.syncFrame();image=PNMImage()
            assert app.aquarium_window.getScreenshot(image)
            assert image.write(str(args.output/(name+'.png')))
            return image
        app.update_fish(1/60)
        before=shot('tidal-garden')
        report={'quality':args.quality,'managed':args.managed,'default':'tidal-garden',
                'renderer':app.aquarium_window.getGsg().getDriverRenderer(),'categories':{},'checkboxes':[]}
        panel=None if args.managed else app.controls.decorations
        if panel:
            app.controls.page('Appearance');app.controls.appearance.page('Quality')
            widget=app.controls.appearance.fields['scene'][0]
            assert widget.get()=='Tidal Garden'
            widget.set('Classic',fCommand=0)
            assert app.controls.appearance.candidate().scene=='classic'
            assert app.controls.appearance.candidate().preset==app.settings.preset
            widget.set('Tidal Garden',fCommand=0)
            app.controls.page('Decorations')
        for category,prefix in (('Reef','reef:study:rock:'),('Plants','reef:study:grass:')):
            keys=[k for k in objects.records if scenery_category(k)==category]
            report['categories'][category]=len(keys)
            assert keys
            key=next(k for k in keys if k.startswith(prefix))
            if panel:
                panel.choose(category)
                assert set(panel.checks)==set(keys)
                check=panel.checks[key];assert check['indicatorValue']
                check.commandFunc(None)
                assert not check['indicatorValue']
            else:
                app.settings.scenery[key]=False;app.settings.save(app.args.settings)
                objects.set_enabled(key,False)
            assert not objects.records[key].enabled and not app.sim.physics.groups.get(key)
            assert Settings.load(app.args.settings).scenery[key] is False
            hidden=shot(category.lower()+'-hidden')
            if category=='Reef':
                assert sum(before.getXel(x,y)!=hidden.getXel(x,y) for y in range(before.getYSize()) for x in range(before.getXSize()))>100
            if panel:
                panel.refresh();assert not panel.checks[key]['indicatorValue']
                for _ in range(3):app.graphicsEngine.renderFrame()
                app.win.saveScreenshot(str(args.output/('checkboxes-'+category.lower()+'.png')))
            report['checkboxes'].append(key)
        # Both unchecked choices persist through quality rebuild, scene switching,
        # temporary zero plants and a fresh load from disk.
        swimmers=dict(app.sim.swimmers)
        hidden=dict(app.settings.scenery)
        original_count=app.settings.plants
        for scene,count in (('classic',original_count),('tidal-garden',0),('tidal-garden',original_count)):
            settings=deepcopy(app.settings);settings.scene=scene;settings.plants=count
            app.appearance.apply_settings(settings)
            if scene=='classic':assert any(k.startswith('reef:rock:') for k in objects.records)
            else:
                for key,value in hidden.items():
                    if key in objects.records:assert objects.records[key].enabled==value
            assert all(app.sim.swimmers[k] is v for k,v in swimmers.items())
            shot(scene+('-zero' if count==0 else ''))
        app.settings=Settings.load(app.args.settings);app.rebuild_scene()
        assert all(not objects.records[k].enabled for k in hidden)
        # Restore through the actual checkbox callback and verify solid ownership.
        for key in hidden:
            if panel:
                panel.choose(scenery_category(key));panel.checks[key].commandFunc(None)
            else:
                app.settings.scenery[key]=True;objects.set_enabled(key,True)
            assert objects.records[key].enabled
        assert len([k for k,v in app.sim.physics.groups.items() if k.startswith('reef:') and v])==24
        # Bounded dense-population motion with the production reef colliders.
        app.roster=list(visitors(256));app.sync_models()
        for _ in range(90):app.update_fish(1/60)
        assert len(app.sim.swimmers)==len(app.models)==256
        import math
        assert all(math.isfinite(v) for s in app.sim.swimmers.values() for v in (s.x,s.y,s.z,s.heading))
        count=len(app.sim.physics.statics)
        app.rebuild_scene();app.rebuild_scene()
        assert len(app.sim.physics.statics)==count
        shot('dense-256')
        report.update(persistence_and_scene_roundtrip=True,solid_groups=24,dense_fish=256,
                      stable_rebuild=True,stats=graph_stats(app.decor))
        (args.output/'report.json').write_text(json.dumps(report,indent=2))
        print('PASS default reef, category checkboxes, pixels, collisions, saved choices, Classic switch, 256 fish and rebuild cleanup',flush=True)
    with tempfile.TemporaryDirectory(prefix='scenery-proof-') as folder:
        settings=Settings();settings.apply(args.quality);settings.vsync=False;settings.fish_animations=False
        settings.appearance.caustics_speed=0
        settings.save(Path(folder)/'settings.json')
        Aquarium.run=exercise
        sys.argv=['scenery-smoke','--demo','12','--width','960','--height','540',
                  '--settings',str(Path(folder)/'settings.json'),'--no-vsync']
        if args.managed:sys.argv.append('--managed-settings')
        run()


if __name__=='__main__':main()
