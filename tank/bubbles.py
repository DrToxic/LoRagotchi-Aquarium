"""Decorative air bubbles that recycle only above the current water view."""
import math
import random

from panda3d.core import TransparencyAttrib

from .art import ellipsoid
from .framing import at_depth


class AirBubbles:
    def __init__(self, parent, count, camera, render):
        self.camera, self.render = camera, render
        self.items = []
        self.time = 0.
        self.ready = False
        rng = random.Random(17)
        for _ in range(count):
            node = ellipsoid("bubble", (.035,.035,.046), (.42,.70,.73,.4), 8)
            node.setTransparency(TransparencyAttrib.MAlpha)
            node.reparentTo(parent)
            self.items.append(dict(node=node, x=rng.uniform(-18,18), y=rng.uniform(-4,6),
                                   phase=rng.random(), speed=rng.uniform(.2,.5)))

    def set_view(self, lens):
        for bubble in self.items:
            bubble["top"] = at_depth(lens,self.camera,self.render,0,1,bubble["y"]).z+.15
            if not self.ready:
                bubble["z"] = -.25+bubble["phase"]*(bubble["top"]+.25)
                bubble["node"].setPos(bubble["x"],bubble["y"],bubble["z"])
        self.ready = True

    def update(self, dt):
        if not self.ready:
            return
        self.time += max(0.,dt)
        for bubble in self.items:
            bubble["z"] += bubble["speed"]*max(0.,dt)
            if bubble["z"] > bubble["top"]:
                bubble["z"] = -.25  # hidden beneath the sand, not mid-water
            bubble["node"].setPos(bubble["x"]+math.sin(self.time+bubble["phase"]*math.tau)*.12,
                                  bubble["y"],bubble["z"])
