"""Exercise real native renderer/operator callbacks under Xvfb, not mock widgets."""
import sys,time
from pathlib import Path
from panda3d.core import WindowProperties,PNMImage
from tank.aquarium import Aquarium

def exercise(self):
    deadline=time.monotonic()+5
    while not self.roster and time.monotonic()<deadline:self.taskMgr.step()
    assert len(self.roster)==12
    self.toggle_panel();assert self.panel_visible
    self.set_preset('low');assert len(self.models)==12
    self.scale_slider['value']=.5;self.apply_scale();assert self.internal_size==(640,360)
    self.toggle_wall();assert len(self.view_cameras)==2 and len(self.models)==12
    self.toggle_names();assert self.show_names
    # Freeze the world: compare one frustum with two cropped frusta, same camera
    # and same exact simulation state. Two views must reconstruct the same image.
    self.panel.hide();self.args.wall_columns=1;self.setup_output()
    self.graphicsEngine.renderFrame();self.graphicsEngine.renderFrame();one=PNMImage();self.win.getScreenshot(one)
    self.args.wall_columns=2;self.setup_output()
    self.graphicsEngine.renderFrame();self.graphicsEngine.renderFrame();two=PNMImage();self.win.getScreenshot(two)
    error=0.;n=0
    for y in range(0,one.getYSize(),4):
        for x in range(0,one.getXSize(),4):
            a,b=one.getXel(x,y),two.getXel(x,y);error+=sum(abs(a[i]-b[i]) for i in range(3));n+=3
    error/=n
    assert error<.01,f'Tile frusta do not reconstruct whole world: mean RGB error {error}'
    print(f'PASS shared-world 1-versus-2-tile reconstruction: mean RGB error {error:.7f}',flush=True)
    props=WindowProperties();props.setSize(960,540);self.win.requestProperties(props)
    for _ in range(5):self.taskMgr.step()
    assert (self.win.getXSize(),self.win.getYSize())==(960,540) and self.internal_size==(480,270)
    self.select_next();owner=self.roster[self.selected].owner;self.remove_selected()
    deadline=time.monotonic()+3
    while len(self.roster)==12 and time.monotonic()<deadline:self.taskMgr.step()
    assert len(self.roster)==11 and owner not in self.models
    self.end_session();self.end_session()
    deadline=time.monotonic()+3
    while self.roster and time.monotonic()<deadline:self.taskMgr.step()
    assert not self.roster
    print('PASS native callbacks: panel, quality, resolution scale, resize, selection, remove, end session; no identity culling by quality',flush=True)

Aquarium.run=exercise
from tank.__main__ import main
if __name__=='__main__':main()
