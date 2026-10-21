"""Seeded, surface-aware decorative emitters with a fixed total particle pool."""
from dataclasses import dataclass
import math
import random


@dataclass(frozen=True)
class Surface:
    key: str
    x: float
    y: float
    z: float
    width: float
    depth: float

    def contains(self, x, y, margin):
        return abs(x-self.x) < self.width/2-margin and abs(y-self.y) < self.depth/2-margin


def surfaces(boxes, placement):
    result = [] if placement == 'shelves' else [Surface('floor', 0., 1., 0., 36., 10.)]
    if placement != 'floor':
        result += [Surface(f'shelf-{i}', pos[0], pos[1], pos[2]+size[2]/2, size[0], size[1])
                   for i, (pos,size,_) in enumerate(boxes)]
    return result


def floor_height(x, y):
    return .13*math.sin(x*.3)+.07*math.cos(y*.5+x*.2)


def place_emitters(settings, available, clear, previous=()):
    """Keep valid anchors; seeded per-slot searches change only invalid placements."""
    placed = []
    margin = settings.column_width+.2
    available = [s for s in available if min(s.width,s.depth) > 2*margin]
    if not available: return placed
    count = min(settings.column_count,settings.column_particles)
    spacing = max(1.5,settings.column_width*4)
    def valid(item):
        key,x,y,z = item
        surface = next((s for s in available if s.key==key),None)
        if not surface or not surface.contains(x,y,margin):return False
        expected = floor_height(x,y) if key=='floor' else surface.z
        if abs(z-expected)>.01:return False
        if any(math.hypot(x-p[1],y-p[2])<spacing for p in placed):return False
        return clear(x,y,z,margin)
    for index in range(count):
        if index<len(previous) and valid(previous[index]):
            placed.append(previous[index]);continue
        rng=random.Random(f'{settings.column_seed}:column:{index}')
        # Round-robin encourages visible use of both floor and shelves in mixed mode.
        for attempt in range(160):
            s=available[(index+attempt//40)%len(available)]
            x=s.x+rng.uniform(-s.width/2+margin,s.width/2-margin)
            y=s.y+rng.uniform(-s.depth/2+margin,s.depth/2-margin)
            z=floor_height(x,y) if s.key=='floor' else s.z
            item=(s.key,x,y,z)
            if valid(item):placed.append(item);break
    return placed


class BubbleColumns:
    def __init__(self,app):
        self.app=app
        self.root=app.scene.attachNewNode('bubble-columns')
        self.anchors=[];self.items=[];self.key=None;self.seed=None
        self.time=0.;self.status='Columns off'

    def clear_path(self,x,y,z,margin):
        from panda3d.core import Point3
        from .framing import at_depth
        a=self.app
        top=at_depth(a.water_lens,a.camera,a.render,0,1,y).z+.15
        if top-z<1:return False
        # Ignore moving fish and world boundary planes; never change their masks.
        for dx,dy in ((0,0),(-margin,0),(margin,0),(0,-margin),(0,margin)):
            result=a.sim.physics.world.rayTestAll(Point3(x+dx,y+dy,z+.08),Point3(x+dx,y+dy,top))
            if any(hit.getNode().getMass()==0 and hit.getNode().getName()!='tank-wall'
                   for hit in result.getHits()):return False
        return True

    def configure(self):
        from panda3d.core import TransparencyAttrib
        from .art import ellipsoid
        from .framing import at_depth
        a=self.app;p=a.settings.appearance
        if not hasattr(a,'water_lens'):return
        key=(tuple((k,v) for k,v in vars(p).items() if k.startswith('column_')),
             a.shelves.boxes,a.sim.physics.revision,tuple(a.water_lens.getFov()))
        if key==self.key:return
        self.key=key
        old=self.anchors if self.seed==(p.column_seed,p.column_placement) else ()
        self.seed=(p.column_seed,p.column_placement)
        self.anchors=place_emitters(p,surfaces(a.shelves.boxes,p.column_placement),self.clear_path,old)
        self.root.getChildren().detach();self.items=[]
        if self.anchors:
            model=ellipsoid('column-bubble',(.04,.04,.052),(.42,.70,.73,.4),8)
            model.setTransparency(TransparencyAttrib.MAlpha)
            model.setDepthWrite(False)
            rng=random.Random(p.column_seed)
            for i in range(p.column_particles):
                anchor=self.anchors[i%len(self.anchors)]
                _,x,y,z=anchor
                top=at_depth(a.water_lens,a.camera,a.render,0,1,y).z+.15
                node=model.copyTo(self.root)
                node.setScale(p.column_size*rng.uniform(.7,1.3))
                self.items.append((node,x,y,z+.04,top,rng.random(),rng.uniform(.7,1.3),rng.random()*math.tau))
        self.status=f'{len(self.anchors)}/{p.column_count} columns · {len(self.items)} bubbles'
        if p.column_count and not self.anchors:self.status+=' · no clear spawning surfaces'
        print('Appearance: '+self.status,flush=True)

    def update(self,dt):
        self.configure()
        self.time+=max(0,dt)
        p=self.app.settings.appearance
        for node,x,y,z,top,phase,speed,drift in self.items:
            height=top-z
            rise=(phase*height+self.time*speed*p.column_speed)%height
            offset=p.column_width*math.sin(self.time*1.1+drift)
            node.setPos(x+offset,y+p.column_width*.3*math.cos(self.time+drift),z+rise)
            node.setColorScale(1,1,1,min(1,rise/.2))
