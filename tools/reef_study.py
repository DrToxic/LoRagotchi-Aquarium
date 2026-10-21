"""Opt-in native reef study. Demo-only, isolated settings, no radio or live store.

uv run python -m tools.reef_study --interactive
uv run python tools/run_native.py tools.reef_study --output .local/reef-study
The default probe compares the same frozen fish/camera/lighting against Classic.
"""
import argparse
import json
import math
from pathlib import Path
import statistics
import sys
import tempfile
import time


def graph_stats(node):
    from panda3d.core import SceneGraphAnalyzer
    stats=SceneGraphAnalyzer();stats.addNode(node.node())
    return dict(geom_batches=stats.getNumGeoms(),vertices=stats.getNumVertices(),
                triangles=stats.getNumTris(),nodes=stats.getNumNodes())


def rss_mib():
    try:
        for line in Path('/proc/self/status').read_text().splitlines():
            if line.startswith('VmRSS:'):return round(int(line.split()[1])/1024,2)
    except OSError:pass
    return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interactive',action='store_true')
    parser.add_argument('--scene',choices=('reef','classic'),default='reef')
    parser.add_argument('--quality',choices=('compatibility','low','balanced','high'),default='balanced')
    parser.add_argument('--output',type=Path,default=Path('.local/reef-study'))
    parser.add_argument('--width',type=int,default=1280);parser.add_argument('--height',type=int,default=720)
    parser.add_argument('--samples',type=int,default=40)
    args=parser.parse_args()
    if args.samples<10:parser.error('--samples must be at least 10')
    args.output.mkdir(parents=True,exist_ok=True)
    from panda3d.core import ClockObject,PNMImage
    import tank.aquarium as aquarium
    from tank.art import scenery as classic
    from tank.reef_art import scenery as reef
    from tank.settings import Settings
    from tank.simulation import Pose
    from tank.__main__ import main as run
    scenes={'classic':classic,'reef':reef}
    aquarium.scenery=scenes[args.scene]
    report={'study':'Tidal Garden','quality':args.quality,'resolution':[args.width,args.height],
            'limits':'Linux Xvfb/Mesa host probe, not Windows/GPU/HAOS acceptance. Geom counts are scene-graph batches, not measured driver draw calls.',
            'samples_per_pass':args.samples,'fish':12,'passes':[]}

    def exercise(app):
        deadline=time.monotonic()+15
        while len(app.roster)!=12 and time.monotonic()<deadline:app.taskMgr.step()
        assert len(app.roster)==12
        app.taskMgr.remove('aquarium-update')
        clock=ClockObject.getGlobalClock();clock.setMode(ClockObject.MNonRealTime);clock.setDt(1/60)
        report['renderer']=app.aquarium_window.getGsg().getDriverRenderer()
        report['internal_resolution']=list(app.internal_size)
        # Capture and compare a fixed composition; never time two different shoals.
        locations=((-5,0,9),(2,2,11),(7,-2,7),(-1,1,5),(-8,-2,6),(11,-1,9),
                   (-14,-2,11),(5,-3,3),(-3,4,7),(15,0,7),(0,-2,9),(8,4,11))
        poses={fish.owner:Pose(*locations[i],(-1 if i%2 else 1)*10+(180 if i%3==0 else 0),0,0,i*.8,.7)
               for i,fish in enumerate(app.roster)}
        snapshots=list(app.roster)
        step=app.sim.step
        app.sim.step=lambda dt:poses
        def capture(name):
            for _ in range(3):app.graphicsEngine.renderFrame()
            image=PNMImage();assert app.aquarium_window.getScreenshot(image)
            image.write(str(args.output/(name+'.png')))
            return image
        def draw():
            app.update_fish(1/60);app.appearance.update(0);app.graphicsEngine.renderFrame()
            # Explicit completion makes software-GL timings full synchronous frames.
            app.graphicsEngine.syncFrame()
        images={};repeat=[];frozen_pose=None
        for index,scene in enumerate(('classic','reef','classic','reef')):
            aquarium.scenery=scenes[scene];app.rebuild_scene()
            clock.setMode(ClockObject.MNonRealTime);clock.setDt(1/60)
            for _ in range(12):draw()
            pose_state={key:(tuple(value[0].getPos()),tuple(value[0].getHpr()),value[0].isHidden()) for key,value in app.models.items()}
            if frozen_pose is not None:assert pose_state==frozen_pose,'Frozen comparison moved or hid fish'
            frozen_pose=pose_state
            image=capture(f'{scene}-{index}')
            image.write(str(args.output/(scene+'.png')))
            if scene in images:
                old=images[scene];changed=0;error=0.
                for y in range(image.getYSize()):
                    for x in range(image.getXSize()):
                        delta=image.getXel(x,y)-old.getXel(x,y)
                        if delta.lengthSquared()>0:
                            changed+=1;error+=sum(abs(v) for v in delta)
                total=image.getXSize()*image.getYSize()
                repeat.append(dict(scene=scene,changed_pixels=changed,total_pixels=total,mean_rgb_error=error/(total*3)))
                # Intersecting static meshes can tie on depth at a few pixels
                # after batching. A structural change is not accepted as jitter.
                assert changed/total<.0001 and error/(total*3)<.00001,repeat[-1]
                if scene=='classic':assert changed==0
            images[scene]=PNMImage(image)
            updates=[];frames=[]
            for _ in range(args.samples):
                started=time.perf_counter();app.update_fish(1/60);app.appearance.update(0)
                updates.append((time.perf_counter()-started)*1000)
                app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
                frames.append((time.perf_counter()-started)*1000)
            result=dict(scene=scene,pass_index=index,update_median_ms=round(statistics.median(updates),3),
                        frame_median_ms=round(statistics.median(frames),3),frame_p95_ms=round(sorted(frames)[math.ceil(len(frames)*.95)-1],3),
                        scene_graph=graph_stats(app.scene),scenery_graph=graph_stats(app.decor),
                        rss_mib=rss_mib(),animated_plants=len(app.plants),
                        placements=len(app.placement.records),visible_placements=sum(r.visible for r in app.placement.records.values()))
            report['passes'].append(result);print(json.dumps(result),flush=True)
            assert app.roster==snapshots and len(app.models)==len(app.sim.swimmers)==12
        report['repeat_pixels']=repeat
        report['identical_fish_poses_across_scenes']=True
        # Same actual renderer at night; effects are dimmed by existing controls.
        app.appearance.preview=0
        app.appearance.update(0,force=True)
        night=capture('reef-night')
        assert night.getAverageGray()<images['reef'].getAverageGray()*.5
        report['night_mean_luminance']=night.getAverageGray()
        report['day_mean_luminance']=images['reef'].getAverageGray()
        app.appearance.preview=1
        app.appearance.update(0,force=True)
        # Runtime motion uses real simulation; matched solid proxies remain attached.
        app.sim.step=step
        for _ in range(180):app.update_fish(1/30)
        for owner,swimmer in app.sim.swimmers.items():
            assert all(math.isfinite(v) for v in app.models[owner][0].getPos())
        capture('reef-moving')
        report['motion_steps']=180
        report['proxy_groups']=len([k for k,v in app.sim.physics.groups.items() if k.startswith('reef:study:') and v])
        report['fish_preserved']=app.roster==snapshots
        assert report['proxy_groups']==24
        assert len(app.models)==len(app.sim.swimmers)==12
        # Masks use the same production placement path, including collider cleanup.
        from tank.deadzones import Deadzone
        model_nodes={k:v[0].node() for k,v in app.models.items()}
        for zone in (Deadzone(x=0,y=55,width=30,height=45),Deadzone(x=0,y=0,width=100,height=100)):
            app.display.zones=[zone];app.setup_output()
            for record in app.placement.records.values():
                if record.visible:assert app.placement.snapshot.clear_bounds(*record.bounds(record.position)),record.key
                else:assert not app.sim.physics.groups.get(record.key),record.key
        assert not any(app.sim.physics.groups.values())
        app.display.zones=[];app.setup_output()
        assert model_nodes=={k:v[0].node() for k,v in app.models.items()}
        assert len([v for k,v in app.sim.physics.groups.items() if k.startswith('reef:study:') and v])==24
        report['mask_and_restore_checks']=2
        # Dense roster is simulation/collision proof, not an FPS benchmark.
        from tank.demo import visitors
        app.roster=list(visitors(256));app.sync_models()
        for _ in range(60):app.update_fish(1/30)
        assert len(app.models)==len(app.sim.swimmers)==len(app.sim.physics.bodies)==256
        assert all(all(math.isfinite(v) for v in model[0].getPos()) for model in app.models.values())
        report['dense_fish']=256;report['dense_steps']=60
        before=len(app.sim.physics.statics)
        for _ in range(2):
            app.rebuild_scene()
            assert len(app.sim.physics.statics)==before
            assert len(app.models)==len(app.sim.swimmers)==256
        report['rebuilds_without_proxy_growth']=2
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    if not args.interactive:aquarium.Aquarium.run=exercise
    # Explicitly off for both sides of the comparison: this is a natural reef,
    # not a pirate-wreck redesign. No changes to real preferences are persisted.
    with tempfile.TemporaryDirectory(prefix='reef-study-',dir=args.output.resolve()) as directory:
        settings=Settings();settings.apply(args.quality);settings.vsync=False
        settings.scale=1;settings.fish_animations=False;settings.show_names=False
        from tank.decorations import discover
        settings.decorations={item.key:False for item in discover()[0]}
        settings.appearance.background_style='gradient'
        settings.appearance.background_top='#286A76';settings.appearance.background_bottom='#061E2D'
        settings.appearance.fog_colour='#16434D';settings.appearance.fog_density=.010
        settings.appearance.sand_tint='#DAD0AF';settings.appearance.shafts_strength=.55
        settings.appearance.caustics_strength=.55
        settings.appearance.night_brightness=.34
        settings.save(Path(directory)/'settings.json')
        sys.argv=['reef-study','--demo','12','--settings',str(Path(directory)/'settings.json'),
                  '--width',str(args.width),'--height',str(args.height)]
        run()


if __name__=='__main__':main()
