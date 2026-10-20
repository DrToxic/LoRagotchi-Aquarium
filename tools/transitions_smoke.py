"""Actual pickup pixels and lifecycle integration under native Panda3D.

uv run python -m tools.run_native tools.transitions_smoke --demo 8 --preset low
  --settings .local/transitions/settings.json
"""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import time
from panda3d.core import PNMImage, Point2, WindowProperties
from tank.transitions import STYLES
from tools.render_smoke import settle


def exercise(app):
    deadline=time.monotonic()+20
    while len(app.roster)!=8 and time.monotonic()<deadline:app.taskMgr.step()
    assert len(app.roster)==8
    app.service.close()
    app.taskMgr.remove("aquarium-update")
    out=Path(".local");out.mkdir(exist_ok=True)

    def advance(seconds):
        for _ in range(round(seconds*30)):app.update_fish(1/30)
    def capture(name):
        settle(app)
        image=PNMImage();assert app.aquarium_window.getScreenshot(image)
        assert image.write(str(out/name))
        return image
    def differences(a,b):
        return sum(max(abs(a.getXel(x,y)[c]-b.getXel(x,y)[c]) for c in range(3))>.06
                   for y in range(0,a.getYSize(),2) for x in range(0,a.getXSize(),2))

    app.settings.fish_animations=False
    fish=replace(app.roster[0],stage=3,body=1,scales=2,name="Lifecycle fish")
    app.roster=[fish];app.sync_models()
    app.settings.fish_animations=True
    app.show_names=False
    advance(.2)
    for style in STYLES:
        app.settings.fish_animations=False;app.sync_models()
        app.settings.fish_animations=True
        s=app.sim.swimmers[fish.owner]
        s.x,s.y,s.z=0,-4,6;s.heading=0
        app.sim.physics.bodies[fish.owner].setPos(0,-4,6)
        app.update_fish(0)
        app.settings.exit_styles={key:key==style for key in STYLES}
        old=app.transitions.shown[fish.owner]
        app.service.events.put(dict(kind="roster",mode="demo",
            fish=[replace(old,event_id=old.event_id+1,body=(old.body+1)%6)]))
        app.update(SimpleNamespace(cont="cont"))
        assert app.transitions.shown[fish.owner]==old
        advance(2.75 if style=="shark" else 3.2)
        state=app.transitions.departures[fish.owner]
        present=capture("v0111-"+style+".png")
        state.actor.hide();absent=capture("v0111-"+style+"-absent.png");state.actor.show()
        count=differences(present,absent)
        assert count>180,(style,count)
        print("PASS native actor pixels",style,count,flush=True)
        # Resize while carrier is lifting: destination follows the new top.
        if style=="bowl":
            props=WindowProperties();props.setSize(720,1000)
            app.aquarium_window.requestProperties(props);settle(app)
        advance(3.0)
        if style!="shark":
            point=Point2()
            app.water_lens.project(app.camera.getRelativePoint(app.render,state.actor.getPos()),point)
            assert point.y>1,(style,point)
        advance(1.)
        assert fish.owner in app.transitions.arrivals
        assert app.transitions.shown[fish.owner]==app.roster[0]
        advance(4.4)
        assert not app.transitions.arrivals and app.transitions.root.getNumChildren()==0
        props=WindowProperties();props.setSize(1280,720)
        app.aquarium_window.requestProperties(props);settle(app)

    app.controls.page("Animations");settle(app)
    app.set_ui_text(app.footer,"1 shared fish · synthetic animation check")
    assert app.win.saveScreenshot(str(out/"v0111-animation-controls.png"))
    # A new output during an update uses the old name and a single shared actor.
    app.roster=[replace(app.roster[0],name="Next name",event_id=999)]
    app.sync_models()
    advance(2.8)
    first=app.views[0]
    props=WindowProperties();props.setOrigin(520,32);props.setSize(1280,720)
    first.window.requestProperties(props);settle(app)
    whole=capture("v0111-panorama-whole.png")
    props=WindowProperties();props.setSize(640,720)
    first.window.requestProperties(props);settle(app)
    second=app.add_window((1160,32,640,720));settle(app)
    error=samples=0
    for v,offset in ((first,0),(second,640)):
        image=PNMImage();assert v.window.getScreenshot(image)
        for y in range(0,720,4):
            for x in range(0,640,4):
                error+=sum(abs(image.getXel(x,y)[c]-whole.getXel(x+offset,y)[c]) for c in range(3))
                samples+=3
    assert error/samples<.012,error/samples
    # Projector masks cover the animated passenger AND the carrier.
    from tank.deadzones import Deadzone
    app.display.zones=[Deadzone("Rectangle",0,0,100,100,blackout=True)]
    app.setup_output();settle(app)
    for view in app.views:
        image=PNMImage();assert view.window.getScreenshot(image)
        assert all(max(image.getXel(x,y))==0 for y in range(5,720,17) for x in range(5,640,17))
    app.display.zones=[];app.setup_output()
    print("PASS animated actor panorama RGB error",error/samples,"and full projector blackout",flush=True)
    assert second.names.labels[fish.owner][1]==app.transitions.shown[fish.owner].name
    assert len(app.transitions.departures)==1 and app.transitions.root.getNumChildren()==1
    app.set_preset("balanced")
    assert len(app.transitions.departures)==1
    advance(11.)
    assert app._model_snapshots[fish.owner].name=="Next name"
    assert all(v.names.labels[fish.owner][1]=="Next name" for v in app.views)
    print("PASS old-out/new-in, live resize, new-window labels, graphics rebuild, zero actor leaks",flush=True)
    # Closing all outputs keeps authoritative collection; pending arrivals resume.
    for v in list(app.views):app.close_view(v)
    app.roster=[replace(app.roster[0],body=4)];app.sync_models();advance(1.)
    app.add_window((520,32,1280,720));settle(app);advance(4.5)
    assert not app.transitions.arrivals and len(app.models)==1
    app.roster=[];app.sync_models();advance(7.)
    assert not app.models and not app.sim.swimmers and app.transitions.root.getNumChildren()==0
    print("PASS all-window close/reopen and removal cleanup",flush=True)
    # Dense startup must retain every identity and release its landing holds.
    from tank.demo import events
    from tank.protocol import Snapshot
    app.roster=[f for f in events(256) if isinstance(f,Snapshot)]
    app.sync_models();advance(6.)
    assert len(app.models)==len(app.sim.swimmers)==len(app.sim.physics.bodies)==256
    assert all(s.arriving==(owner in app.transitions.arrivals) for owner,s in app.sim.swimmers.items())
    assert not app.transitions.arrivals,len(app.transitions.arrivals)
    # More updates than pickup slots, followed by a geometry rebuild, must
    # preserve queued old snapshots without reading discarded model nodes.
    app.roster=[replace(f,event_id=f.event_id+2000,body=(f.body+1)%6) for f in app.roster]
    app.sync_models()
    assert len(app.transitions.departures)==4
    app.set_preset("low");app.update_fish(.05)
    assert len(app.models)==256 and len(app.transitions.departures)==4
    app.settings.fish_animations=False;app.sync_models();app.update_fish(.05)
    assert len(app.models)==256 and app.transitions.root.getNumChildren()==0
    assert not any(s.arriving for s in app.sim.swimmers.values())
    print("PASS 256 animated arrivals, bounded update queue, quality rebuild and immediate opt-out",flush=True)


from tank.aquarium import Aquarium
Aquarium.run=exercise
from tank.__main__ import main
if __name__=="__main__":main()
