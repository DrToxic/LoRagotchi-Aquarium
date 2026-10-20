import math
import random

import pytest
from panda3d.core import NodePath, Point2, Point3

from tank.bubbles import AirBubbles
from tank.chat import CHANNEL, ChatBubbles
from tank.deadzones import Deadzone
from tank.framing import SAND_BACK, aim_at_sand, bounds, regions
from tank.swim_volume import SwimVolume
from tank.views import desktop_lenses


def frame(rectangles):
    render = NodePath("render")
    camera = render.attachNewNode("camera")
    camera.setPos(0,-32,12)
    full = desktop_lenses([bounds(rectangles)])[0]
    aim_at_sand(camera,render,full)
    return render,camera,full,desktop_lenses(rectangles)


@pytest.mark.parametrize("rectangles", [
    [(0,0,1280,720)],
    [(0,0,720,1280)],
    [(0,0,320,1800)],
    [(0,0,1280,720),(1280,300,960,540)],
    [(-1920,-200,1920,1080),(0,400,2560,1440),(2560,-600,800,600)],
    [(0,0,1280,720),(0,1080,1280,720)],
])
def test_sand_anchors_combined_panorama_and_views_use_physical_offsets(rectangles):
    render,camera,full,lenses = frame(rectangles)
    point = Point2()
    full.project(camera.getRelativePoint(render,Point3(*SAND_BACK)),point)
    assert point.y == pytest.approx(-1/3,abs=2e-6)
    for lens,(a,b,c,d) in zip(lenses,regions(rectangles)):
        point = Point2()
        lens.project(camera.getRelativePoint(render,Point3(*SAND_BACK)),point)
        assert c+(point.y+1)*(d-c)/2 == pytest.approx(-1/3,abs=2e-6)
    assert full.getHfov() <= 60.001 and full.getVfov() <= 60.001


@pytest.mark.parametrize("shape", ["Rectangle","Rounded rectangle","Ellipse"])
@pytest.mark.parametrize("inverted", [False,True])
def test_panoramic_water_constraints_match_physical_screen_masks(shape,inverted):
    rects = [(0,0,1280,720),(1280,300,960,540)]
    render,camera,full,lenses = frame(rects)
    water = regions(rects)
    screen = regions(rects)
    rotation = camera.getQuat(render)
    zone = Deadzone(shape,16,10,73,78,inverted=inverted)
    volume = SwimVolume()
    _,_,width,height = bounds(rects)
    volume.configure(camera.getPos(render),rotation.getRight(),rotation.getForward(),rotation.getUp(),
                     math.tan(math.radians(full.getHfov()/2)),math.tan(math.radians(full.getVfov()/2)),
                     water,[zone],True,tuple(zip(water,screen)),width/height)
    rng = random.Random(17)
    tested = blocked = 0
    for _ in range(300):
        p = volume.point(rng.uniform(-.99,.99),rng.uniform(-.99,.99),32)
        visible = False
        excluded = False
        for lens,(a,b,c,d) in zip(lenses,screen):
            uv = Point2()
            lens.project(camera.getRelativePoint(render,Point3(*p)),uv)
            if abs(uv.x) <= 1 and abs(uv.y) <= 1:
                visible = True
                x,y = a+(uv.x+1)*(b-a)/2,c+(uv.y+1)*(d-c)/2
                excluded |= zone.blocks((x,x,y,y),width/height)
        assert volume.allows(p,0) == (visible and not excluded)
        tested += visible
        blocked += visible and excluded
    assert tested > 100 and 0 < blocked < tested


def test_air_bubbles_pass_old_cutoff_and_resize_without_teleporting():
    render,camera,full,_ = frame([(0,0,1280,720)])
    bubbles = AirBubbles(render,3,camera,render)
    bubbles.set_view(full)
    b = bubbles.items[0]
    b["z"] = 12
    bubbles.update(.1)
    assert 12 < b["z"] < b["top"]
    old = tuple(b["node"].getPos())
    taller = desktop_lenses([(0,0,720,1280)])[0]
    aim_at_sand(camera,render,taller)
    bubbles.set_view(taller)
    assert tuple(b["node"].getPos()) == old
    b["z"] = b["top"]-.001
    bubbles.update(0)
    p = Point2()
    taller.project(camera.getRelativePoint(render,b["node"].getPos()),p)
    assert p.y > 1
    bubbles.update(1)
    assert b["node"].getZ() == pytest.approx(-.25)


def test_chat_resize_updates_exit_without_rebuilding_or_old_timer_expiry():
    render,camera,full,_ = frame([(0,0,2560,720)])
    chat = ChatBubbles(render,camera,render)
    chat.set_view(full)
    chat.accept(dict(kind="mesh",route="channel 2",channel_index=2,channel_name=CHANNEL,
                     text_type=0,timestamp=1,text="Nickel: Keep floating 🐟"))
    chat.update(0)
    bubble = chat.active[0]
    chat.update(bubble["duration"]-.2)
    previous = tuple(bubble["node"].getPos())
    old_exit = bubble["top"]
    taller = desktop_lenses([(0,0,1280,720)])[0]
    aim_at_sand(camera,render,taller)
    chat.set_view(taller)
    assert tuple(bubble["node"].getPos()) == previous
    assert bubble["top"] > old_exit
    chat.update(.3)
    assert bubble in chat.active and chat.builds == 1
    bubble["node"].setZ(bubble["top"]-.01)
    chat.update(0)
    assert bubble in chat.active
    chat.update(1)
    assert not chat.active and chat.root.getNumChildren() == 0
    chat.destroy()


def test_inverted_mask_does_not_allow_offscreen_escape_with_edges_disabled():
    volume = SwimVolume()
    area = (-1,1,-1,1)
    volume.configure(volume.origin,volume.right,volume.forward,volume.up,volume.tan_x,volume.tan_y,
                     [area],[Deadzone("Ellipse",10,10,80,80,inverted=True)],False,[(area,area)],16/9)
    assert volume.allows_box((-.1,.1,-.1,.1))
    assert not volume.allows_box((2,3,2,3))
