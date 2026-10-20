"""Native Unicode labels, controls, and RX discovery. Synthetic data only."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def exercise(app):
    app.settings.fish_animations=False;app.sync_models()
    from dataclasses import replace
    from panda3d.core import PNMImage, TextNode
    from direct.gui.OnscreenText import OnscreenText
    from tank.text import display_text

    deadline = time.monotonic() + 15
    while len(app.roster) != 12 and time.monotonic() < deadline:
        app.taskMgr.step()
    assert len(app.roster) == 12
    samples = ['🐟 Tank ☣️', '🐠🐡🦈 Reef', 'Café · Рыба', '未知 😀']
    app.roster = [replace(f, name=samples[i % len(samples)]) for i, f in enumerate(app.roster)]
    app.sync_models()
    app.show_names = True
    app.show_controls()
    app.status = 'Connected to 🐟 ☣️ RX'
    app.inbox = [{'text': '🐟 ☣️ Hello 中'}]
    app._next_ui_update = 0
    for _ in range(6):
        app.taskMgr.step()
    assert app.fish_label['text'].startswith(display_text(samples[0]))
    assert display_text('🐟 ☣️ Hello 中') in app.message_label['text']
    assert display_text(app.status) in app.footer['text']

    out = Path('.local')
    out.mkdir(exist_ok=True)
    # Readable large proof within the real aquarium, not a mocked text raster.
    proof = OnscreenText(
        parent=app.views[0].aspect_root,
        text=display_text('🐟 Tank ☣️\n🐠 🐡 🦈 😀\nCafé · Рыба · Ελληνικά\nUnknown 中 → ?'),
        pos=(-1.62, .62), scale=.075, align=TextNode.ALeft,
        fg=(.83,.93,.88,1), mayChange=True,
    )
    for _ in range(3):
        app.graphicsEngine.renderFrame()
    assert app.win.saveScreenshot(str(out/'v016-unicode-controls.png'))

    # A font-coverage result is insufficient: check that emoji add real pixels.
    def capture():
        app.graphicsEngine.renderFrame()
        app.graphicsEngine.renderFrame()
        image = PNMImage()
        assert app.aquarium_window.getScreenshot(image)
        return image
    app.taskMgr.remove('aquarium-update')
    proof.setText(display_text('🐟 ☣️ 🐠 🐡 🦈'))
    present = capture()
    proof.setText('')
    absent = capture()
    differences = sum(
        max(abs(present.getXel(x,y)[c]-absent.getXel(x,y)[c]) for c in range(3)) > .1
        for y in range(100,200) for x in range(0,600)
    )
    assert differences > 150, differences
    proof.destroy()
    app.add_window((1280,0,960,540))
    for view in app.views:
        view.names.update(True,view.lens,app.camera,app.render,app.models,view.aspect)
        assert view.names.root.getNumChildren() == 12
        builds = view.names.builds
        view.names.sync(app.roster)
        assert view.names.builds == builds
        assert all(name == app.roster[i].name for i, (node,name) in enumerate(view.names.labels.values()))
    app.graphicsEngine.renderFrame()
    app.graphicsEngine.renderFrame()
    assert app.views[1].window.saveScreenshot(str(out/'v016-unicode-window-2.png'))

    controls = app.controls
    controls.page('Radio')
    controls.transport_menu.set('Bluetooth LE')
    address = 'AA:BB:CC:DD:EE:FF'
    controls.on_devices({'transport':'ble','devices':[(address,'🐟 ☣️ RX')]})
    controls.device_menu.set(next(iter(controls.devices)))
    assert controls.endpoint.get() == address
    controls.on_connection({'state':'idle','text':'Disconnected from 🐟 ☣️ RX'})
    assert display_text('Disconnected from 🐟 ☣️ RX') == controls.connection_label['text']
    app.graphicsEngine.renderFrame()
    app.graphicsEngine.renderFrame()
    assert app.win.saveScreenshot(str(out/'v016-unicode-radio.png'))
    print(f'PASS native Unicode labels, HUD, inbox, selected fish, device menu, and second window; {differences} emoji pixels',flush=True)


def main():
    if '--inside' in sys.argv:
        sys.argv.remove('--inside')
        from tank.aquarium import Aquarium
        Aquarium.run = exercise
        from tank.__main__ import main as tank_main
        tank_main()
        return
    read, write = os.pipe()
    xvfb = subprocess.Popen(
        ['Xvfb','-displayfd',str(write),'-screen','0','2560x1440x24','-nolisten','tcp'],
        pass_fds=[write],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
    )
    os.close(write)
    with os.fdopen(read) as pipe:
        display = pipe.readline().strip()
    try:
        with tempfile.TemporaryDirectory(prefix='tank-unicode-') as directory:
            result = subprocess.run(
                [sys.executable,'-m','tools.text_smoke','--inside','--demo','12',
                 '--preset','low','--width','1280','--height','720',
                 '--settings',str(Path(directory)/'settings.json')],
                env={**os.environ,'DISPLAY':':'+display},
                capture_output=True,text=True,
            )
        print(result.stdout,end='')
        print(result.stderr,end='',file=sys.stderr)
        if any(marker in result.stderr for marker in ('No definition','Unknown TextProperties','Assertion failed','glgsg(error)')):
            raise SystemExit('FAIL native text/graphics warning')
    finally:
        xvfb.terminate()
        xvfb.wait(timeout=5)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
