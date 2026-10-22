"""Fixed-radius swept bubbles against cached static Bullet geometry, never fish.

The static broadphase is rebuilt only when scenery changes. No particle bodies,
no bubble/bubble interactions, and at most two sweep queries per moving bubble.
"""
from panda3d.core import NodePath, Point3, Vec3, TransformState
from panda3d.bullet import BulletWorld, BulletRigidBodyNode, BulletSphereShape


class BubbleObstacles:
    def __init__(self, physics):
        self.physics = physics
        self.revision = -1
        self.world = BulletWorld()
        self.root = NodePath('bubble-static-proxies')
        self.nodes = []
        self.shapes = {}
        self.probes = {}
        self.queries = self.contacts = self.builds = 0

    def sync(self):
        if self.revision == self.physics.revision:
            return
        for path in self.nodes:
            self.world.removeRigidBody(path.node())
            path.removeNode()
        self.nodes = []
        for source in self.physics.statics:
            if source.getName() == 'tank-wall':
                continue
            node = BulletRigidBodyNode('bubble-solid')
            for i in range(source.node().getNumShapes()):
                node.addShape(source.node().getShape(i), source.node().getShapeTransform(i))
            path = self.root.attachNewNode(node)
            path.setTransform(source.getTransform(self.physics.root))
            self.world.attachRigidBody(node)
            self.nodes.append(path)
        self.revision = self.physics.revision
        self.builds += 1

    def shape(self,radius):
        radius=round(radius,4)
        if radius not in self.shapes:self.shapes[radius]=BulletSphereShape(radius)
        return self.shapes[radius]

    def clear(self,position,radius):
        self.sync()
        radius=round(radius,4)
        if radius not in self.probes:
            node=BulletRigidBodyNode('bubble-origin-probe');node.addShape(self.shape(radius))
            self.probes[radius]=NodePath(node)
        probe=self.probes[radius];probe.setPos(*position)
        return self.world.contactTest(probe.node()).getNumContacts()==0

    def move(self, start, end, radius=.075):
        self.sync()
        delta = Vec3(*(b-a for a,b in zip(start,end)))
        if delta.lengthSquared() < 1e-12:
            return tuple(end)
        self.queries += 1
        hit = self.world.sweepTestClosest(self.shape(radius),
            TransformState.makePos(Point3(*start)), TransformState.makePos(Point3(*end)))
        if not hit.hasHit():
            return tuple(end)
        self.contacts += 1
        normal = hit.getHitNormal()
        normal.normalize()
        point = Point3(*start) + delta*max(0., hit.getHitFraction()-.01)
        remainder = delta*(1-hit.getHitFraction())
        slide = remainder-normal*min(0., remainder.dot(normal))
        # An underside needs a small lateral nudge; an exactly vertical ray has
        # no tangent. A stable direction keeps bubbles moving towards an edge.
        if slide.lengthSquared() < delta.lengthSquared()*.04:
            slide += Vec3(delta.length()*.8, 0, 0)
        target = point + slide
        self.queries += 1
        second = self.world.sweepTestClosest(self.shape(radius),
            TransformState.makePos(point), TransformState.makePos(target))
        if second.hasHit():
            target = point+slide*max(0., second.getHitFraction()-.01)
        return tuple(target)


def object_origins(app):
    """Named authored ports follow the owning object's placed transform/visibility."""
    owner = getattr(app, 'placement', None) or getattr(app, 'fixed_scenery', None)
    if owner is None:
        owner = getattr(app, 'scenery_objects', None)
    result = []
    for key, record in getattr(owner, 'records', {}).items():
        if not record.enabled or not getattr(record, 'visible', True):
            continue
        if not getattr(record,'bubble_origins',()):
            continue
        position = record.position
        if position is None:
            continue
        for name, offset in record.bubble_origins:
            result.append((key+':'+name, *(position[i]+offset[i] for i in range(3))))
    return result
