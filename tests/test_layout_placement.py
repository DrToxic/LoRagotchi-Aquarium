"""Full-footprint placement, real Bullet ownership and migration regressions."""
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest
from panda3d.core import NodePath, Loader, LoaderOptions
from tank.deadzones import Deadzone, DisplayProfile
from tank.settings import Settings
from tank.simulation import Simulation
from tank.placement import ScenePlacement
from tank.decorations import DecorationLibrary
from tank.shelves import SandShelves, edge_attached, shelf_envelope, stacked_indices
from tank.layout import LayoutSnapshot
from tank.views import desktop_lenses
from tank.framing import bounds, regions, aim_at_sand


class NativeLoader:
    def loadModel(self,path,**kwargs):
        return NodePath(Loader.getGlobalPtr().loadSync(path,LoaderOptions()))


def app_at(tmp_path):
    app=SimpleNamespace(render=NodePath('world'),settings=Settings(),display=DisplayProfile(),
                        sim=Simulation(reefs=False),loader=NativeLoader(),
                        args=SimpleNamespace(settings=tmp_path/'settings.json'))
    app.scene=app.render.attachNewNode('scene');app.camera=app.render.attachNewNode('camera')
    app.camera.setPos(0,-32,12);app.placement=ScenePlacement(app);app.shelves=SandShelves(app)
    app.save_display=lambda:app.display.save(tmp_path/'display.json')
    configure(app)
    app.decorations=DecorationLibrary(app)
    return app


def configure(app,zones=(),rectangles=((0,0,960,540),)):
    import math
    app.display.zones=list(zones);app.display.identities()
    lens=app.water_lens=desktop_lenses([bounds(rectangles)])[0]
    aim_at_sand(app.camera,app.render,lens)
    q=app.camera.getQuat(app.render)
    app.sim.set_view(tuple(app.camera.getPos()),tuple(q.getRight()),tuple(q.getForward()),tuple(q.getUp()),
                     math.tan(math.radians(lens.getHfov()/2)),math.tan(math.radians(lens.getVfov()/2)),regions(rectangles),app.display.zones)
    app.shelves.layout(rectangles,lens,app.camera,app.render,snapshot=LayoutSnapshot(app.sim.volume),
                       view_ids=['test-'+str(i) for i in range(len(rectangles))])
    app.placement.apply()


def mask_for(app,record):
    a,b,c,d=app.placement.snapshot.footprint(*record.bounds(record.position))
    x=max(0,min(98,(a+b+2)*25-1));y=max(0,min(98,(2-c-d)*25-1))
    return Deadzone(x=x,y=y,width=2,height=2)


def test_auto_relocation_preserves_neighbours_and_no_per_frame_changes(tmp_path):
    app=app_at(tmp_path)
    key='decoration:treasure-chest'
    app.decorations.set_enabled('treasure-chest',True)
    record=app.placement.records[key];original=record.position
    others={k:r.position for k,r in app.placement.records.items() if r.visible and k!=key}
    zone=mask_for(app,record)
    configure(app,[zone])
    assert record.visible and record.position!=original
    assert app.placement.snapshot.clear_bounds(*record.bounds(record.position))
    assert app.sim.physics.groups[key]
    for k,pos in others.items():
        r=app.placement.records[k]
        if app.placement.snapshot.clear_bounds(*r.bounds(pos)):assert r.position==pos
    positions={k:r.position for k,r in app.placement.records.items()}
    rev=app.sim.physics.revision
    app.placement.apply()
    assert {k:r.position for k,r in app.placement.records.items()}==positions
    assert app.sim.physics.revision==rev
    configure(app)
    assert record.position!=original  # removing a mask does not reshuffle valid objects


def test_pin_omission_removes_solids_and_returns_without_unchecking(tmp_path):
    app=app_at(tmp_path);key='decoration:pirate-ship';record=app.placement.records[key]
    original=record.position;app.placement.pin(key,True)
    configure(app,[mask_for(app,record)])
    assert not record.visible and 'Pinned' in record.reason
    assert not app.sim.physics.groups[key]
    assert app.decorations.enabled(app.decorations.items['pirate-ship'])
    configure(app)
    assert record.visible and record.position==original and app.sim.physics.groups[key]
    app.placement.reset()
    assert record.position==original and app.placement.pinned(key)


def test_all_masks_omit_whole_objects_and_restore_without_ghosts(tmp_path):
    app=app_at(tmp_path)
    initial=sum(len(v) for v in app.sim.physics.groups.values())
    configure(app,[Deadzone(x=0,y=0,width=100,height=100)])
    assert all(not r.visible for r in app.placement.records.values())
    assert not any(app.sim.physics.groups.values())
    configure(app)
    assert sum(len(v) for v in app.sim.physics.groups.values())==initial


