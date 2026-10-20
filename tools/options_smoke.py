"""Exercise actual native options and RX worker with a simulated local peer.

No physical device discovery, RF, or user's live database is used.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def exercise(app):
    from dataclasses import replace
    from panda3d.core import WindowProperties
    from tank.simulator import SimulatedRadio
    from tank.store import Store
    import tank.service as service_module
    radio=SimulatedRadio(2)
    service_module.open_transport=lambda *a,**kw:radio
    service_module.discover=lambda kind:[('COM7','COM7 · Test USB RX')]
    app.args.live_database=Path(app.args.settings).parent/'test-live.sqlite'
    controls=app.controls
    def wait_for(predicate):
        deadline=time.monotonic()+6
        while not predicate() and time.monotonic()<deadline:app.taskMgr.step()
        assert predicate()
    wait_for(lambda:len(app.roster)==12)
    app.show_controls()
    assert app.panel_visible
    Path('.local').mkdir(exist_ok=True)
    for width,height in ((1280,720),(2560,1440),(3840,2160),(800,450)):
        props=WindowProperties();props.setSize(width,height);app.win.requestProperties(props)
        for _ in range(4):app.taskMgr.step()
        app.on_window(app.win);controls.resize()
        scale=min(1.,(width-24)/controls.WIDTH,(height-24)/controls.HEIGHT)
        assert abs(app.panel.getSx()-scale)<1e-5
        assert abs(app.panel.getX()+controls.WIDTH*scale-(width-12))<1e-3
        assert controls.HEIGHT*scale<=height-24+.01
        controls.page('Aquarium');app.graphicsEngine.renderFrame()
        assert app.win.saveScreenshot(f'.local/v013-options-{width}.png')
    print('PASS compact panel fixed at 432x724px on 720p/1440p/4K; fits smaller windows',flush=True)
    props=WindowProperties();props.setSize(1280,720);app.win.requestProperties(props)
    for _ in range(4):app.taskMgr.step()
    app.on_window(app.win);controls.resize();controls.page('Radio')
    controls.transport_menu.set('USB serial')
    controls.scan_button['command']()
    wait_for(lambda:bool(controls.devices))
    controls.device_menu.set(next(iter(controls.devices)))
    assert controls.endpoint.get()=='COM7'
    controls.endpoint['focus']=1
    quality=app.settings.preset;names=app.show_names
    for key in ('f','n','v','1','delete','arrow_right'):app.messenger.send(key)
    assert app.settings.preset==quality and app.show_names==names and app.second_window is None
    assert not app.window_modes.saved and len(app.roster)==12
    app.messenger.send('tab');assert app.panel_visible
    controls.blur()
    app.graphicsEngine.renderFrame();app.graphicsEngine.renderFrame()
    assert app.win.saveScreenshot('.local/v013-radio-usb.png')
    controls.transport_menu.set('Bluetooth LE')
    controls.endpoint.enterText('AA:BB:CC:DD:EE:FF')
    controls.transport_menu.set('Network bridge')
    assert controls.local_group.isHidden() and not controls.network_group.isHidden()
    controls.host.enterText('127.0.0.1');controls.port.enterText('bad')
    controls.connect_button['command']()
    assert '1–65535' in controls.connection_label['text']
    assert len(app.roster)==12
    app.graphicsEngine.renderFrame();app.graphicsEngine.renderFrame()
    assert app.win.saveScreenshot('.local/v013-radio-bridge.png')
    controls.transport_menu.set('USB serial')
    assert controls.endpoint.get()=='COM7'
    controls.connect_button['command']()
    wait_for(lambda:controls.state=='connected' and len(app.roster)==2)
    assert controls.mode=='live' and controls.profile.serial_port=='COM7'
    app.graphicsEngine.renderFrame();assert app.win.saveScreenshot('.local/v013-radio-connected.png')
    controls.disconnect_button['command']()
    wait_for(lambda:controls.state=='idle')
    assert len(app.roster)==2 and radio.lease is None
    db=Store(app.args.live_database,app.args.session);assert len(db.roster())==2;db.close()
    controls.connect_button['command']();wait_for(lambda:controls.state=='connected')
    controls.disconnect_button['command']();wait_for(lambda:controls.state=='idle')
    print('PASS native RX tabs, device selection, input-focus shortcuts, field validation, live-store switch, connect/disconnect/reconnect',flush=True)


def main():
    if '--inside' in sys.argv:
        sys.argv.remove('--inside')
        from tank.aquarium import Aquarium
        Aquarium.run=exercise
        from tank.__main__ import main as tank_main
        tank_main();return
    read,write=os.pipe()
    xvfb=subprocess.Popen(['Xvfb','-displayfd',str(write),'-screen','0','3840x2160x24','-nolisten','tcp'],
                          pass_fds=[write],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.close(write)
    with os.fdopen(read) as pipe:display=pipe.readline().strip()
    try:
        with tempfile.TemporaryDirectory(prefix='tank-options-') as directory:
            result=subprocess.run([sys.executable,'-m','tools.options_smoke','--inside','--demo','12',
                                   '--preset','low','--settings',str(Path(directory)/'settings.json')],
                                  env={**os.environ,'DISPLAY':':'+display})
    finally:xvfb.terminate();xvfb.wait(timeout=5)
    raise SystemExit(result.returncode)

if __name__=='__main__':main()
