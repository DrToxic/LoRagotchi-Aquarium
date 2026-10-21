"""Actual output pixels and interruption recovery for desktop fish transfers."""
from dataclasses import replace
from pathlib import Path
import json
import tempfile
import time


def exercise(app):
    from panda3d.core import ClockObject, PNMImage, WindowProperties
    from tank.deadzones import Deadzone, DisplayProfile
    from tools.render_smoke import settle
    out=Path('.local/transfers');out.mkdir(parents=True,exist_ok=True)
    deadline=time.monotonic()+15
    while len(app.roster)!=1 and time.monotonic()<deadline:app.taskMgr.step()
    assert len(app.roster)==1
    app.service.close();app.taskMgr.remove('aquarium-update')
    ClockObject.getGlobalClock().setMode(ClockObject.MNormal)
    app.roster=[replace(app.roster[0],stage=0,name='Panoramic traveller')]
    app.sync_models();app.settings.fish_animations=True
    owner=app.roster[0].owner;fish=app.roster[0]
    app.show_names=False
    first=app.views[0]
    props=WindowProperties();props.setOrigin(520,32);props.setSize(640,720)
    first.window.requestProperties(props);settle(app)
    second=app.add_window((1320,32,640,720));settle(app)
    app.display.transfers='Frequent'
    travel=app.transitions.travel
    s=app.sim.swimmers[owner]
    report={'renderer':first.window.getGsg().getDriverRenderer(),'pixels':[], 'checks':[], 'attempt_ms':[]}

    def advance(seconds):
        for _ in range(round(seconds*30)):app.update_fish(1/30)

    def start():
        travel.finish(restore=True);travel.cooldowns.clear()
        v=app.sim.volume
        for u,w,d in [(-.62,.25,30),(-.62,0,30),(-.6,.45,32),(-.7,.2,34)]:
            s.x,s.y,s.z=v.point(u,w,d);s.heading=0;s.parked=False
            app.sim.physics.bodies[owner].setPos(s.x,s.y,s.z)
            app.sim._layout_dirty=False;app.update_fish(0)
            started=time.perf_counter();accepted=travel.start(owner)
            report['attempt_ms'].append((time.perf_counter()-started)*1000)
            if accepted:return
        raise AssertionError(('no native transfer route',travel.status))

    def capture(name=None):
        for _ in range(3):app.graphicsEngine.renderFrame()
        counts=[]
        for i,view in enumerate(app.views):
            im=PNMImage();assert view.window.getScreenshot(im)
            if name:im.write(str(out/f'{name}-{i}.png'))
            count=sum(1 for y in range(1,im.getYSize(),2) for x in range(1,im.getXSize(),2)
                      if im.getRed(x,y)>.8 and im.getGreen(x,y)<.2 and im.getBlue(x,y)>.8)
            counts.append(count)
        return counts

    model=app.models[owner][0];body=app.sim.physics.bodies[owner]
    model.setColor(1,0,1,1,100);model.setLightOff(100);model.setFogOff(100)
    start();j=travel.active
    assert j.source.area!=j.target.area
    for phase in ('exit','entry'):
        counts=[]
        if phase=='entry':advance(1/30)
        for i in range(12):
            advance(1/3)
            seen=capture(phase+'-mid' if i==5 else None)
            counts.append(seen)
            assert seen[1 if phase=='exit' else 0]==0,(phase,i,seen)
            report['pixels'].append({'phase':phase,'sample':i,'counts':seen})
        assert max(c[0 if phase=='exit' else 1] for c in counts)>20,(phase,counts)
        if phase=='exit':
            assert travel.active.phase=='hidden'
            assert capture('fully-hidden')==[0,0]
    assert travel.completed==1 and travel.active is None
    assert app.models[owner][0]==model and app.sim.swimmers[owner] is s and app.sim.physics.bodies[owner]==body
    assert app.roster==[fish] and app.transitions.shown[owner]==fish
    assert not s.travelling and not s.arriving and j.reservation is None
    report['checks'].append('24 phase samples: source-only departure, full occlusion, destination-only entry; identity/body unchanged')
    print('PASS native source/hidden/destination pixels and preserved model/swimmer/body',flush=True)

    # Same-frame refresh is absolute, and quality changes retain a journey.
    start();advance(1.)
    pose=app.models[owner][0].getTransform();clock=travel.active.time
    for _ in range(5):app.sync_models();app.update_fish(0)
    assert app.models[owner][0].getTransform()==pose and travel.active.time==clock
    from copy import deepcopy
    settings=deepcopy(app.settings);settings.fish_style='rounded'
    app.appearance.apply_settings(settings)
    assert travel.active and travel.active.time==clock
    assert app.models[owner][0].getTransform()==pose
    assert app.models[owner][0].getTag('fish-style')=='rounded'
    app.set_preset('balanced')
    assert app.models[owner][0].getTransform()==pose
    app.update_fish(0)
    assert travel.active and travel.active.time==clock
    advance(8.)
    assert not travel.active and not s.arriving
    report['checks'].append('dt=0 idempotence, mid-journey restyle and live quality rebuild')

    # Native preferences persist only in the display profile.
    app.controls.page('Transfers');app.controls.transfers.choose('Occasional')
    app.controls.refresh();settle(app)
    assert app.win.saveScreenshot(str(out/'controls.png'))
    assert DisplayProfile.load(app.display_path).transfers=='Occasional'
    app.controls.transfers.choose('Off');assert not travel.start(owner)
    app.controls.transfers.choose('Frequent')
    report['checks'].append('native preference callbacks and display-profile roundtrip')

    # An unrelated geometry revision retains the phase; closing the destination
    # while partially outside causes a smooth retreat or hidden recovery.
    start();advance(3.)
    app.close_view(second);settle(app);advance(8.)
    assert not s.travelling and not s.arriving and len(app.models)==1
    assert app.sim.volume.allows((s.x,s.y,s.z),s.outline)
    second=app.add_window((1320,32,640,720));settle(app)
    start();advance(1.)
    for view in list(app.views):app.close_view(view)
    advance(1.)
    assert travel.active.phase=='parked' and app.models[owner][0].isHidden()
    first=app.add_window((520,32,640,720));second=app.add_window((1320,32,640,720));settle(app)
    advance(7.)
    assert not travel.active and not s.arriving and not s.parked
    report['checks'].append('destination close, all-output close and reopen recovery')
    print('PASS native quality/settings and output-close/reopen recovery',flush=True)

    # Fully opaque mask may be a portal; transparent keep-out may not.
    app.close_view(second);props=WindowProperties();props.setSize(1440,720)
    first.window.requestProperties(props);settle(app)
    app.display.zones=[Deadzone(x=40,y=0,width=20,height=100,blackout=True)]
    app.setup_output();advance(.1)
    assert travel.refresh() and travel.topology.count==2
    start();advance(8.1)
    assert not travel.active and app.transitions.shown[owner]==fish
    report['checks'].append('single output split by opaque deadzone')
    app.display.zones=[];app.setup_output();advance(.1)
    assert travel.topology.count==1 and not travel.start(owner)
    second=app.add_window((1960,32,640,720));settle(app);advance(.1)
    assert travel.topology.count==1 and not travel.start(owner)
    report['checks'].append('joined-window seam does not create transfers')
    print('PASS opaque split and connected-window suppression',flush=True)

    # Bounded idle work: no topology rebuild or route attempts for 256 fish
    # between scheduled attempts (timings are software GL, not a GPU claim).
    from tank.demo import visitors
    app.settings.fish_animations=False;app.roster=visitors(256);app.sync_models()
    app.display.transfers='Off';before=travel.solve_count;attempts=travel.attempts
    advance(1.)
    assert len(app.models)==len(app.sim.swimmers)==256
    assert travel.solve_count==before and travel.attempts==attempts
    report['checks'].append('256-fish idle: zero extra topology solves or route attempts')
    app.display.zones=[Deadzone(x=45,y=0,width=10,height=100)]
    app.setup_output();advance(.2)
    app.settings.fish_animations=True;app.display.transfers='Frequent'
    started=time.perf_counter();accepted=travel.start()
    report['dense_attempt_ms']=(time.perf_counter()-started)*1000
    report['dense_attempt_accepted']=accepted
    travel.finish(restore=True)
    (out/'report.json').write_text(json.dumps(report,indent=2))
    print('PASS 256-fish idle cache; native transfer suite complete',flush=True)


def main():
    import sys
    from panda3d.core import loadPrcFileData
    from tank.aquarium import Aquarium
    from tank.__main__ import main as run
    from tank.settings import Settings
    loadPrcFileData('travel-regression','gl-debug true')
    Aquarium.run=exercise
    with tempfile.TemporaryDirectory(prefix='aquarium-travel-') as directory:
        path=Path(directory)/'settings.json'
        settings=Settings();settings.apply('low');settings.fish_animations=False
        settings.vsync=False;settings.save(path)
        sys.argv=['travel-smoke','--demo','1','--width','960','--height','540','--settings',str(path)]
        run()


if __name__=='__main__':main()
