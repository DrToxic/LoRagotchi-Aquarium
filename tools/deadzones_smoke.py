"""Real native multi-view/deadzone lifecycle; Xvfb is not Windows hardware proof."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def exercise(app):
    # Measure steady-state swimming/target freshness, not the initial interval
    # while arrivals can legitimately be above a lower output's crop.
    # Animated panorama/mask/lifecycle behavior lives in transitions_smoke.
    app.settings.fish_animations=False;app.sync_models()
    from panda3d.core import WindowProperties, GraphicsWindow, Point3
    from tank.deadzones import DisplayProfile
    from tools.render_smoke import settle, capture
    deadline=time.monotonic()+15
    while len(app.roster)!=48 and time.monotonic()<deadline:app.taskMgr.step()
    assert len(app.roster)==48
    controls=app.controls;panel=controls.deadzones
    app.show_controls();controls.page('Deadzones')
    Path('.local').mkdir(exist_ok=True)
    assert list(controls.tabs)==['Aquarium','Radio','Deadzones','Decorations','Animations']
    for width,height in ((1280,720),(2560,1440),(3840,2160),(800,450)):
        props=WindowProperties();props.setSize(width,height);app.win.requestProperties(props);settle(app)
        controls.resize();app.graphicsEngine.renderFrame()
        assert app.panel.getSx()*controls.HEIGHT<=height-24+.01
        assert app.win.saveScreenshot(f'.local/v014-deadzones-{width}.png')
    props=WindowProperties();props.setOrigin(800,0);props.setSize(960,540);app.aquarium_window.requestProperties(props);settle(app)
    # Disjoint, vertically offset three-window arrangement with a missing corner.
    second=app.add_window((0,300,760,540));third=app.add_window((800,580,760,440));settle(app)
    assert len(app.views)==3 and len(app.winList)==4
    assert all(isinstance(v.window,GraphicsWindow) for v in app.views)
    ids=set(app.sim.swimmers)
    for _ in range(6):app.taskMgr.step()
    assert all(not s.parked and app.sim.volume.allows((s.x,s.y,s.z),s.outline) for s in app.sim.swimmers.values())
    # Edit the real controls, including invalid numbers, disabled shapes and saved data.
    panel.fields[0].enterText('nan');panel.apply()
    assert not app.display.zones and 'finite' in panel.note['text']
    for shape,values in [('Rectangle',(5,42,12,18)),('Rounded rectangle',(60,15,17,28)),('Ellipse',(65,67,20,20))]:
        panel.new();panel.shape.set(shape)
        for field,value in zip(panel.fields,values):field.enterText(str(value))
        panel.apply()
    assert len(app.display.zones)==3
    panel.toggle_enabled();assert not app.display.zones[2].enabled
    panel.toggle_enabled();panel.toggle_outlines()
    assert len(panel.overlay_nodes)==9
    panel.selected=1;panel.show_selected()
    panel.fields[0]['focus']=1
    for key in ('v','f','n','1','delete'):app.messenger.send(key)
    assert len(app.views)==3 and not app.window_modes.saved
    controls.blur()
    # A preview click edits the draft; no unexpected zone save before Apply.
    mouse=app.mouseWatcherNode
    class Click:
        def hasMouse(self):return True
        def getMouse(self):
            point=app.render2d.getRelativePoint(panel.preview,Point3(200,0,-60))
            from panda3d.core import Point2
            return Point2(point.x,point.z)
    original=app.mouseWatcherNode;app.mouseWatcherNode=Click()
    old=app.display.zones[1]
    try:panel.place(None)
    finally:app.mouseWatcherNode=original
    assert app.display.zones[1]==old
    panel.show_selected()
    panel.save_layout();saved=DisplayProfile.load(app.display_path)
    assert saved.windows==[v.rectangle() for v in app.views] and saved.zones==app.display.zones
    for _ in range(12):app.taskMgr.step()
    assert set(app.sim.swimmers)==ids
    assert all(not s.parked and app.sim.volume.allows((s.x,s.y,s.z),s.outline) for s in app.sim.swimmers.values())
    buffers=[v.buffer for v in app.views]
    for v in app.views:app.on_window(v.window)
    assert buffers==[v.buffer for v in app.views]
    before=[capture(app,v.window) for v in app.views]
    for _ in range(10):app.taskMgr.step()
    for i,v in enumerate(app.views):
        image=capture(app,v.window)
        assert image.write(f'.local/v014-layout-window-{i+1}.png')
        # Sample left of controls; scene must animate in every native window.
        delta=sum(sum(abs(image.getXel(x,y)[k]-before[i].getXel(x,y)[k]) for k in range(3))
                  for x in range(10,min(400,image.getXSize()),7) for y in range(20,image.getYSize()-20,7))
        assert delta>1.,(i,delta)
    print('PASS 3 offset native windows, visible outlines, scene animation in each, 3 shape controls, draft/validation/focus and saved geometry',flush=True)
    # Close a non-last window via its native event, not by popping the last view.
    closing=second.window;props=WindowProperties();props.setOpen(False);closing.requestProperties(props);settle(app)
    app.on_window(closing);settle(app)
    assert second not in app.views and third in app.views and len(app.views)==2
    assert app.second_window==third.window
    app.close_view(third);settle(app)
    baseline=(app.graphicsEngine.getNumWindows(),len(app.camList),app.dataRoot.getNumChildren())
    for _ in range(3):
        a=app.add_window((0,300,640,360));b=app.add_window((660,400,640,360));settle(app)
        app.close_view(a);app.close_view(b);settle(app)
        assert (app.graphicsEngine.getNumWindows(),len(app.camList),app.dataRoot.getNumChildren())==baseline
    # Native input per window closes only its originating view.
    a=app.add_window((0,0,320,180));b=app.add_window((320,0,320,180));settle(app)
    app.messenger.send(f'view-{a.view_id}-escape');settle(app)
    assert a not in app.views and b in app.views
    app.close_view(b);settle(app)
    assert (app.graphicsEngine.getNumWindows(),len(app.camList),app.dataRoot.getNumChildren())==baseline
    # Reach the advertised cap with small outputs, then clean them all up.
    for i in range(7):app.add_window((i*80,i*40,320,180))
    settle(app);assert len(app.views)==8 and app.add_window() is None
    for v in list(app.views)[1:]:app.close_view(v)
    settle(app)
    assert len(app.views)==1 and set(app.sim.swimmers)==ids
    print('PASS non-last native close, originating-window keyboard routing, 3 reopen cycles without output/camera/input leaks, 8-window cap',flush=True)


def main():
    if '--inside' in sys.argv:
        sys.argv.remove('--inside')
        from tank.aquarium import Aquarium
        if '--restore-check' in sys.argv:
            sys.argv.remove('--restore-check')
            def restored(app):
                from tools.render_smoke import settle
                from tank.deadzones import DisplayProfile
                settle(app)
                saved=DisplayProfile.load(app.display_path)
                if app.restore_rectangles:
                    assert len(app.views)==3
                    assert [v.rectangle() for v in app.views]==saved.windows
                else:assert len(app.views)==1
                assert app.display.zones==saved.zones and len(saved.zones)==3
                print('PASS fresh-process saved window/zone restoration or explicit single-window override',flush=True)
            Aquarium.run=restored
        else:Aquarium.run=exercise
        from tank.__main__ import main as tank_main
        tank_main();return
    read,write=os.pipe()
    xvfb=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','3840x2160x24','-nolisten','tcp'],pass_fds=[write],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.close(write)
    with os.fdopen(read) as pipe:display=pipe.readline().strip()
    try:
        with tempfile.TemporaryDirectory(prefix='tank-deadzones-') as directory:
            result=subprocess.run([sys.executable,'-m','tools.deadzones_smoke','--inside','--demo','48','--preset','low','--settings',str(Path(directory)/'settings.json')],env={**os.environ,'DISPLAY':':'+display})
            if result.returncode==0:
                for override in ([],['--wall-columns','1']):
                    result=subprocess.run([sys.executable,'-m','tools.deadzones_smoke','--inside','--restore-check','--demo','0','--preset','low','--settings',str(Path(directory)/'settings.json'),*override],env={**os.environ,'DISPLAY':':'+display})
                    if result.returncode:break
    finally:xvfb.terminate();xvfb.wait(timeout=5)
    raise SystemExit(result.returncode)

if __name__=='__main__':main()
