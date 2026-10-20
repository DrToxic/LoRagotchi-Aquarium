"""Synthetic wire-to-render chat check. No real radio or live database."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def exercise(app):
    import struct
    from panda3d.core import PNMImage
    from tank.chat import CHANNEL, MAX_ACTIVE
    from tank.client import Client
    from tank.simulator import SimulatedRadio
    from tank.store import Store

    deadline = time.monotonic()+15
    while len(app.roster) != 12 and time.monotonic() < deadline:
        app.taskMgr.step()
    assert len(app.roster) == 12
    def packet(index, text, timestamp=42):
        return b"\x11\0\0\0"+bytes([index,255,0])+struct.pack("<I",timestamp)+text.encode()
    wire = [
        packet(2, "Nickel: Hello from the mesh! 🐟"),
        packet(7, "Other: This must not become a bubble"),
        packet(2, "Fish: LFG1|COMMIT|123|456"),
        b"\x07"+bytes(6)+b"\xff\0"+bytes(4)+b"Private: no bubble",
    ]
    store = Store(":memory:")
    client = Client(SimulatedRadio(0, {2:CHANNEL,7:"#other"}, wire), store, app.service.notify)
    try:
        client.connect()
        for _ in wire:client.poll_messages()
    finally:
        client.close();store.close()
    app.taskMgr.step()
    app.taskMgr.remove("aquarium-update")
    assert len(app.chat.active) == 1 and not app.chat.queue.pending
    first = app.chat.active[0]
    # Center the fixture in clear water; production chooses staggered lanes.
    first["x"] = 0
    first["node"].setX(0)
    out = Path(".local");out.mkdir(exist_ok=True)
    def capture(path=None):
        app.graphicsEngine.renderFrame();app.graphicsEngine.renderFrame()
        image = PNMImage();assert app.aquarium_window.getScreenshot(image)
        if path:assert image.write(str(out/path))
        return image
    def difference(a,b):
        return sum(max(abs(a.getXel(x,y)[c]-b.getXel(x,y)[c]) for c in range(3))>.05
                   for y in range(a.getYSize()) for x in range(a.getXSize()))
    submerged = capture()
    app.chat.root.hide()
    absent = capture()
    assert difference(submerged,absent) == 0
    app.chat.root.show()
    # The submerged geometry really exists; actual sand depth hides it.
    app.chat.root.setDepthTest(False)
    through_sand = capture()
    under_pixels = difference(through_sand,submerged)
    assert under_pixels > 50, under_pixels
    app.chat.root.setDepthTest(True)
    builds = app.chat.builds
    app.chat.update(9)
    rising = capture("v018-chat-rising.png")
    app.chat.root.hide();without = capture();app.chat.root.show()
    rising_pixels = difference(rising,without)
    assert rising_pixels > 500, rising_pixels
    assert app.chat.builds == builds
    from tank.deadzones import Deadzone
    app.display.zones=[Deadzone(x=0,y=0,width=100,height=100,blackout=True)]
    app.setup_output()
    masked=capture()
    assert all(max(masked.getXel(x,y))==0 for x in range(0,1280,16) for y in range(0,720,16))
    app.display.zones=[];app.setup_output()
    # Geometry leaves the top before removal, not an abrupt on-screen expiry.
    rising_z=first["node"].getZ()
    first["node"].setZ(first["top"]-first["speed"]*.2)
    app.chat.update(.1)
    top=capture()
    app.chat.root.hide();no_top=capture();app.chat.root.show()
    assert difference(top,no_top)==0 and len(app.chat.active)==1
    first["node"].setZ(rising_z);app.chat.update(0)

    # Shared world object, with a native second window and projector masks.
    app.add_window((1280,0,1280,720))
    identity = first["node"]
    assert app.chat.active[0]["node"] == identity
    app.chat.update(1)
    capture("v018-chat-wall-left.png")
    assert app.views[1].window.saveScreenshot(str(out/"v018-chat-wall-right.png"))
    app.close_second_window()
    capture()
    app.chat.update(80)
    assert not app.chat.active and app.chat.root.getNumChildren() == 0

    # Bounded burst, UI on/off, scene rebuild and no regenerated text per frame.
    for i in range(40):
        app.chat.accept(dict(kind="mesh",route="channel 2",channel_index=2,
                             channel_name=CHANNEL,text_type=0,timestamp=i,
                             text=f"Demo {i}: Café ☣️ · A longer message from the reef."))
    for _ in range(60):
        app.chat.update(.25)
        assert len(app.chat.active) <= MAX_ACTIVE
    ids = [b["node"] for b in app.chat.active]
    app.rebuild_scene()
    assert [b["node"] for b in app.chat.active] == ids
    app.show_controls()
    capture("v018-chat-controls.png")
    app.toggle_chat()
    assert not app.chat.active and not app.chat.queue.pending
    assert not app.settings.chat_bubbles
    app.toggle_chat()
    assert app.settings.chat_bubbles
    print(f"PASS synthetic wire/channel filter, sand occlusion ({under_pixels} hidden pixels), "
          f"rise ({rising_pixels} visible pixels), top exit, projector blackout, native windows, bounded burst, "
          "cached geometry, scene rebuild and toggle",flush=True)


def main():
    if "--inside" in sys.argv:
        sys.argv.remove("--inside")
        from tank.aquarium import Aquarium
        Aquarium.run = exercise
        from tank.__main__ import main as tank_main
        tank_main()
        return
    read,write = os.pipe()
    xvfb = subprocess.Popen(["Xvfb","-displayfd",str(write),"-screen","0","2560x1440x24",
                             "-nolisten","tcp"],pass_fds=[write],
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.close(write)
    with os.fdopen(read) as pipe:display=pipe.readline().strip()
    try:
        with tempfile.TemporaryDirectory(prefix="tank-chat-") as directory:
            result = subprocess.run(
                [sys.executable,"-m","tools.chat_smoke","--inside","--demo","12",
                 "--preset","high","--width","1280","--height","720",
                 "--settings",str(Path(directory)/"settings.json")],
                env={**os.environ,"DISPLAY":":"+display},capture_output=True,text=True)
        print(result.stdout,end="")
        print(result.stderr,end="",file=sys.stderr)
        assert not any(m in result.stderr for m in ("No definition","Unknown TextProperties",
                                                    "Assertion failed","glgsg(error)"))
        raise SystemExit(result.returncode)
    finally:
        xvfb.terminate();xvfb.wait(timeout=5)


if __name__ == "__main__":
    main()
