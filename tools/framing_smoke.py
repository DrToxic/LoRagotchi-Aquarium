"""Native panoramic seabed pixels and bubble exits; no radio or live database."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def exercise(app):
    from panda3d.core import PNMImage, WindowProperties
    from tank.art import floor_mesh
    from tank.framing import bounds
    from tank.chat import CHANNEL
    from tools.render_smoke import settle

    deadline = time.monotonic()+15
    while len(app.roster) != 12 and time.monotonic() < deadline:
        app.taskMgr.step()
    assert len(app.roster) == 12
    app.taskMgr.remove("aquarium-update")
    app.footer.hide()
    out = Path(".local");out.mkdir(exist_ok=True)

    def capture(view, name=None):
        settle(app)
        image = PNMImage();assert view.window.getScreenshot(image)
        if name:assert image.write(str(out/name))
        return image

    # Use the actual floor geometry and rear-water plane, with diagnostic
    # colours so lighting, rocks, fish and the sand texture cannot fool the
    # shoreline measurement. The normal scene is restored for the preview.
    fixture = app.scene.attachNewNode("sand-measurement")
    sand = floor_mesh();sand.reparentTo(fixture)
    sand.setColor(1,0,0,1);sand.setLightOff();sand.setFogOff()
    background = app.decor.find("**/deep-water").copyTo(fixture)
    background.setColor(0,0,0,1)
    fixture.hide()

    def measure(label):
        app.decor.hide();app.decorations.root.hide();app.shelves.root.hide()
        for model,_,_ in app.models.values():model.hide()
        fixture.show()
        readings = []
        left,top,full_width,full_height=bounds([v.rectangle() for v in app.views])
        for view in app.views:
            image = capture(view)
            w,h = image.getXSize(),image.getYSize()
            edges = []
            for x in range(w//3,2*w//3,max(1,w//36)):
                edge = next((y for y in range(h) if image.getXel(x,y)[0] > .7),h)
                edges.append(edge/h)
            expected=max(0,min(1,(top+full_height*2/3-view.rectangle()[1])/h))
            assert all(abs(edge-expected) < .025 for edge in edges),(label,view.view_id,edges,expected)
            readings.append(f"{w}x{h}: {min(edges):.4f}..{max(edges):.4f}")
        fixture.hide();app.decor.show();app.decorations.root.show();app.shelves.root.show()
        for model,_,_ in app.models.values():model.show()
        print(f"PASS sand pixels {label}: "+", ".join(readings),flush=True)

    measure("single")
    props=WindowProperties();props.setSize(720,1280)
    app.aquarium_window.requestProperties(props);settle(app);measure("single portrait")
    capture(app.views[0],"v019-framing-portrait.png")
    props=WindowProperties();props.setSize(1280,720)
    app.aquarium_window.requestProperties(props);settle(app)
    second = app.add_window((1280,260,960,540))
    third = app.add_window((2260,0,720,1280))
    settle(app)
    buffers = [v.buffer for v in app.views]
    measure("three unequal/offset views")
    props=WindowProperties();props.setOrigin(1280,120);props.setSize(600,1000)
    second.window.requestProperties(props);settle(app)
    assert [v.buffer for v in app.views] == buffers
    measure("resize/move")
    app.settings.scale=.5;app.setup_output();measure("half-scale scene")
    app.settings.scale=1;app.setup_output()
    app.fullscreen(second.window);settle(app);measure("secondary fullscreen")
    app.fullscreen(second.window);settle(app);measure("fullscreen restore")
    app.close_view(third);app.close_view(second);settle(app)
    measure("close survivors")
    fixture.removeNode()

    # Air bubble really renders above the old z=12 wrap point, then reaches
    # the top few pixels and is already invisible before recycling.
    for bubble in app.bubbles.items:bubble["node"].hide()
    bubble = app.bubbles.items[0]
    bubble["node"].show()
    bubble["x"]=0.;bubble["y"]=-3.
    app.bubbles.set_view(app.water_lens)
    bubble["z"]=12.
    app.bubbles.update(0)

    def difference(a,b):
        return [(x,y) for y in range(a.getYSize()) for x in range(a.getXSize())
                if max(abs(a.getXel(x,y)[c]-b.getXel(x,y)[c]) for c in range(3)) > .025]

    def air_pixels():
        shown=capture(app.views[0])
        bubble["node"].hide();hidden=capture(app.views[0]);bubble["node"].show()
        return difference(shown,hidden)

    pixels = air_pixels()
    assert len(pixels) > 0,"air bubble missing at old cutoff"
    app.bubbles.update(.1)
    assert bubble["z"] > 12
    from tank.framing import at_depth
    bubble["z"]=at_depth(app.water_lens,app.camera,app.render,0,.98,bubble["y"]).z
    app.bubbles.update(0)
    pixels = air_pixels()
    assert pixels and max(y for x,y in pixels) < 20,pixels
    bubble["z"]=bubble["top"]-.001
    app.bubbles.update(0)
    assert not air_pixels(),"air bubble must be invisible before recycling"
    app.bubbles.update(1)
    assert bubble["node"].getZ() == -.25
    assert not air_pixels(),"recycled bubble must start beneath sand"
    for b in app.bubbles.items:b["node"].show()
    print("PASS air bubble visible above old cutoff and within top 20 pixels; invisible at recycle/birth",flush=True)

    # Expand the view during a chat bubble's final moments. Keep the node and
    # its current position, and let it continue through the new upper water.
    second=app.add_window((1280,0,1280,720));settle(app)
    app.chat.accept(dict(kind="mesh",route="channel 2",channel_index=2,
                         channel_name=CHANNEL,text_type=0,timestamp=101,
                         text="Nickel: More water, room to float 🐟"))
    app.chat.update(0)
    chat=app.chat.active[0];chat["x"]=0
    app.chat.update(chat["duration"]-.2)
    pos=tuple(chat["node"].getPos())
    old_top=chat["top"]
    app.close_view(second);settle(app)
    assert tuple(chat["node"].getPos()) == pos and chat["top"] > old_top
    app.chat.update(.3)
    assert chat in app.chat.active
    shown=capture(app.views[0])
    app.chat.root.hide();hidden=capture(app.views[0]);app.chat.root.show()
    assert len(difference(shown,hidden)) > 100,"resized chat should still be visible"
    builds=app.chat.builds
    # Prove the card crosses the actual top border, not merely some world Z.
    exit_center=at_depth(app.water_lens,app.camera,app.render,0,1,app.chat.DEPTH).z
    chat["node"].setZ(exit_center)
    app.chat.update(0)
    shown=capture(app.views[0],"v019-chat-top.png")
    app.chat.root.hide();hidden=capture(app.views[0]);app.chat.root.show()
    pixels=difference(shown,hidden)
    assert len(pixels)>100 and min(y for x,y in pixels)<=1
    chat["node"].setZ(chat["top"]-.001);app.chat.update(0)
    shown=capture(app.views[0])
    app.chat.root.hide();hidden=capture(app.views[0]);app.chat.root.show()
    assert not difference(shown,hidden) and chat in app.chat.active
    app.chat.update(1)
    assert not app.chat.active and app.chat.builds == builds
    print("PASS resized chat survives old deadline, crosses top border, then removes off-screen; no text rebuild",flush=True)

    app.chat.accept(dict(kind="mesh",route="channel 2",channel_index=2,
                         channel_name=CHANNEL,text_type=0,timestamp=102,
                         text="Nickel: More water, room to float 🐟"))
    app.chat.update(0)
    chat=app.chat.active[0];chat["x"]=0
    app.chat.update(10)
    app.footer.show()
    capture(app.views[0],"v019-framing.png")


def main():
    if "--inside" in sys.argv:
        sys.argv.remove("--inside")
        from panda3d.core import loadPrcFileData
        loadPrcFileData("framing-test","gl-debug true")
        from tank.aquarium import Aquarium
        Aquarium.run=exercise
        from tank.__main__ import main as tank_main
        tank_main()
        return
    read,write=os.pipe()
    xvfb=subprocess.Popen(["Xvfb","-displayfd",str(write),"-screen","0","3200x1800x24",
                           "-nolisten","tcp"],pass_fds=[write],
                          stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.close(write)
    with os.fdopen(read) as pipe:display=pipe.readline().strip()
    try:
        with tempfile.TemporaryDirectory(prefix="tank-framing-") as directory:
            result=subprocess.run(
                [sys.executable,"-m","tools.framing_smoke","--inside","--demo","12",
                 "--preset","high","--width","1280","--height","720",
                 "--settings",str(Path(directory)/"settings.json")],
                env={**os.environ,"DISPLAY":":"+display},capture_output=True,text=True)
        print(result.stdout,end="")
        print(result.stderr,end="",file=sys.stderr)
        assert not any(s in result.stderr for s in ("No definition","Unknown TextProperties",
                                                    "Assertion failed","glgsg(error)","GL error"))
        raise SystemExit(result.returncode)
    finally:
        xvfb.terminate();xvfb.wait(timeout=5)


if __name__ == "__main__":
    main()
