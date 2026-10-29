"""Actual XTest operator input, drafts, resize and page reachability (synthetic only).

python -m tools.run_native tools.controls_smoke --demo 12 --preset low --settings <isolated>/settings.json
CONTROLS_REPORT selects an external evidence directory; no physical RF/HA access.
"""
import ctypes
import ctypes.util
import os
from pathlib import Path
import time


def exercise(app):
    from panda3d.core import WindowProperties, PNMImage
    from tank.settings import Settings
    from tank.controls_shell import NAVIGATION
    out=Path(os.environ.get('CONTROLS_REPORT','.local/controls-redesign'));out.mkdir(parents=True,exist_ok=True)
    end=time.monotonic()+12
    while len(app.roster)!=12 and time.monotonic()<end:app.taskMgr.step()
    assert len(app.roster)==12
    ui=app.controls;p=ui.appearance
    a=app.window_drag.pointer.api;d=app.window_drag.pointer.display
    assert d
    x=ctypes.CDLL(ctypes.util.find_library('Xtst'))
    x.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
    x.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
    x.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
    a.XFlush.argtypes=[ctypes.c_void_p]
    a.XSetInputFocus.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
    a.XStringToKeysym.argtypes=[ctypes.c_char_p];a.XStringToKeysym.restype=ctypes.c_ulong
    a.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];a.XKeysymToKeycode.restype=ctypes.c_uint
    def frames(n=5):
        a.XFlush(d)
        for _ in range(n):app.taskMgr.step()
    def move(px,py):
        props=app.win.getProperties()
        x.XTestFakeMotionEvent(d,-1,props.getXOrigin()+int(px),props.getYOrigin()+int(py),0);frames()
    def mouse(number=1):
        x.XTestFakeButtonEvent(d,number,1,0);frames(2)
        x.XTestFakeButtonEvent(d,number,0,0);frames(3)
    def click(widget,dx=None):
        pos=app.pixel2d.getRelativePoint(widget,(0,0,0))
        if dx is None:
            l,r,b,t=widget['frameSize'];dx=(l+r)/2;dy=-(b+t)/2
        else:dy=0
        a.XSetInputFocus(d,app.win.getWindowHandle().getIntHandle(),1,0)
        move(pos.x+dx,-pos.z+dy);mouse()
    def key(name):
        code=a.XKeysymToKeycode(d,a.XStringToKeysym(name.encode()))
        assert code,name
        x.XTestFakeKeyEvent(d,code,1,0);x.XTestFakeKeyEvent(d,code,0,0);frames(2)
    def capture(name):
        frames();assert app.win.saveScreenshot(str(out/(name+'.png')))
    def size(w,h):
        props=WindowProperties();props.setSize(w,h);app.win.requestProperties(props);frames(10);ui.resize()
        assert app.win.getXSize()==w and app.win.getYSize()==h
        assert ui.root.getSx()==1
    size(1100,800);ui.refresh();capture('overview')
    assert '12 synthetic fish displayed'==ui.session_text['text']
    assert app.roster[app.selected].name in app.fish_label['text']
    assert ui._portrait_signature[0]==app.roster[app.selected]
    assert ui.mode=='demo' and ui.state!='connected'
    roster=list(app.roster);old_selected=app.selected
    app.select_next();frames(12);ui.refresh()
    assert app.selected!=(old_selected) and ui._portrait_signature[0]==app.roster[app.selected]
    # Actual sidebar click, then numeric keyboard editing in a real PGEntry.
    click(ui.tabs['Appearance']);assert ui.active_page=='Appearance'
    click(p.buttons['Light']);assert p.active=='Light'
    field=p.fields['brightness'][0];click(field,20);assert field.guiItem.getFocus() and ui.editing()
    key('Home')
    for _ in range(8):key('Delete')
    for char in '0.73':key('period' if char=='.' else char)
    assert field.get()=='0.73',field.get()
    p.update_dirty();assert p.dirty
    saved=Path(app.args.settings).read_bytes() if Path(app.args.settings).exists() else None
    old_brightness=app.settings.appearance.brightness
    click(ui.tabs['Windows & layout']);assert ui.active_page=='Deadzones'
    click(ui.tabs['Appearance']);assert field.get()=='0.73' and p.dirty
    assert app.settings.appearance.brightness==old_brightness
    p.reset();assert p.confirming;p.cancel_reset();assert field.get()=='0.73'
    capture('appearance-dirty')
    ui.viewport.verticalScroll['value']=1;frames()
    click(p.apply_button);assert abs(app.settings.appearance.brightness-.73)<1e-6
    assert Settings.load(app.args.settings).appearance.brightness==.73 and not p.dirty
    # Reset is an edit discard, never an immediate Classic write.
    field.enterText('0.84');p.reset();assert p.confirming
    p.cancel_reset();assert field.get()=='0.84'
    p.reset();p.reset();assert field.get()=='0.73' and app.settings.appearance.brightness==.73
    # Invalid fields never partially save. Preview uses only applied texture/settings.
    p.fields['night_start'][0].enterText('invalid');before=Path(app.args.settings).read_bytes()
    p.apply();assert Path(app.args.settings).read_bytes()==before
    p.refresh();p.preview(0);assert app.settings.appearance.brightness==.73
    p.preview(None);p.page('Theme');ui.viewport.verticalScroll['value']=0;frames();capture('appearance')
    assert p._preview_texture is not None and p._preview_texture.hasRamImage()
    # Main-window close requests are intercepted before losing the draft.
    field.enterText('0.82');app.messenger.send('operator-close-request');assert ui._close_dialog
    capture('discard-confirmation');ui.cancel_close();assert p.dirty and field.get()=='0.82';p.refresh()
    # Every original controller stays reachable, with disconnected writes disabled.
    for category,targets in NAVIGATION.items():
        click(ui.tabs[category]);assert ui.active_page==targets[0]
        for target in targets:
            if target not in ui.pages:continue
            ui.page(target);assert not ui.pages[target].isHidden()
            assert all(frame.isHidden() for name,frame in ui.pages.items() if name!=target)
            capture(target.lower())
    assert all(button['state']=='disabled' for button in ui.radio.write_buttons)
    for sub in ui.radio.NAMES:ui.radio.page(sub);frames();capture('radio-'+sub.lower())
    ui.page('Appearance');p.page('Light');frames()
    # Wheel routed to the inner editor, not the whole page.
    move(600,430);old=ui.viewport.verticalScroll['value'];mouse(5)
    assert p.scrollers['Light'].verticalScroll['value']>0
    assert ui.viewport.verticalScroll['value']==old
    # Tab scrolls a focused field into view and never triggers aquarium shortcuts.
    ui.blur();field['focus']=1;key('Tab');assert ui.editing()
    models={key:value[0].node() for key,value in app.models.items()}
    buffer=app.views[0].buffer
    for w,h in ((800,600),(1100,800),(1440,1000),(800,600)):
        size(w,h)
        ui.page('Appearance');p.page('Theme');capture('appearance-'+str(w))
        ui.viewport.verticalScroll['value']=1;frames();capture('appearance-bottom-'+str(w))
        ui.page('Deadzones');capture('windows-'+str(w))
        assert app.views[0].buffer==buffer
    # Scrollable bottom retains actions and focus at smaller window sizes.
    ui.page('Appearance');p.page('Water');p.scrollers['Water'].verticalScroll['value']=1
    field=p.fields['column_speed'][0];ui.reveal_field(field);field['focus']=1;frames()
    assert ui.editing();ui.blur()
    # Both scopes apply independently in the real native editor.
    p.fields['brightness'][0].enterText('0.71');p.fields['fps'][0].enterText('46')
    p.page('Quality');p.apply();assert app.settings.fps==46 and app.settings.appearance.brightness==.73
    p.page('Theme');p.apply();assert app.settings.appearance.brightness==.71
    before=app.settings.appearance.background_top
    label=next(k for k,v in p.theme_names.items() if v=='deep-sea')
    p.theme_menu.set(label);assert p.dirty and app.settings.appearance.background_top==before
    p.apply();assert app.settings.appearance.background_top=='#10344f' and app.settings.fps==46
    assert app.roster==roster and ui.mode=='demo'
    assert models=={key:value[0].node() for key,value in app.models.items()}
    assert not any(command for command in list(app.service.commands.queue) if command[0] in ('connect','clear','remove'))
    size(1100,800);ui.page('Appearance');p.page('Theme');p.refresh()
    for view in list(app.views):app.close_view(view)
    frames();p._next_preview=0;ui.refresh();assert p.preview_image['image'] is None
    app.add_window();frames();p._next_preview=0;ui.refresh();assert p.preview_image['image'] is not None
    capture('appearance-final')
    ui.page('Aquarium');capture('overview-final')
    print('PASS actual XTest sidebar, field editing, Apply, draft retention, reset/cancel, close guard, wheel/focus, all controllers, selected fish/status, 800/1100/1440 resize, demo isolation and stable render target',flush=True)

if __name__=='__main__':
    from tank.aquarium import Aquarium
    Aquarium.run=exercise
    from tank.__main__ import main
    main()