def test_cache_survives_restart_and_changed_mask_is_revalidated(tmp_path):
    app=app_at(tmp_path);r=app.placement.records['decoration:pirate-ship']
    zone=mask_for(app,r);configure(app,[zone]);app.save_display()
    saved={k:r.position for k,r in app.placement.records.items() if r.visible}
    second=app_at(tmp_path);second.display=DisplayProfile.load(tmp_path/'display.json')
    second.placement.discard('decoration:');second.decorations.refresh();configure(second,[zone])
    for k,pos in saved.items():assert second.placement.records[k].position==pytest.approx(pos)
    configure(second,[Deadzone(x=0,y=0,width=100,height=100)])
    assert not any(r.visible for r in second.placement.records.values())


def test_edge_shelf_is_wholly_in_water_stable_and_rejects_unsupported_shapes(tmp_path):
    app=app_at(tmp_path)
    zone=Deadzone(x=0,y=60,width=30,height=40,uid='edge-test',edge_shelf=True)
    configure(app,[zone])
    assert app.shelves.boxes,app.shelves.status
    assert app.shelves.keys==('shelf-edge:edge-test',)
    assert all(app.placement.snapshot.clear_bounds(*shelf_envelope(b),visible=True) for b in app.shelves.boxes)
    surface=app.shelves.surfaces[0]
    configure(app,[Deadzone(x=80,y=5,width=10,height=10),zone])
    assert app.shelves.surfaces[0]==surface
    configure(app,[replace(zone,shape='Rounded rectangle')])
    assert app.shelves.boxes and app.shelves.status['edge-test']=='Placed'
    for unsupported in (replace(zone,shape='Ellipse'),replace(zone,inverted=True),replace(zone,enabled=False)):
        configure(app,[unsupported]);assert not app.shelves.boxes
        assert app.shelves.status['edge-test']!='Placed'


def test_small_edge_contact_and_joined_seam_are_distinguished(tmp_path):
    app=app_at(tmp_path)
    zone=Deadzone(x=0,y=20,width=10,height=1)
    assert edge_attached(zone,app.placement.snapshot)
    configure(app,rectangles=((0,0,480,540),(480,0,480,540)))
    assert not edge_attached(Deadzone(x=45,y=30,width=10,height=10),app.placement.snapshot)


def test_minimized_windows_do_not_generate_stacked_supports():
    rectangles=((0,0,960,540),(0,540,960,540))
    assert stacked_indices(rectangles,(True,True))==[0]
    assert not stacked_indices(rectangles,(True,False))
    assert not stacked_indices(rectangles,(False,True))


def test_v1_migration_preserves_geometry_and_invalid_new_metadata_is_local(tmp_path):
    path=tmp_path/'display.json'
    raw={'version':1,'constrain':False,'zones':[{'shape':'Ellipse','x':12,'y':23,'width':20,'height':30,'blackout':True}],
         'windows':[[-960,-100,960,540]],'placements':{'bad':{'position':[float('nan'),0,0]}},'protect_scenery':'oops','window_ids':[3]}
    path.write_text(json.dumps(raw));before=path.read_bytes()
    p=DisplayProfile.load(path)
    assert len(p.zones)==1 and p.windows==[(-960,-100,960,540)] and p.zones[0].blackout
    assert p.protect_scenery and p.placements=={}
    assert path.read_bytes()==before
    p.identities();uid=p.zones[0].uid;p.save(path)
    assert path.with_suffix('.v1.json').read_bytes()==before
    assert json.loads(path.read_text())['version']==2
    assert DisplayProfile.load(path).zones[0].uid==uid


def test_drag_withdraws_invalid_objects_then_reflows_after_release(tmp_path):
    app=app_at(tmp_path)
    record=app.placement.records['decoration:pirate-ship'];original=record.position
    app.window_drag=SimpleNamespace(active={'moved':True})
    configure(app,[mask_for(app,record)])
    assert app.placement.pending and not record.visible
    assert not app.sim.physics.groups[record.key]
    assert record.position==original
    app.window_drag.active=None;app.placement.apply()
    assert not app.placement.pending
    assert record.visible and record.position!=original


def test_disabled_reef_solid_survives_saved_reload_and_geometry_rebuild(tmp_path):
    from tank.scenery import scenery
    app=app_at(tmp_path);key='reef:study:rock:0'
    app.settings.scenery[key]=False;app.settings.save(app.args.settings)
    app.settings=Settings.load(app.args.settings)
    for scene in ('tidal-garden','classic','tidal-garden'):
        app.placement.discard('reef:');app.settings.scene=scene
        root=app.scene.attachNewNode('test-reef')
        scenery(root,app.settings,app.placement);app.placement.apply()
        if scene=='tidal-garden':
            assert not app.placement.records[key].enabled
            assert not app.placement.records[key].visible
            assert not app.sim.physics.groups.get(key)
        app.placement.discard('reef:');root.removeNode()
