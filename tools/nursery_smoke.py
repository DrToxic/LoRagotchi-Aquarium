"""Isolated native nursery proof: real Panda menus, XTest clicks, worker and reload.

Run with tools/run_native.py tools.nursery_smoke --output <evidence directory>.
No radio, owner's settings, installed HA or live database is accessed.
"""
import argparse
import ctypes
import ctypes.util
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
import tempfile
import time


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--managed',action='store_true')
    parser.add_argument('--state-dir',type=Path)
    parser.add_argument('--reload',action='store_true')
    parser.add_argument('--clear-approach',action='store_true')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    from tank.aquarium import Aquarium
    from tank.__main__ import main as run
    from tank.settings import Settings
    from tank.nursery import NurserySettings, NurseryStore, NurseryWorker
    import tank.service
    def no_radio(*args,**kwargs):raise AssertionError('Nursery must not open a radio')
    tank.service.open_transport=no_radio

    def exercise(app):
        from panda3d.core import ClockObject
        clock=ClockObject.getGlobalClock();clock.setMode(ClockObject.MNonRealTime);clock.setDt(1/60)
        end=time.monotonic()+12
        while len(app.roster)!=12 and time.monotonic()<end:app.taskMgr.step()
        # Freeze swimming during native UI input so host render time cannot alter
        # the collision route under test; accelerate only the cave visit below.
        app.taskMgr.remove('aquarium-update')
        while app.nursery.pending_request and time.monotonic()<end:
            app.nursery.update(0);time.sleep(.01)
        assert len(app.roster)==12 and app.nursery.mode=='demo' and not app.nursery.pending_request
        if args.reload:
            expected=json.loads((Path(app.args.settings).parent/'expected-fry.json').read_text())
            assert len(app.nursery.fish)==1 and asdict(app.nursery.fish[0])=={**expected,'local_body_rgb':tuple(expected['local_body_rgb'])}
            assert len(app.roster)==13 and app.nursery.fish[0].owner in app.models
            assert not app.nursery.eggs
            for _ in range(10):app.graphicsEngine.renderFrame()
            assert app.aquarium_window.saveScreenshot(str(args.output/'restart-fry.png'))
            (args.output/'restart.json').write_text(json.dumps(dict(full_native_process_restart=True,fish=expected)))
            return
        roster=list(app.roster);adults=[f for f in roster if f.stage in (2,3)]
        report=dict(renderer=app.aquarium_window.getGsg().getDriverRenderer(),managed=args.managed)
        def clear_approach_fixture():
            # Test-only fixture: exercise descent/visit/commit from a known clear
            # approach, not the unrelated roaming planner's variable start pose.
            position=tuple(app.nursery.root.getPos(app.scene))
            for i,fish in enumerate(adults[:2]):
                s=app.sim.swimmers[fish.owner]
                s.x,s.y,s.z=position[0]+(i-.5)*2.2,position[1]-2.6,7.5
                app.sim.physics.bodies[fish.owner].setPos(s.x,s.y,s.z)
                assert app.sim.volume.path_clear((s.x,s.y,s.z),(s.x,s.y,position[2]+2.5),s.outline)
            report['test_only_clear_approach_fixture']=True
        def frames(n=5):
            for _ in range(n):
                app.taskMgr.step()
                if not args.managed:app.controls.refresh()
        def capture(name,controls=False):
            for _ in range(3):app.graphicsEngine.renderFrame()
            app.graphicsEngine.syncFrame()
            assert (app.win if controls else app.aquarium_window).saveScreenshot(str(args.output/(name+'.png')))
        if not args.managed:
            ui=app.controls;panel=ui.nursery;ui.page('Nursery');ui.viewport.verticalScroll['value']=0
            frames();panel.refresh()
            assert all('Demo (unowned)' in item for item in panel.first['items'])
            assert panel.first.selectedIndex==0 and panel.second.selectedIndex==1
            # Reproduce the old failing access using the actual installed widget.
            try:panel.first['selectedIndex']
            except KeyError:report['old_option_keyerror_reproduced']=True
            else:raise AssertionError('Old DirectOptionMenu option access unexpectedly works')
            # Exercise zero/one/invalid/stale paths through the real callback.
            for choices in ([],[adults[0]],[replace(adults[0],stage=0),replace(adults[1],stage=1)]):
                app.roster=choices;panel.refresh();panel.create['command']()
                assert not app.nursery.pending
            app.roster=adults[:2];panel.refresh()
            panel.first.selectedIndex=-1;panel.create['command']();assert not app.nursery.pending
            panel.first.selectedIndex=99;panel.create['command']();assert not app.nursery.pending
            panel.first.set(0,fCommand=0)
            app.roster=[replace(adults[0],name='stale'),adults[1]]
            panel.create['command']();assert not app.nursery.pending
            report['zero_one_juvenile_invalid_stale_callbacks_safe']=True
            app.roster=roster;panel.refresh()
            a=app.window_drag.pointer.api;display=app.window_drag.pointer.display
            assert display
            x=ctypes.CDLL(ctypes.util.find_library('Xtst'))
            x.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
            x.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
            a.XFlush.argtypes=[ctypes.c_void_p]
            a.XSetInputFocus.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
            def click(widget):
                l,r,b,t=widget['frameSize']
                point=app.pixel2d.getRelativePoint(widget,((l+r)/2,0,(b+t)/2))
                props=app.win.getProperties()
                a.XSetInputFocus(display,app.win.getWindowHandle().getIntHandle(),1,0)
                x.XTestFakeMotionEvent(display,-1,props.getXOrigin()+int(point.x),props.getYOrigin()-int(point.z),0)
                a.XFlush(display);frames()
                x.XTestFakeButtonEvent(display,1,1,0);a.XFlush(display);frames(2)
                x.XTestFakeButtonEvent(display,1,0,0);a.XFlush(display);frames(4)
            def choose(menu,index):
                # Real popup item receives native pointer press/release.
                menu.showPopupMenu();frames();click(menu.component('item%d'%index))
                assert menu.selectedIndex==index
            choose(panel.second,0)
            click(panel.create);assert not app.nursery.pending and 'different' in app.nursery.status
            report['duplicate_parent_native_click_safe']=True
            choose(panel.second,1)
            if args.clear_approach:clear_approach_fixture()
            capture('nursery-controls-before',True)
            click(panel.create);assert app.nursery.pending==tuple(adults[:2]),app.nursery.status
            report['actual_native_invite_click']=True
        else:
            if args.clear_approach:clear_approach_fixture()
            app.settings.nursery.automatic=True;app.nursery.next_attempt=0
            app.nursery.update(1/30)
            assert app.nursery.pending
            report['managed_automatic_pair']=True
        for _ in range(5500):
            app.nursery.update(1/30);app.update_fish(1/30)
            if app.nursery.pending_request or app.nursery.eggs:break
        end=time.monotonic()+5
        while not app.nursery.eggs and time.monotonic()<end:
            app.nursery.update(.05);time.sleep(.01)
        assert len(app.nursery.eggs)==1,(app.nursery.status,app.nursery.routes,app.nursery.visited)
        frozen=app.nursery.eggs[0]
        assert frozen['lineage']==dict(rule='demo-ancestry-v2',ancestry_depth=1,pet_generation=1)
        assert frozen['preview']['firmware_genome'] is None
        assert len(app.nursery.egg_root.findAllMatches('**/parent-portrait'))==2
        report['real_cave_visit_committed_local_egg']=True
        capture('nursery-egg-portraits')
        if not args.managed:
            panel.refresh();capture('nursery-controls-after',True)
        # Shut down the actual worker and reload the exact same durable store.
        app.nursery.worker.close();app.nursery.worker=NurseryWorker(app.args)
        app.nursery.mode=None;app.nursery.roster_mode('demo')
        end=time.monotonic()+5
        while app.nursery.pending_request and time.monotonic()<end:
            app.nursery.update(.01);time.sleep(.01)
        assert app.nursery.eggs==[frozen]
        report['worker_restart_exact_egg_reload']=True
        # A mode change during a pending demo visit cannot populate live storage.
        app.settings.nursery.automatic=False
        app.nursery.request_pair(*adults[:2]);app.nursery.roster_mode('live')
        assert app.nursery.pending is None and not app.nursery.eggs
        end=time.monotonic()+5
        while app.nursery.pending_request and time.monotonic()<end:
            app.nursery.update(.01);time.sleep(.01)
        assert app.nursery.eggs==[frozen]
        try:app.nursery.request_pair(*adults[:2])
        except ValueError as exc:assert 'Demo' in str(exc)
        else:raise AssertionError('Demo parents entered live nursery')
        live=NurseryStore(Path(app.args.settings).parent/'nursery-live.sqlite3',app.args.session)
        assert not live.eggs();live.close()
        app.nursery.roster_mode('demo')
        end=time.monotonic()+5
        while app.nursery.pending_request and time.monotonic()<end:
            app.nursery.update(.01);time.sleep(.01)
        assert app.nursery.eggs==[frozen]
        report['demo_live_eggs_shared_parents_isolated']=True
        if not args.managed:
            panel.refresh();ui.viewport.verticalScroll['value']=1;frames()
            choose(panel.egg,0);capture('nursery-hatch-controls',True)
            click(panel.hatch);assert app.nursery.pending_request
            report['actual_native_hatch_click']=True
        else:app.nursery.request_hatch(frozen['id'])
        end=time.monotonic()+5
        while app.nursery.pending_request and time.monotonic()<end:
            app.nursery.update(.01);time.sleep(.01)
        assert not app.nursery.eggs and len(app.nursery.fish)==1
        fry=app.nursery.fish[0]
        assert len(app.roster)==13 and fry.owner in app.models and fry.owner in app.sim.swimmers
        assert fry.stage==0 and fry.generation==1 and fry.lifetime_hours==0
        assert fry.local_body_rgb==tuple(frozen['preview']['body_rgb'])
        assert not app.nursery.egg_root.findAllMatches('**/parent-portrait')
        # Real application handler merges a new live roster, never a radio.
        live=replace(adults[0],owner='d'*64,rx='e'*64)
        app.service.events.put(dict(kind='roster',mode='live',fish=[live],lifespan=dict(hours=.001)))
        from types import SimpleNamespace
        app.update(SimpleNamespace(cont='cont'))
        end=time.monotonic()+5
        while app.nursery.pending_request and time.monotonic()<end:
            app.nursery.update(.01);time.sleep(.01)
        assert app.roster==[live,fry] and len(app.models)==2
        app.sim.time+=10**9
        for _ in range(100):app.nursery.update(.1);app.update_fish(.1)
        assert app.nursery.fish==[fry] and fry.stage==0 and fry.lifetime_hours==0
        try:app.nursery.request_pair(fry,live)
        except ValueError:pass
        else:raise AssertionError('Permanent fry bred')
        report['permanent_gen1_fry_with_live_visitor']=True
        app.selected=1
        if not args.managed:ui.page('Aquarium');ui.refresh();frames();capture('local-fry-selected',True)
        capture('local-fry-with-live')
        (Path(app.args.settings).parent/'expected-fry.json').write_text(json.dumps(asdict(fry)))
        report['fry_identity']=fry.owner
        report['limits']='Linux Xvfb/llvmpipe; actual native pair/hatch clicks; accelerated elapsed simulation, no teleport unless --clear-approach. No physical Windows/HAOS/radio test.'
        (args.output/'report.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2),flush=True)
    Aquarium.run=exercise
    from contextlib import nullcontext
    if args.state_dir:args.state_dir.mkdir(parents=True,exist_ok=True)
    with (nullcontext(str(args.state_dir)) if args.state_dir else tempfile.TemporaryDirectory(prefix='aquarium-nursery-proof-')) as directory:
        settings=Settings();settings.apply('low');settings.vsync=False;settings.fish_animations=False
        settings.nursery=NurserySettings(True,False,6,30)
        path=Path(directory)/'settings.json';settings.save(path)
        sys.argv=['nursery-smoke','--demo','12','--settings',str(path),'--database',str(Path(directory)/'demo.sqlite3'),'--width','960','--height','540']
        if args.managed:sys.argv+=['--managed-settings']
        run()


if __name__=='__main__':main()
