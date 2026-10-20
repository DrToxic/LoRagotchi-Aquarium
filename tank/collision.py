"""Bundled Panda3D/Bullet collision detection and non-bouncy contact response.

Capsules enclose fish bodies, not flexible fins/tails. Convex rock/coral proxies
share the artwork's transforms. Bullet supplies broadphase, CCD and the solver.
"""
import math
from panda3d.core import NodePath, Vec3, loadPrcFileData
from panda3d.bullet import (BulletWorld, BulletRigidBodyNode, BulletCapsuleShape,
                           BulletConvexHullShape, BulletPlaneShape, BulletBoxShape, XUp)
from .habitat import FISH_SCALES, TANK_LIMITS, reef_rocks, coral_branches


def body_dimensions(stage):
    scale = FISH_SCALES[stage]
    # Small clearance shell around the opaque body allows solver contact slop
    # without requiring flexible tails/fins to behave like rigid paddles.
    return .70*scale*(1.1 if stage == 3 else 1.), .9*scale


def ellipsoid_hull(scale, padding=1.):
    shape = BulletConvexHullShape()
    for i in range(9):
        phi = math.pi*i/8
        for j in range(16):
            theta = math.tau*j/16
            shape.addPoint(Vec3(scale[0]*math.sin(phi)*math.cos(theta)*padding,
                                scale[1]*math.sin(phi)*math.sin(theta)*padding,
                                scale[2]*math.cos(phi)*padding))
    return shape


class CollisionWorld:
    def __init__(self, reefs=True):
        loadPrcFileData('aquarium-contacts', 'bullet-solver-iterations 24\nbullet-split-impulse true')
        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, 0))
        self.root = NodePath('fish-collision-world')
        self.bodies = {}
        self.statics = []
        self.probes = {}
        self.groups = {}
        self.revision = 0
        for axis, (low, high) in enumerate(TANK_LIMITS):
            for sign, boundary in ((1, low), (-1, high)):
                normal = [0, 0, 0]; normal[axis] = sign
                self._static('tank-wall', BulletPlaneShape(Vec3(*normal), sign*boundary))
        if reefs:
            for pos, scale, heading, colour, seed in reef_rocks():
                self._static('reef-rock', ellipsoid_hull(scale, 1.12), pos, (heading, 0, 0))
            for pos, scale, roll in coral_branches():
                self._static('coral', ellipsoid_hull(scale, 1.06), pos, (0, 0, roll))

    def _static(self, name, shape, pos=(0, 0, 0), hpr=(0, 0, 0)):
        node = BulletRigidBodyNode(name)
        node.addShape(shape)
        node.setFriction(.05)
        path = self.root.attachNewNode(node)
        path.setPos(*pos); path.setHpr(*hpr)
        self.world.attachRigidBody(node)
        self.statics.append(path)
        return path

    def replace_boxes(self, group, boxes):
        """Replace a decoration's solids, never a hull enclosing its openings.

        Entries are (world centre, full size, world HPR). The artwork and these
        proxies share transforms; removing an object removes its collisions too.
        """
        self.revision += 1
        for path in self.groups.pop(group, []):
            self.world.removeRigidBody(path.node())
            self.statics.remove(path)
            path.removeNode()
        self.groups[group] = [
            self._static(group, BulletBoxShape(Vec3(*(s/2 for s in size))), pos, hpr)
            for pos, size, hpr in boxes]

    def add(self, key, stage, pos, heading):
        if key in self.bodies:
            self.remove(key)
        radius, length = body_dimensions(stage)
        node = BulletRigidBodyNode(key)
        node.addShape(BulletCapsuleShape(radius, length, XUp))
        node.setMass(1.)
        node.setAngularFactor(Vec3(0, 0, 0))
        node.setRestitution(0.)
        node.setFriction(.05)
        node.setDeactivationEnabled(False)
        node.setCcdMotionThreshold(radius*.5)
        node.setCcdSweptSphereRadius(radius*.8)
        path = self.root.attachNewNode(node)
        path.setPos(*pos); path.setH(math.degrees(heading))
        self.world.attachRigidBody(node)
        self.bodies[key] = path

    def remove(self, key):
        path = self.bodies.pop(key)
        self.world.removeRigidBody(path.node())
        path.removeNode()

    def clear_at(self, stage, position, heading=0., ignore=None, static_only=False, ignore_walls=False):
        if stage not in self.probes:
            radius, length = body_dimensions(stage)
            node = BulletRigidBodyNode('placement-probe')
            node.addShape(BulletCapsuleShape(radius+.08, length, XUp))
            self.probes[stage] = NodePath(node)
        probe = self.probes[stage]
        probe.setPos(*position); probe.setH(math.degrees(heading))
        result = self.world.contactTest(probe.node())
        for contact in result.getContacts():
            other = contact.getNode1() if contact.getNode0() == probe.node() else contact.getNode0()
            if ignore_walls and other.getName()=="tank-wall":continue
            if other.getName() == ignore or (static_only and other.getMass() > 0):
                continue
            # Placement/anticipation require clearance, not just a negative
            # penetration depth. Treat margin contacts as occupied as well.
            return False
        return True

    def advance(self, swimmers, velocities, dt):
        for key, s in swimmers.items():
            path = self.bodies[key]
            path.setPos(s.x, s.y, s.z)
            path.setHpr(math.degrees(s.heading), s.bank,
                        -math.degrees(math.atan2(s.vz, max(.01, s.speed))))
            # Respect the solver's previous contact response. Replacing its
            # stopped velocity with full cruise speed every frame would keep
            # driving bodies into one another and create persistent overlap.
            current = path.node().getLinearVelocity()
            change = Vec3(*velocities[key])-current
            maximum = 3.*dt
            if change.length() > maximum:
                change.normalize(); change *= maximum
            path.node().setLinearVelocity(current+change)
        if dt:
            self.world.doPhysics(dt, 0)
        for key, s in swimmers.items():
            point = self.bodies[key].getPos()
            s.x, s.y, s.z = point.x, point.y, point.z

    def penetrations(self, tolerance=.025):
        """Diagnostic: actual Bullet manifold depths, not steering distances."""
        # Cached manifolds describe pre-solver contacts. Query the final body
        # transforms so diagnostics measure residual penetration, not contact.
        results = []
        for manifold in self.world.getManifolds():
            a, b = manifold.getNode0(), manifold.getNode1()
            result = self.world.contactTestPair(a, b)
            for contact in result.getContacts():
                distance = contact.getManifoldPoint().getDistance()
                if distance < -tolerance:
                    results.append((a.getName(), b.getName(), distance))
        return results
