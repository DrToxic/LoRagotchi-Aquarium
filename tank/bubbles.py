"""Decorative air bubbles that recycle only above the current water view."""
import math
import random

from panda3d.core import TransparencyAttrib

from .art import ellipsoid
from .framing import at_depth


class AirBubbles:
    def __init__(self, parent, count, camera, render, app=None):
        self.app = app
        self.camera, self.render = camera, render
        self.items = []
        self.time = 0.
        self.ready = False
        rng = random.Random(17)
        for _ in range(count):
            node = ellipsoid("bubble", (.035,.035,.046), (.42,.70,.73,.4), 8)
            node.setTransparency(TransparencyAttrib.MAlpha)
            node.reparentTo(parent)
            node.setDepthWrite(False)
            node.setScale(rng.uniform(.7,1.3))
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
        dt=min(.1,max(0.,dt));self.time+=dt
        p=self.app.settings.appearance if self.app else None
        obstacles=getattr(self.app,'bubble_obstacles',None)
        for bubble in self.items:
            phase=self.time+bubble['phase']*math.tau
            pos=bubble['node'].getPos()
            start=(pos.x,pos.y,bubble['z'])
            speed=bubble['speed']*(1+.25*math.sin(phase*.7) if p and p.bubble_dynamics else 1)
            end=(start[0]+math.cos(phase)*.12*dt,start[1]+math.sin(phase*.7)*.04*dt,start[2]+speed*dt)
            if dt and p and p.bubble_collisions and obstacles:end=obstacles.move(start,end)
            bubble['age']=bubble.get('age',0)+dt
            if end[2]>bubble['top'] or bubble['age']>150:
                end=(bubble['x'],bubble['y'],-.25);bubble['age']=0.
            bubble['z']=end[2]
            bubble['node'].setPos(*end)
