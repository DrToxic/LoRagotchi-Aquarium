"""Opt-in artwork constraints: finite geometry, repeatability, solids, budgets."""
import hashlib
import math
from panda3d.core import GeomNode,GeomVertexReader,NodePath,Vec3
from panda3d.bullet import BulletRigidBodyNode,BulletWorld,BulletSphereShape
from tank.reef_art import scenery,rock_model,plate_model,sponge_model,solid_hull,reef_texture
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
        assert len(plants)<=8
        assert all(list(points(root)))
        stat=graph_stats(root);stats.append(stat)
        bounds.append(root.getTightBounds())
        assert stat['triangles']<60000 and stat['geom_batches']<20
        root.removeNode()
    assert stats[0]['triangles']<stats[-1]['triangles']
    # Floor and large coarse forms remain; tiers do not remove focal structures.
    assert all(abs(a[i]-b[i])<.2 for lowhigh in zip(*bounds) for a,b in zip(lowhigh,lowhigh[1:]) for i in range(3))


def test_texture_is_shared_and_bounded():
    a=reef_texture();b=reef_texture()
    assert a is b and (a.getXSize(),a.getYSize())==(128,128)
    assert a.getNumComponents()==3


def test_default_app_does_not_import_study():
    # The shipped selector/config remains untouched; experiment is opt-in only.
    import tank.aquarium
    from tank.art import scenery as classic
    assert tank.aquarium.scenery is classic
