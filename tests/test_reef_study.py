"""Opt-in artwork constraints: finite geometry, repeatability, solids, budgets."""
import hashlib
import math
from panda3d.core import GeomNode,GeomVertexReader,NodePath,Vec3
from panda3d.bullet import BulletRigidBodyNode,BulletWorld,BulletSphereShape
from tank.reef_art import scenery,rock_model,plate_model,sponge_model,solid_hull,reef_texture,seagrass_model,seagrass_site
from tank.decoration_panel import scenery_category,scenery_name
from tank.settings import Settings
from tools.reef_study import graph_stats


def points(root):
    nodes=list(root.findAllMatches('**/+GeomNode'))
    if isinstance(root.node(),GeomNode):nodes.insert(0,root)
    for path in nodes:
        for geom in path.node().getGeoms():
            data=geom.getVertexData()
            for column in ('vertex','normal'):
                reader=GeomVertexReader(data,column)
                while not reader.isAtEnd():
                    value=reader.getData3()
                    assert all(math.isfinite(n) for n in value)
            yield memoryview(data.getArray(0)).tobytes()


def test_original_geometry_is_finite_and_seeded():
    a=rock_model((3,2,1),11,18);b=rock_model((3,2,1),11,18);c=rock_model((3,2,1),12,18)
    digest=lambda n:hashlib.sha256(b''.join(points(n))).digest()
    assert digest(a)==digest(b) and digest(a)!=digest(c)
    assert list(points(plate_model(2,(.4,.6,.5),18,5)))
    assert list(points(sponge_model(2,.5,(.6,.4,.3),18,5)))


def test_solid_mesh_produces_working_collision_proxy():
    world=BulletWorld();solid=BulletRigidBodyNode('rock')
    solid.addShape(solid_hull(rock_model((3,2,1),11,18)));world.attach(solid)
    probe=BulletRigidBodyNode('probe');probe.addShape(BulletSphereShape(.2))
    path=NodePath(probe);path.setPos(0,0,0)
    assert world.contactTest(probe).getNumContacts()>0
    path.setPos(7,0,0)
    assert world.contactTest(probe).getNumContacts()==0


def test_quality_keeps_composition_and_bounds_work():
    stats=[];bounds=[]
    for tier in ('compatibility','low','balanced','high','ultra'):
        settings=Settings();settings.apply(tier)
        root=NodePath('test');plants,_=scenery(root,settings)
        assert len(plants)==settings.plants
        assert all(list(points(root)))
        stat=graph_stats(root);stats.append(stat)
        bounds.append(root.getTightBounds())
        assert stat['triangles']<60000 and stat['geom_batches']<=settings.plants+5
        root.removeNode()
    assert stats[0]['triangles']<stats[-1]['triangles']
    # Floor and large coarse forms remain; tiers do not remove focal structures.
    assert all(abs(a[i]-b[i])<.2 for lowhigh in zip(*bounds) for a,b in zip(lowhigh,lowhigh[1:]) for i in range(3))


def test_texture_is_shared_and_bounded():
    a=reef_texture();b=reef_texture()
    assert a is b and (a.getXSize(),a.getYSize())==(128,128)
    assert a.getNumComponents()==3


def test_default_scene_and_explicit_classic_use_real_providers():
    from tank.scenery import scenery as selected
    for scene,expected in (('tidal-garden','reef:study:'),('classic','reef:rock:')):
        class Placement:
            def __init__(self):self.keys=[]
            def register(self,key,*args,**kwargs):self.keys.append(key)
        placement=Placement();root=NodePath('test')
        selected(root,Settings(scene=scene),placement)
        assert any(k.startswith(expected) for k in placement.keys)
        root.removeNode()


def test_grass_is_seeded_single_batch_and_leaves_the_centre_open():
    digest=lambda n:hashlib.sha256(b''.join(points(n))).digest()
    a=seagrass_model(4,.35,18,800)
    assert digest(a)==digest(seagrass_model(4,.35,18,800))
    assert digest(a)!=digest(seagrass_model(4,.35,18,801))
    assert graph_stats(a)['geom_batches']==1
    for index in range(100):
        pos,height=seagrass_site(index)
        n=seagrass_model(height,.42,28,800+index);n.setPos(*pos)
        # Include the maximum supported sway, not just the neutral blade pose.
        for roll in (-9,0,9):
            n.setR(roll);low,high=n.getTightBounds()
            assert high.x<-2.4 or low.x>2.4
        n.removeNode()


def test_zero_and_maximum_plant_budgets():
    settings=Settings()
    for count in (0,100):
        settings.plants=count;root=NodePath('test')
        plants,_=scenery(root,settings)
        assert len(plants)==count
        assert len({phase for _,phase in plants})==count
        assert graph_stats(root)['geom_batches']<=count+5
        root.removeNode()


def test_every_scene_placement_appears_in_exactly_one_native_category():
    class Placement:
        def __init__(self):self.keys=[]
        def register(self,key,*args,**kwargs):self.keys.append(key)
    from tank.art import scenery as classic
    for provider in (classic,scenery):
        placement=Placement();root=NodePath('test');settings=Settings()
        provider(root,settings,placement)
        assert sum(scenery_category(k)=='Plants' for k in placement.keys)==settings.plants
        assert any(scenery_category(k)=='Reef' for k in placement.keys)
        assert all(scenery_category(k) in ('Plants','Reef') for k in placement.keys)
        assert all('study' not in scenery_name(k).lower() for k in placement.keys)
        root.removeNode()
    assert scenery_category('decoration:pirate-ship') is None
