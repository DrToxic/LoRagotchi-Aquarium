"""Exercise native windows and renderer at 256 fish (Xvfb, not hardware FPS)."""
import time
import sys
from dataclasses import replace
from pathlib import Path
from panda3d.core import WindowProperties, PNMImage, GraphicsWindow
from tank.aquarium import Aquarium


def settle(app, frames=4):
    for _ in range(frames):
        app.graphicsEngine.renderFrame()
        app.eventMgr.doEvents()
    app.setup_output()


def capture(app, window):
    settle(app)
    image=PNMImage()
    assert window.getScreenshot(image)
    # A black framebuffer is not a passing native-window test.
    pixels=[image.getXel(x,y) for y in range(0,image.getYSize(),13) for x in range(0,image.getXSize(),13)]
    assert max(sum(pixel) for pixel in pixels)-min(sum(pixel) for pixel in pixels)>.15
    return image


def exercise(self):
    # This suite measures steady-state labels/window lifecycle. Animated
    # removal/update behavior is exercised separately by transitions_smoke.
    self.settings.fish_animations=False;self.sync_models()
    expected=self.args.demo
    deadline=time.monotonic()+20
    while len(self.roster)!=expected and time.monotonic()<deadline:self.taskMgr.step()
    assert len(self.roster)==expected
    assert self.panel_visible
    before={key:state for key,state in self.sim.swimmers.items()}
    self.set_preset('low');assert len(self.models)==expected
    assert all(self.sim.swimmers[key] is state for key,state in before.items())
    self.scale_slider['value']=.5;self.apply_scale()
    self.toggle_names();assert self.show_names
    for _ in range(4):self.taskMgr.step()
    primary=self.views[0]
    assert primary.names.root.getNumChildren()==expected
    builds=primary.names.builds
    for _ in range(10):self.taskMgr.step()
    assert primary.names.builds==builds
    renamed=replace(self.roster[0],name='Refreshed owner')
    self.roster[0]=renamed;self.sync_models()
    assert primary.names.labels[renamed.owner][1]=='Refreshed owner'
    assert primary.names.builds==builds+1
    print(f'PASS {expected} fish: cached names, rename refresh, graphics retain swimming state',flush=True)

    original_size=(self.aquarium_window.getXSize(),self.aquarium_window.getYSize())
    self.fullscreen();settle(self)
    assert not self.aquarium_window.getProperties().getFullscreen()
    # Xvfb has no WM to apply decoration hints. Windows style changes need the
    # physical Windows check; here verify actual dimensions and no mode switch.
    if sys.platform=='win32':assert self.aquarium_window.getProperties().getUndecorated()
    assert (self.aquarium_window.getXSize(),self.aquarium_window.getYSize())==(self.pipe.getDisplayWidth(),self.pipe.getDisplayHeight())
    self.fullscreen();settle(self)
    assert (self.aquarium_window.getXSize(),self.aquarium_window.getYSize())==original_size
    assert self.aquarium_window.getRequestedProperties().getUndecorated() or self.aquarium_window.getProperties().getUndecorated()
    print('PASS borderless fullscreen and exact window-size restore without hardware mode switch',flush=True)

    self.taskMgr.remove('aquarium-update')  # frozen reference world for pixel comparison
    self.panel.hide()
    primary.names.root.hide()
    props=WindowProperties();props.setOrigin(0,0);props.setSize(1280,360);self.aquarium_window.requestProperties(props)
    whole=capture(self,self.aquarium_window)
    assert (whole.getXSize(),whole.getYSize())==(1280,360)
    props=WindowProperties();props.setSize(640,360);self.aquarium_window.requestProperties(props)
    settle(self)
    self.args.second_width=640;self.args.second_height=360;self.args.second_origin=[640,0]
    self.toggle_wall()
    assert isinstance(self.second_window,GraphicsWindow) and self.second_window!=self.aquarium_window
    assert len(self.views)==2 and len(self.winList)==3
    for view in self.views:view.names.root.hide()
    left=capture(self,self.aquarium_window);right=capture(self,self.second_window)
    error=0.;n=0
    for y in range(0,360,4):
        for x in range(0,1280,4):
            a=whole.getXel(x,y);b=(left if x<640 else right).getXel(x%640,y)
            error+=sum(abs(a[i]-b[i]) for i in range(3));n+=3
    error/=n
    assert error<.012,f'Two OS windows do not reconstruct full frustum: {error}'
    print(f'PASS separate OS windows reconstruct shared world: mean RGB error {error:.7f}',flush=True)

    # Moving/focusing must retain render targets; resizing must update only the
    # affected target. Mixed-size/offset camera geometry is also unit-tested.
    buffers=[v.buffer for v in self.views]
    props=WindowProperties();props.setOrigin(640,120);self.second_window.requestProperties(props)
    settle(self)
    assert [v.buffer for v in self.views]==buffers
    for _ in range(3):self.on_window(self.aquarium_window);self.on_window(self.second_window)
    assert [v.buffer for v in self.views]==buffers
    props=WindowProperties();props.setSize(800,450);self.second_window.requestProperties(props)
    settle(self)
    assert primary.buffer==buffers[0] and self.views[1].internal_size==(400,225)
    secondary_rect=self.views[1].rectangle()
    self.fullscreen(self.second_window);settle(self)
    if sys.platform=='win32':assert self.second_window.getProperties().getUndecorated()
    self.fullscreen(self.second_window);settle(self)
    assert self.views[1].rectangle()==secondary_rect
    for i,view in enumerate(self.views):
        view.names.update(True,view.lens,self.camera,self.render,self.models,view.aspect)
        view.names.root.show()
        image=capture(self,view.window)
        Path('.local').mkdir(exist_ok=True)
        assert image.write(f'.local/revised-window-{i+1}.png')
    print('PASS independent resize, vertical offset, move/focus target reuse; both windows render names',flush=True)

    # Close via native window property/event, then repeat toggles to detect leaks.
    closing=self.second_window
    props=WindowProperties();props.setOpen(False);closing.requestProperties(props)
    settle(self)
    # Panda only emits window-event for external OS changes. Deliver that same
    # handler after this programmatic close (Xvfb has no window manager).
    self.on_window(closing)
    settle(self)
    assert self.second_window is None and len(self.views)==1
    baseline=(self.graphicsEngine.getNumWindows(),len(self.camList),self.dataRoot.getNumChildren())
    for _ in range(3):
        self.toggle_wall();settle(self)
        self.toggle_wall();settle(self)
        assert (self.graphicsEngine.getNumWindows(),len(self.camList),self.dataRoot.getNumChildren())==baseline
    assert len(self.models)==expected
    print('PASS close-event handling and three reopen cycles, no output/camera/input-node leaks',flush=True)
    self.taskMgr.add(self.update,'aquarium-update')
    self.select_next();owner=self.roster[self.selected].owner;self.remove_selected()
    deadline=time.monotonic()+3
    while len(self.roster)==expected and time.monotonic()<deadline:self.taskMgr.step()
    assert len(self.roster)==expected-1 and owner not in self.models
    assert owner not in primary.names.labels
    self.end_session();self.end_session()
    deadline=time.monotonic()+3
    while self.roster and time.monotonic()<deadline:self.taskMgr.step()
    assert not self.roster and not primary.names.labels
    print('PASS remove/end-session clean models, simulation and cached labels',flush=True)


Aquarium.run=exercise
from tank.__main__ import main
if __name__=='__main__':main()
