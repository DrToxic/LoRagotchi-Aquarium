"""Native pixels, state continuity, columns, controls and layout cost evidence."""
from pathlib import Path
from dataclasses import replace
import json
import statistics
import tempfile
import time


def exercise(app):
    from panda3d.core import PNMImage, ClockObject, WindowProperties
    from tank.deadzones import Deadzone, DisplayProfile
    from tank.demo import visitors
    out=Path('.local/layout');out.mkdir(parents=True,exist_ok=True)
    end=time.monotonic()+12
    while len(app.roster)!=12 and time.monotonic()<end:app.taskMgr.step()
    assert len(app.roster)==12
    app.taskMgr.remove('aquarium-update')
    ClockObject.getGlobalClock().setMode(ClockObject.MNormal)
    models={k:v[0].node() for k,v in app.models.items()}
    swimmers={k:id(v) for k,v in app.sim.swimmers.items()}
    report={'renderer':app.aquarium_window.getGsg().getDriverRenderer(),'layout_ms':[],'mask_pixels':[]}
    def capture(name,window=None):
        for _ in range(3):app.graphicsEngine.renderFrame()
        image=PNMImage();assert (window or app.aquarium_window).getScreenshot(image)
        image.write(str(out/(name+'.png')));return image
    def layout(zones):
        app.display.zones=list(zones)
        started=time.perf_counter();app.setup_output();app.columns.update(0)
        report['layout_ms'].append((time.perf_counter()-started)*1000)
        for r in app.placement.records.values():
            if r.visible:assert app.placement.snapshot.clear_bounds(*r.bounds(r.position)),r.key
            else:assert not app.sim.physics.groups.get(r.key),r.key
        app.update_fish(.05)
    capture('baseline')
    zone=Deadzone(x=0,y=60,width=30,height=40,uid='left-shelf',edge_shelf=True)
    layout([zone])
    assert app.shelves.boxes,app.shelves.status
    app.settings.appearance.column_count=3;app.settings.appearance.column_particles=60
    app.settings.appearance.column_placement='mixed'
    for _ in range(15):app.columns.update(1/30)
    assert app.columns.anchors,app.columns.status
    capture('edge-shelf')
    anchors=list(app.columns.anchors)
    layout([zone,Deadzone(x=80,y=0,width=10,height=8)])
    assert anchors==app.columns.anchors
    # Exercise native callbacks, not only the data structures.
    app.controls.page('Decorations');panel=app.controls.decorations
    key='decoration:pirate-ship';panel.pin(key);assert app.placement.pinned(key)
    record=app.placement.records[key];pinned=record.position
    layout([Deadzone(x=0,y=0,width=100,height=100)])
    assert not record.visible and 'Pinned' in record.reason
    assert not any(app.sim.physics.groups.values())
    layout([]);assert record.visible and record.position==pinned
    panel.pin(key);assert not app.placement.pinned(key)
    panel.choose('Reef');panel.scroller.verticalScroll['value']=.85
    panel.refresh_status();capture('controls-reef-scroll',app.win)
    panel.choose('Library');capture('controls-library',app.win)
    app.controls.page('Deadzones')
    layout([zone]);app.controls.deadzones.selected=0;app.controls.deadzones.show_selected()
    app.controls.deadzones.shelf_note();capture('controls-edge-shelf',app.win)
    app.save_display(windows=True)
    saved=DisplayProfile.load(app.display_path)
    assert saved.zones[0].uid==zone.uid and saved.placements
    assert models=={k:v[0].node() for k,v in app.models.items()}
    assert swimmers=={k:id(v) for k,v in app.sim.swimmers.items()}
    # Diagnostic flat colour proves pixels, not merely accepted bounding boxes.
    app.show_names=False
    for model,_,_ in app.models.values():model.hide()
    app.bubbles.root.hide() if hasattr(app.bubbles,'root') else None
    app.columns.root.hide()
    for shape in ('Rectangle','Rounded rectangle','Ellipse'):
        for inverted in (False,True):
            z=Deadzone(shape,8,38,76,60,inverted=inverted,uid='pixel')
            layout([z])
            for model,_,_ in app.models.values():model.hide()
            nodes=[app.placement.batch,app.decorations.root]+[n for n,_ in app.plants]
            for n in nodes:n.setColor(1,0,1,1,100);n.setLightOff(100);n.setFogOff(100)
            im=capture('diagnostic-'+shape.replace(' ','-')+('-inverted' if inverted else ''))
            bad=painted=0
            for y in range(2,im.getYSize()-2,2):
                for x in range(2,im.getXSize()-2,2):
                    r,g,b=im.getXel(x,y)
                    if r>.8 and g<.15 and b>.8:
                        painted+=1
                        u=2*(x+.5)/im.getXSize()-1;v=1-2*(y+.5)/im.getYSize()
                        # Ignore a 2px contour rasterization band.
                        eps=4/min(im.getXSize(),im.getYSize())
                        if inverted:forbidden=not z.intersects((u-eps,u+eps,v-eps,v+eps),im.getXSize()/im.getYSize())
                        else:forbidden=z.contains((u-eps,u+eps,v-eps,v+eps),im.getXSize()/im.getYSize())
                        bad+=int(forbidden)
            assert bad==0,(shape,inverted,bad)
            assert painted>0,(shape,inverted,'empty diagnostic')
            report['mask_pixels'].append({'shape':shape,'inverted':inverted,'painted_samples':painted,'forbidden_samples':bad})
    for n in [app.placement.batch,app.decorations.root]+[n for n,_ in app.plants]:
        n.clearColor();n.clearLight();n.clearFog()
    layout([])
    app.columns.root.show()
    # Camera/output lifecycle, including a non-last close and complete recovery.
    for n in range(1,8):app.add_window((500+(n%4)*500,40+(n//4)*300,500,300))
    for _ in range(4):app.taskMgr.step()
    app.setup_output();capture('eight-views')
    app.close_view(app.views[2])
    capture('after-non-last-close')
    while app.views:app.close_view(app.views[-1])
    assert not any(r.visible for r in app.placement.records.values())
    app.add_window((500,40,960,540));app.setup_output();layout([])
    assert any(r.visible for r in app.placement.records.values())
    app.roster=visitors(256);app.sync_models()
    for _ in range(20):app.update_fish(1/60)
    assert len(app.sim.swimmers)==256
    started_count=app.placement.solve_count
    frame=[]
    for _ in range(30):
        started=time.perf_counter();app.update_fish(1/60);app.appearance.update(1/60);app.columns.update(1/60)
        app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
        frame.append((time.perf_counter()-started)*1000)
    assert app.placement.solve_count==started_count
    report['frame_256']={'median_ms':statistics.median(frame),'p95_ms':sorted(frame)[28]}
    report['placement_solves']=app.placement.solve_count
    report['status']=app.placement.status
    (out/'report.json').write_text(json.dumps(report,indent=2))
    print('PASS dynamic scenery/solids, pins, migration, six analytic mask pixel checks, shelves/columns, native controls, eight-view lifecycle, 256 fish; no idle placement solves',flush=True)


def main():
    import sys
    from tank.aquarium import Aquarium
    from tank.__main__ import main as run
    from tank.settings import Settings
    Aquarium.run=exercise
    with tempfile.TemporaryDirectory(prefix='aquarium-layout-') as directory:
        path=Path(directory)/'settings.json'
        settings=Settings();settings.apply('low');settings.fish_animations=False;settings.vsync=False;settings.save(path)
        sys.argv=['layout-smoke','--demo','12','--width','960','--height','540','--settings',str(path)]
        run()


if __name__=='__main__':main()
