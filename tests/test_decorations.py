import json
from types import SimpleNamespace

import pytest
from panda3d.core import NodePath, Loader, LoaderOptions, Filename

from tank.collision import CollisionWorld
from tank.decorations import discover, DecorationLibrary
from tank.settings import Settings
from tank.simulation import Swimmer
from tank.shelves import shelf_boxes, stacked_indices
from tank.framing import bounds, aim_at_sand
from tank.views import desktop_lenses


def test_bundled_models_and_solid_openings():
    items,errors=discover()
    assert not errors and len(items)==5
    physics=CollisionWorld(reefs=False)
    for key in ("pirate-ship","stone-arch"):
        item=next(item for item in items if item.key==key)
        # Check local geometry, independent of placement among legacy reefs.
        physics.replace_boxes("test",item.solids)
        for stage in range(4):
            for depth in (-3,-2,-1,0,1,2,3):
                assert physics.clear_at(stage,(-2 if key=="pirate-ship" else 0,depth,2.7),1.5708,static_only=True),(key,stage,depth)
        assert not physics.clear_at(3,(-4.5,0,1.2) if key=="pirate-ship" else (2.4,0,2),static_only=True)
        physics.replace_boxes("test",[])
        assert physics.clear_at(3,(0,0,2.7),static_only=True)


def test_asset_validation_and_removed_library_files(tmp_path):
    folder=tmp_path/"custom";folder.mkdir()
    (folder/"model.egg").write_text("<CoordinateSystem> { Z-up }")
    manifest=folder/"decoration.json"
    base=dict(name="Custom rock",model="model.egg",solids=[])
    manifest.write_text(json.dumps(base))
    assert len(discover(tmp_path)[0])==1
    for change in (dict(model="../../outside.egg"),dict(scale=float("nan")),
                   dict(solids=[dict(center=[0,0,0],size=[1,-1,1])]),dict(enabled="yes")):
        manifest.write_text(json.dumps({**base,**change}))
        items,errors=discover(tmp_path)
        assert not items and len(errors)==1


@pytest.mark.parametrize("key,x",[("pirate-ship",-2),("stone-arch",0)])
def test_adult_body_physically_traverses_opening_with_bullet(key,x):
    item=next(item for item in discover()[0] if item.key==key)
    physics=CollisionWorld(reefs=False)
    physics.replace_boxes(key,item.solids)
    swimmer=Swimmer("passage-proof",3)
    swimmer.x,swimmer.y,swimmer.z=x,-3.,2.7
    swimmer.heading=1.57079632679
    physics.add("passage-proof",3,(x,-3,2.7),swimmer.heading)
    for _ in range(330):
        physics.advance({"passage-proof":swimmer},{"passage-proof":(0,1.3,0)},1/60)
    assert swimmer.y>3 and abs(swimmer.x-x)<.01 and abs(swimmer.z-2.7)<.01
    assert not physics.penetrations()


def test_decoration_toggle_reload_persistence_and_collision_cleanup(tmp_path):
    class NativeLoader:
        def loadModel(self,path,**kwargs):
            return NodePath(Loader.getGlobalPtr().loadSync(path,LoaderOptions()))
    physics=CollisionWorld(reefs=False)
    app=SimpleNamespace(scene=NodePath("scene"),render=NodePath("world"),loader=NativeLoader(),
        sim=SimpleNamespace(physics=physics,obstacles_changed=lambda:None),
        settings=Settings(),args=SimpleNamespace(settings=tmp_path/"settings.json"))
    app.scene.reparentTo(app.render)
    library=DecorationLibrary(app)
    assert not library.errors and len(library.nodes)==5
    item=library.items["pirate-ship"]
    assert physics.groups["decoration:pirate-ship"]
    library.set_enabled(item.key,False)
    assert library.nodes[item.key].isHidden() and not physics.groups["decoration:pirate-ship"]
    assert Settings.load(app.args.settings).decorations[item.key] is False
    library.refresh()
    assert library.nodes[item.key].isHidden() and not physics.groups["decoration:pirate-ship"]
    library.set_enabled(item.key,True)
    count=len(physics.statics)
    for _ in range(3):library.refresh()
    assert len(physics.statics)==count and library.root.getNumChildren()==5
    library.directory=tmp_path/"empty";library.refresh()
    assert not library.nodes and not any(physics.groups.values())


def test_stacked_shelves_have_centre_and_foreground_routes():
    rectangles=[(-600,-360,640,360),(-600,0,640,360)]
    render=NodePath("render");camera=render.attachNewNode("camera")
    camera.setPos(0,-32,12)
    full=desktop_lenses([bounds(rectangles)])[0]
    aim_at_sand(camera,render,full)
    assert stacked_indices(rectangles)==[0]
    boxes=shelf_boxes(rectangles,full,camera,render)
    assert len(boxes)==2
    physics=CollisionWorld(reefs=False);physics.replace_boxes("shelves",boxes)
    for stage in range(4):
        for z in (3,5,7,9,11,13):
            assert physics.clear_at(stage,(0,0,z),static_only=True)
    for position,size,hpr in boxes:
        assert not physics.clear_at(0,position,static_only=True)
    assert not stacked_indices([(0,0,640,360),(640,140,640,360)])


def test_settings_without_decoration_key_keep_defaults(tmp_path):
    path=tmp_path/"settings.json";path.write_text('{"preset":"high"}')
    assert Settings.load(path).decorations=={}
