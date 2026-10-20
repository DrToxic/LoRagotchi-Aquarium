"""Native controller/output, XTest dragging, panorama, shelves and library.

Use python -m tools.run_native tools.operator_smoke --demo 24 --preset low
--settings <isolated-directory>/settings.json. XTest is actual native pointer
input; Xvfb without a WM does not prove Windows or compositor behavior.
"""
import ctypes
import ctypes.util
from pathlib import Path
import time


def exercise(app):
    from panda3d.core import PNMImage, WindowProperties
    from tank.deadzones import Deadzone
    from tools.render_smoke import settle
    deadline=time.monotonic()+20
    while len(app.roster)!=24 and time.monotonic()<deadline:app.taskMgr.step()
    assert len(app.roster)==24
    out=Path(".local");out.mkdir(exist_ok=True)
    assert len(app.views)==1 and len(app.winList)==2
    assert app.winList[0]==app.win and app.winList[1]==app.aquarium_window
    assert app.controls.root.getParent()==app.pixel2d
    assert all(v.root!=app.render2d for v in app.views)
    assert app.panel_visible
    view=app.views[0]
    props=WindowProperties();props.setOrigin(520,100);props.setSize(640,360)
    view.window.requestProperties(props);settle(app)

    api=app.window_drag.pointer.api;display=app.window_drag.pointer.display
    assert display,"X11 pointer backend not available"
    xtest=ctypes.CDLL(ctypes.util.find_library("Xtst"))
    xtest.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
    xtest.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
    api.XFlush.argtypes=[ctypes.c_void_p]
    api.XSetInputFocus.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
    def frames(n=5):
        api.XFlush(display)
        for _ in range(n):app.taskMgr.step()
    def motion(x,y):
        xtest.XTestFakeMotionEvent(display,-1,x,y,0);frames()
    def button(down):
        xtest.XTestFakeButtonEvent(display,1,int(down),0);frames()
    def drag(client,delta):
        start=view.rectangle()
        api.XSetInputFocus(display,view.window.getWindowHandle().getIntHandle(),1,0)
        motion(start[0]+client[0],start[1]+client[1]);button(True)
        assert app.window_drag.active is not None
        motion(start[0]+client[0]+delta[0],start[1]+client[1]+delta[1]);button(False)
        settle(app);assert app.window_drag.active is None
        return start,view.rectangle()

    buffer=view.buffer
    start,end=drag((300,170),(85,45))
    assert end==(start[0]+85,start[1]+45,start[2],start[3]),(start,end)
    start,end=drag((end[2]-2,end[3]-2),(70,50))
    assert end==(start[0],start[1],start[2]+70,start[3]+50),(start,end)
    start,end=drag((2,2),(-40,-30))
    assert end==(start[0]-40,start[1]-30,start[2]+40,start[3]+30),(start,end)
    assert view.buffer==buffer
    # Fullscreen disables dragging, and restores borderless window geometry.
    app.fullscreen(view.window);settle(app)
    app.window_drag.begin(view);assert app.window_drag.active is None
    app.fullscreen(view.window);settle(app);assert view.rectangle()==end
    print("PASS XTest client drag, edge/corner resize, outside-client release, persistent render target, fullscreen restore",flush=True)

    app.taskMgr.remove("aquarium-update")
    app.show_names=False
    for v in app.views:v.names.root.hide()
    app.settings.scale=1.;app.setup_output()
    app.decorations.set_enabled("stone-arch",True)
    app.controls.decorations.rebuild()
    app.controls.page("Decorations")
    settle(app)
    assert app.win.saveScreenshot(str(out/"v0110-decorations-controls.png"))
    assert app.aquarium_window.saveScreenshot(str(out/"v0110-aquarium.png"))
    # Controller's own pixels are unaffected by a fully black aquarium.
    baseline=PNMImage();app.win.getScreenshot(baseline)
    app.display.zones=[Deadzone("Rectangle",0,0,100,100,blackout=True)]
    app.setup_output();settle(app)
    masked=PNMImage();assert app.aquarium_window.getScreenshot(masked)
    assert all(max(masked.getXel(x,y))==0 for y in range(5,masked.getYSize(),11)
               for x in range(5,masked.getXSize(),11))
    control=PNMImage();assert app.win.getScreenshot(control)
    assert all(
        control.getXel(x,y)==baseline.getXel(x,y) for y in range(10,600,13) for x in range(10,440,13))
    app.display.zones=[];app.setup_output()
    print("PASS first-window controls remain pixel-identical and usable while aquarium output is entirely black",flush=True)

    # Freeze world + shelves, compare an offset/corner panorama to one full
    # render. Actual desktop coordinates, not sand-normalized lens rectangles.
    props=WindowProperties();props.setOrigin(520,40);props.setSize(960,720)
    view.window.requestProperties(props);settle(app)
    whole=PNMImage();assert view.window.getScreenshot(whole)
    props=WindowProperties();props.setSize(480,720)
    view.window.requestProperties(props);settle(app)
    second=app.add_window((1000,400,480,360));settle(app)
    assert not app.shelves.boxes
    samples=error=0
    for v,ox,oy in ((view,0,0),(second,480,360)):
        image=PNMImage();assert v.window.getScreenshot(image)
        for y in range(0,image.getYSize(),4):
            for x in range(0,image.getXSize(),4):
                old=whole.getXel(x+ox,y+oy);new=image.getXel(x,y)
                error+=sum(abs(a-b) for a,b in zip(old,new));samples+=3
    error/=samples
    assert error<.012,error
    print(f"PASS unequal, vertically offset panoramic crops reconstruct reference: mean RGB error {error:.7f}",flush=True)
    app.close_view(second)

    # Two aligned, vertically stacked views: world shelves cross no window
    # ownership boundary and leave a wide centre + foreground passage.
    props=WindowProperties();props.setOrigin(520,40);props.setSize(720,400)
    view.window.requestProperties(props);settle(app)
    lower=app.add_window((520,440,720,400));settle(app)
    assert len(app.shelves.boxes)==2
    for v in app.views:
        assert v.window.saveScreenshot(str(out/f"v0110-stacked-{v.view_id}.png"))
    baseline_count=len(app.sim.physics.statics)
    for _ in range(4):app.setup_output()
    assert len(app.sim.physics.statics)==baseline_count
    assert app.shelves.root.getNumChildren()>0
    # A controlled pulse proves both upper and lower outputs still render.
    before=[]
    for v in app.views:
        image=PNMImage();v.window.getScreenshot(image);before.append(image)
    app.render.setColorScale(.5,.8,.4,1);settle(app)
    for v,old in zip(app.views,before):
        image=PNMImage();v.window.getScreenshot(image)
        assert sum(sum(abs(a-b) for a,b in zip(image.getXel(x,y),old.getXel(x,y)))
                   for y in range(10,400,15) for x in range(10,720,15))>1
    app.render.clearColorScale()
    app.close_view(view);settle(app)
    assert app.views==[lower] and not app.shelves.boxes
    app.close_view(lower);settle(app)
    assert not app.views and app.win.getProperties().getOpen() and len(app.models)==24
    counts=(app.graphicsEngine.getNumWindows(),len(app.camList),app.dataRoot.getNumChildren())
    for _ in range(3):
        v=app.add_window((520,40,720,400));settle(app)
        app.close_view(v);settle(app)
        assert (app.graphicsEngine.getNumWindows(),len(app.camList),app.dataRoot.getNumChildren())==counts
    v=app.add_window((520,40,960,540));settle(app)
    app.taskMgr.add(app.update,"aquarium-update")
    frames(8)
    assert len(app.roster)==24 and any(not s.parked for s in app.sim.swimmers.values())
    print("PASS stacked shelves, fresh frames, arbitrary/last output close, three reopen cycles, retained fish and controller",flush=True)


if __name__=="__main__":
    from panda3d.core import loadPrcFileData
    loadPrcFileData("operator-smoke","gl-debug true")
    from tank.aquarium import Aquarium
    Aquarium.run=exercise
    from tank.__main__ import main
    main()
