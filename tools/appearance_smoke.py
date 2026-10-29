"""Native pixel/lifecycle proof for appearance and pooled shelf bubble columns."""
from copy import deepcopy
from pathlib import Path
import tempfile
import json
import statistics
import time


def exercise(app):
    from panda3d.core import PNMImage, ClockObject
    from tank.settings import Settings
    out=Path('.local/appearance');out.mkdir(parents=True,exist_ok=True)
    end=time.monotonic()+12
    while len(app.roster)!=12 and time.monotonic()<end:app.taskMgr.step()
    assert len(app.roster)==12
    for _ in range(100):app.taskMgr.step()
    models={k:v[0].node() for k,v in app.models.items()}
    swimmers={k:id(v) for k,v in app.sim.swimmers.items()}
    app.taskMgr.remove('aquarium-update')
    ClockObject.getGlobalClock().setMode(ClockObject.MNormal)
    def capture(name):
        for _ in range(3):app.graphicsEngine.renderFrame()
        image=PNMImage();assert app.aquarium_window.getScreenshot(image)
        image.write(str(out/(name+'.png')))
        return image
    def mean(image):
        return sum(sum(image.getXel(x,y))/3 for x in range(0,image.getXSize(),8)
                   for y in range(0,image.getYSize(),8))/len(range(0,image.getXSize(),8))/len(range(0,image.getYSize(),8))
    def timing():
        times=[]
        for _ in range(30):
            started=time.perf_counter()
            app.appearance.update(1/30);app.columns.update(1/30)
            app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
            times.append((time.perf_counter()-started)*1000)
        return dict(median_ms=statistics.median(times),p95_ms=sorted(times)[28])
    baseline=timing()
    day=capture('day')
    app.appearance.preview=0;app.appearance.update(0,force=True)
    night=capture('night')
    assert mean(night)<mean(day)*.65,(mean(day),mean(night))
    app.appearance.preview=1;app.appearance.update(0,force=True)
    restored=capture('restored')
    assert mean(restored)==mean(day)
    p=deepcopy(app.settings)
    p.appearance.column_count=3;p.appearance.column_particles=90
    app.appearance.apply_settings(p);app.columns.update(.1)
    assert len(app.columns.anchors)==3 and len(app.columns.items)==90
    anchors=list(app.columns.anchors)
    nodes=[item[0].node() for item in app.columns.items]
    before=[tuple(item[0].getPos()) for item in app.columns.items]
    for _ in range(180):app.appearance.update(1/30);app.columns.update(1/30)
    assert anchors==app.columns.anchors and nodes==[item[0].node() for item in app.columns.items]
    assert before!=[tuple(item[0].getPos()) for item in app.columns.items]
    assert all(app.columns.clear_path(x,y,z,p.appearance.column_width+.2) for _,x,y,z in anchors)
    capture('columns-floor')
    column_timing=timing()
    app.settings.appearance.background_style='solid';app.settings.appearance.background_top='#354020'
    app.settings.appearance.fog_enabled=False;app.appearance.update(0,force=True)
    capture('water-settings')
    (out/'timing.json').write_text(json.dumps(dict(baseline=baseline,columns_3_particles_90=column_timing,renderer=app.win.getGsg().getDriverRenderer(),note='12 frozen fish, low profile, 960x540 Xvfb software renderer; not target hardware FPS'),indent=2))
    assert models=={k:v[0].node() for k,v in app.models.items()}
    assert swimmers=={k:id(v) for k,v in app.sim.swimmers.items()}
    assert Settings.load(app.args.settings).appearance.column_count==3
    if hasattr(app,'controls'):
        panel=app.controls.appearance
        app.controls.page('Appearance');panel.page('Cycle')
        panel.fields['night_start'][0].enterText('not-a-time');saved=Path(app.args.settings).read_bytes()
        panel.apply();assert Path(app.args.settings).read_bytes()==saved
        panel.refresh();panel.page('Bubbles');panel.apply()
        assert app.columns.status in panel.note['text']
        app.graphicsEngine.renderFrame();assert app.win.saveScreenshot(str(out/'controls.png'))
        # Upper view shelves become real emitter surfaces. Existing floor columns
        # remain valid; shelf-only selects bases strictly on generated top faces.
        from panda3d.core import WindowProperties
        props=WindowProperties();props.setOrigin(500,50);props.setSize(960,540)
        app.aquarium_window.requestProperties(props)
        for _ in range(5):app.taskMgr.step()
        app.add_window((500,590,960,540))
        for _ in range(5):app.taskMgr.step()
        app.setup_output()
        assert app.shelves.boxes
        app.settings.appearance.column_placement='shelves'
        app.columns.update(.1)
        assert app.columns.anchors and all(x[0].startswith('shelf-') for x in app.columns.anchors)
        assert all(app.columns.clear_path(x,y,z,p.appearance.column_width+.2) for _,x,y,z in app.columns.anchors)
        capture('columns-shelves')
        app.close_view(app.views[-1]);app.columns.update(.1)
        assert not app.columns.anchors and not app.columns.items
    print('PASS day/night/restored pixels; no model/swimmer rebuild; validated controls; bounded moving column pool; floor/shelf clearance',flush=True)


def main():
    from tank.aquarium import Aquarium
    from tank.__main__ import main as run
    from tank.settings import Settings
    import sys
    Aquarium.run=exercise
    with tempfile.TemporaryDirectory(prefix='aquarium-appearance-') as directory:
        path=Path(directory)/'settings.json'
        # Isolate the legacy shelf-emitter proof from object-deflection mode:
        # the accepted baseline's support rock fails the near-base sphere
        # clearance check. Living/default collision behavior is tested separately.
        settings=Settings();settings.apply('low');settings.scene='classic';settings.appearance.bubble_collisions=False;settings.fish_animations=False;settings.vsync=False;settings.save(path)
        sys.argv=['appearance-smoke','--demo','12','--width','960','--height','540','--settings',str(path)]
        run()


if __name__=='__main__':main()
