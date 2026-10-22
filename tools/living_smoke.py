"""Isolated living-aquarium proof. No radio, no owner's settings or collection."""
import argparse
from dataclasses import asdict,replace
import json
import math
from pathlib import Path
import statistics
import sys
import tempfile
import time


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--managed',action='store_true');parser.add_argument('--quality',default='balanced')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    from tank.aquarium import Aquarium
    from tank.__main__ import main as run
    from tank.settings import Settings
    from tank.nursery import NurserySettings
    from tank.bubble_physics import object_origins
    from tank.demo import visitors
    from panda3d.core import ClockObject,PNMImage

    def exercise(app):
        deadline=time.monotonic()+10
        while len(app.roster)<12 and time.monotonic()<deadline:app.taskMgr.step()
        assert len(app.roster)==12
        app.taskMgr.remove('aquarium-update')
        clock=ClockObject.getGlobalClock();clock.setMode(ClockObject.MNonRealTime);clock.setDt(1/60)
        def capture(name,controls=False):
            for _ in range(3):app.graphicsEngine.renderFrame()
            image=PNMImage();app.graphicsEngine.syncFrame()
            assert (app.win if controls else app.aquarium_window).getScreenshot(image)
            image.write(str(args.output/(name+'.png')));return image
        def changed(a,b):
            return sum(a.getXel(x,y)!=b.getXel(x,y) for y in range(a.getYSize()) for x in range(a.getXSize()))
        report={'renderer':app.aquarium_window.getGsg().getDriverRenderer(),'managed':getattr(app,'managed',False),'quality':args.quality}
        app.columns.configure();assert len(app.columns.items)==300
        assert len(app.bubbles.items)==100
        origins=object_origins(app);assert origins
        owner=getattr(app,'placement',None) or app.scenery_objects
        key=origins[0][0].rsplit(':',1)[0]
        owner.set_enabled(key,False);app.columns.configure()
        assert not any(p[0].startswith(key+':') for p in object_origins(app))
        owner.set_enabled(key,True);app.columns.configure()
        assert len(app.columns.items)==300
        report['hidden_object_emitter_removed']=True
        # Frozen fish: alternate collisions on/off with identical particle start
        # states and settings. Report CPU update separately from full frame.
        measurements=[]
        for enabled in (False,True,False,True):
            p=app.settings.appearance;p.bubble_collisions=enabled
            app.columns.configure()
            for _ in range(180):app.columns.update(1/60);app.bubbles.update(1/60)
            update=[];frame=[]
            for _ in range(60):
                start=time.perf_counter();app.columns.update(1/60);app.bubbles.update(1/60)
                update.append((time.perf_counter()-start)*1000)
                app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
                frame.append((time.perf_counter()-start)*1000)
            measurements.append(dict(collisions=enabled,update_median_ms=statistics.median(update),update_p95_ms=sorted(update)[56],frame_median_ms=statistics.median(frame),frame_p95_ms=sorted(frame)[56]))
        report['bubble_300_plus_100']=measurements
        report['bubble_queries']=app.bubble_obstacles.queries;report['bubble_contacts']=app.bubble_obstacles.contacts
        # Isolate water pixels, then prove speed zero freezes geometry/opacity.
        p=app.settings.appearance;p.plant_sway=0;p.caustics_speed=0;p.background_motion='rays';p.background_speed=1
        app.appearance.update(0);before=capture('living-water-before')
        for _ in range(120):app.appearance.update(1/30)
        after=capture('living-water-after');report['water_changed_pixels']=changed(before,after)
        assert report['water_changed_pixels']>30
        p.background_speed=0;app.appearance.update(0);before=capture('living-water-frozen')
        app.appearance.update(4);after=capture('living-water-frozen-repeat')
        assert changed(before,after)==0
        report['zero_speed_pixel_identical']=True
        # Worker commits frozen parents and displays portraits; rename does not
        # rewrite them. This exercises the real worker, not test-only storage.
        adults=[f for f in app.roster if f.stage>=2]
        a,b=adults[:2]
        app.nursery.request_pair(a,b)
        for _ in range(5500):
            app.nursery.update(1/30);app.update_fish(1/30)
            if app.nursery.pending_request or app.nursery.eggs:break
        deadline=time.monotonic()+5
        while not app.nursery.eggs and time.monotonic()<deadline:
            app.nursery.update(.05);time.sleep(.01)
        if not app.nursery.eggs:
            print('PAIR DEBUG',[(f.name,vars(app.sim.swimmers[f.owner])) for f in (a,b)],tuple(app.nursery.root.getPos(app.scene)),flush=True)
        assert len(app.nursery.eggs)==1,app.nursery.status
        report['real_pair_reached_cave_and_stored']=True
        capture('living-cave-egg-parents')
        assert len(app.nursery.egg_root.findAllMatches('**/parent-portrait'))==2
        report['stored_eggs']=1;report['parent_portraits']=2
        if hasattr(app,'controls'):
            app.controls.page('Nursery');app.controls.nursery.refresh();capture('living-nursery-controls',True)
            app.controls.page('Appearance');app.controls.appearance.page('Bubbles');capture('living-bubble-controls',True)
        if hasattr(app,'controls'):
            app.controls.page('Games');panel=app.controls.games
            panel.new();panel.move.enterText('1');panel.play()
            assert panel.game.moves==['1']
            capture('living-games-controls',True)
        # Full simulation and resource lifecycle, including both scene choices.
        app.roster=list(visitors(256));app.sync_models();activities=set()
        for _ in range(300):
            app.update_fish(1/30)
            activities.update(s.activity for s in app.sim.swimmers.values())
        assert len(app.models)==len(app.sim.physics.bodies)==256
        assert len(activities)>=3
        report['dense_fish']=256;report['activities']=sorted(activities)
        counts=[]
        for scene in ('classic','tidal-garden','tidal-garden'):
            app.settings.scene=scene;app.rebuild_scene();app.columns.configure();app.bubble_obstacles.sync()
            counts.append(len(app.sim.physics.statics))
            assert len(app.models)==256
            assert len(app.nursery.eggs)==1
        assert counts[-1]==counts[-2]
        report['rebuild_static_counts']=counts
        report['limits']='Shared Linux Xvfb/llvmpipe timings, not HAOS or physical GPU performance. No live mesh test.'
        (args.output/'report.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2),flush=True)
    Aquarium.run=exercise
    with tempfile.TemporaryDirectory(prefix='aquarium-living-') as directory:
        settings=Settings();settings.apply(args.quality);settings.vsync=False;settings.fish_animations=False
        settings.bubbles=100;settings.appearance.column_count=8;settings.appearance.column_particles=300
        settings.appearance.column_placement='all';settings.appearance.fish_activity='lively'
        settings.appearance.background_motion='rays';settings.nursery=NurserySettings(True,False,6,30)
        path=Path(directory)/'settings.json';settings.save(path)
        sys.argv=['living-smoke','--demo','12','--settings',str(path),'--width','960','--height','540']
        if args.managed:sys.argv+=['--managed-settings']
        run()


if __name__=='__main__':main()
