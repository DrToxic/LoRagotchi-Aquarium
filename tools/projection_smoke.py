"""Verify projector blackouts as rendered pixels, not just mask geometry."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def exercise(app):
    Path('.local').mkdir(exist_ok=True)
    from dataclasses import replace
    from panda3d.core import PNMImage, WindowProperties
    from tank.deadzones import Deadzone, DisplayProfile
    from tools.render_smoke import settle
    deadline=time.monotonic()+15
    while len(app.roster)!=24 and time.monotonic()<deadline:app.taskMgr.step()
    assert len(app.roster)==24
    app.show_names=True
    for _ in range(3):app.taskMgr.step()
    app.taskMgr.remove('aquarium-update')
    props=WindowProperties();props.setOrigin(0,0);props.setSize(960,540)
    app.aquarium_window.requestProperties(props);settle(app)
    panel=app.controls.deadzones
    app.panel.show()
    def capture(view):
        settle(app)
        image=PNMImage();assert view.window.getScreenshot(image)
        return image
    def compare(zones):
        app.display.zones=[];app.setup_output()
        baseline=[capture(v) for v in app.views]
        app.display.zones=zones;app.setup_output()
        rectangles=[v.rectangle() for v in app.views]
        left=min(r[0] for r in rectangles);top=min(r[1] for r in rectangles)
        width=max(x+w for x,y,w,h in rectangles)-left;height=max(y+h for x,y,w,h in rectangles)-top
        checked=black=unchanged=0
        for view,original,(x,y,w,h) in zip(app.views,baseline,rectangles):
            image=capture(view)
            for py in range(3,h-3,7):
                for px in range(3,w-3,7):
                    u=2*(x+px+.5-left)/width-1;v=1-2*(y+py+.5-top)/height
                    box=(u-4/width,u+4/width,v-4/height,v+4/height)
                    # Exclude the sub-pixel tessellated edge: check only pixels
                    # at least two output pixels away from an analytic boundary.
                    active=[z for z in zones if z.enabled and z.blackout]
                    if any(z.intersects(box,width/height) and not z.contains(box,width/height) for z in active):continue
                    blocked=any(z.blocks((u,u,v,v),width/height) for z in active)
                    pixel=image.getXel(px,py);old=original.getXel(px,py)
                    if blocked:
                        assert max(pixel)==0.,(view.view_id,px,py,tuple(pixel),zones)
                        black+=1
                    else:
                        assert max(abs(pixel[i]-old[i]) for i in range(3))<1/255+.0001,(view.view_id,px,py)
                        unchanged+=1
                    checked+=1
        return checked,black,unchanged
    totals=[0,0,0]
    for shape in ('Rectangle','Rounded rectangle','Ellipse'):
        for inverted in (False,True):
            values=compare([Deadzone(shape,18,12,64,76,blackout=True,inverted=inverted)])
            assert values[1]>100 and values[2]>100
            totals=[a+b for a,b in zip(totals,values)]
    assert compare([Deadzone('Ellipse',blackout=True,enabled=False)])[1]==0
    assert compare([Deadzone('Ellipse',inverted=True)])[1]==0
    circle=Deadzone('Ellipse',21.875,0,56.25,100,blackout=True,inverted=True)
    compare([circle,Deadzone('Rounded rectangle',44,40,12,20,blackout=True)])
    full=compare([Deadzone('Rectangle',0,0,100,100,blackout=True)])
    assert full[1]==full[0] and full[2]==0
    print(f'PASS all 3 shapes in both modes: {totals[0]} sampled pixels, {totals[1]} exactly black, {totals[2]} match the unmasked image; disabled/steering-only, combined and full-size masks',flush=True)
    # Recoverability: even with all output black, Tab controls remain usable.
    app.show_controls();app.controls.page('Deadzones')
    panel.selected=0;panel.show_selected();settle(app)
    image=PNMImage();assert app.win.getScreenshot(image)
    assert sum(sum(image.getXel(x,y)) for x in range(20,430,20) for y in range(30,500,20))>10
    assert image.write('.local/v015-blackout-controls.png')
    panel.shape.showPopupMenu()
    assert not panel.shape.popupMenu.isHidden()
    settle(app);assert app.win.saveScreenshot('.local/v015-blackout-popup.png')
    panel.shape.hidePopupMenu()
    panel.blackout_button['command']();assert not app.display.zones[0].blackout
    panel.blackout_button['command']();assert app.display.zones[0].blackout
    panel.invert_button['command']();assert app.display.zones[0].inverted
    saved=DisplayProfile.load(app.display_path);assert saved.zones==app.display.zones
    # A circle in a 16:9 output, with controls open then closed.
    app.display.zones=[circle];app.setup_output();panel.selected=0;panel.show_selected()
    app.taskMgr.add(app.update,'aquarium-update')
    for _ in range(12):app.taskMgr.step()
    app.taskMgr.remove('aquarium-update')
    assert all(not s.parked and app.sim.volume.allows((s.x,s.y,s.z),s.outline) for s in app.sim.swimmers.values())
    assert capture(app.views[0]).write('.local/v015-circle-controls.png')
    app.toggle_panel();assert capture(app.views[0]).write('.local/v015-circle-output.png')
    print('PASS per-zone toggles persist, separate editor survives full blackout, aquarium stays clean',flush=True)
    print('CHECK add two native views',flush=True)
    second=app.add_window((1000,120,640,420));third=app.add_window((0,600,640,360));settle(app)
    for inverted in (False,True):
        values=compare([Deadzone('Ellipse',12,8,76,84,blackout=True,inverted=inverted),
                        Deadzone('Rectangle',43,35,12,12,blackout=True)])
        assert values[1]>100 and values[2]>100
    buffers=[v.buffer for v in app.views]
    for scale in (.35,1.2):
        print('CHECK render scale',scale,flush=True)
        app.settings.scale=scale;app.setup_output()
        compare([Deadzone('Rounded rectangle',10,10,80,80,blackout=True,inverted=True)])
        assert [v.buffer for v in app.views]==buffers
    print('CHECK secondary move/resize',flush=True)
    props=WindowProperties();props.setSize(720,480);props.setOrigin(950,80);second.window.requestProperties(props);settle(app)
    compare([Deadzone('Ellipse',15,10,70,80,blackout=True,inverted=True)])
    for i,v in enumerate(app.views):assert capture(v).write(f'.local/v015-projector-window-{i+1}.png')
    # A full window bounds mask must not be distorted when another view closes.
    print('CHECK middle window close',flush=True)
    app.close_view(second);settle(app)
    app.display.zones=[];app.setup_output()
    before=[capture(v) for v in app.views]
    # A deterministic 3D colour pulse is visible even in a floor-only crop
    # with no fish/plants. It detects a stale FBO rather than relying on activity.
    app.render.setColorScale(.4,1,.6,1)
    for v,old in zip(app.views,before):
        image=capture(v)
        delta=sum(sum(abs(image.getXel(x,y)[k]-old.getXel(x,y)[k]) for k in range(3))
                  for y in range(10,image.getYSize()-10,9) for x in range(10,image.getXSize()-10,9))
        assert delta>1.,(v.view_id,delta)
    app.render.clearColorScale()
    print('PASS surviving outputs render new 3D frames after middle-window close',flush=True)
    compare([Deadzone('Rectangle',25,25,50,50,blackout=True,inverted=True)])
    assert all(v.root.findAllMatches('**/projector-mask-transform').getNumPaths()==1 for v in app.views)
    for i in range(6):
        app.display.zones=[];app.setup_output()
        assert all(v.blackout is None for v in app.views)
        app.display.zones=[circle];app.setup_output()
        assert all(v.root.findAllMatches('**/projector-mask-transform').getNumPaths()==1 for v in app.views)
    print('CHECK last extra window close',flush=True)
    app.close_view(third);settle(app)
    app.settings.scale=.35
    props=WindowProperties();props.setOrigin(0,0);props.setSize(3840,2160);app.aquarium_window.requestProperties(props);settle(app)
    values=compare([circle])
    assert values[1]>10000 and values[2]>10000
    print('PASS 4K circular blackout at output resolution with 0.35 scene scale',flush=True)
    print('PASS masks align across 3 offset windows, independent render scales, move/resize, arbitrary close and repeated clear/rebuild without mask leaks',flush=True)


def main():
    if '--inside' in sys.argv:
        sys.argv.remove('--inside')
        from panda3d.core import loadPrcFileData
        loadPrcFileData('projection-smoke','gl-debug true')
        from tank.aquarium import Aquarium
        Aquarium.run=exercise
        from tank.__main__ import main as tank_main
        tank_main();return
    read,write=os.pipe()
    xvfb=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','3840x2160x24','-nolisten','tcp'],pass_fds=[write],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.close(write)
    with os.fdopen(read) as pipe:display=pipe.readline().strip()
    try:
        with tempfile.TemporaryDirectory(prefix='tank-projector-') as directory:
            result=subprocess.run([sys.executable,'-m','tools.projection_smoke','--inside','--demo','24','--preset','low','--settings',str(Path(directory)/'settings.json')],env={**os.environ,'DISPLAY':':'+display},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            print(result.stdout,end='',flush=True)
            assert not any(marker in result.stdout for marker in ('GL_INVALID_','GL error ','FBO incomplete','BadMatch')), 'Graphics errors in projection smoke'
    finally:xvfb.terminate();xvfb.wait(timeout=5)
    raise SystemExit(result.returncode)

if __name__=='__main__':main()
