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


def surfaces(boxes, placement, registered=None):
    result = [] if placement == 'shelves' else [Surface('floor', 0., 1., 0., 36., 10.)]
    if placement != 'floor':
        result += list(registered) if registered is not None else [Surface(f'shelf-{i}', pos[0], pos[1], pos[2]+size[2]/2, size[0], size[1])
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
        self.time=0.;self.status='Columns off';self.states=[]

    def clear_path(self,x,y,z,margin):
        return self.column_top(x,y,z,margin) is not None

    def column_top(self,x,y,z,margin):
        from panda3d.core import Point3
        from .framing import at_depth
        a=self.app
        top=at_depth(a.water_lens,a.camera,a.render,0,1,y).z+.15
        layout=getattr(getattr(a,'placement',None),'snapshot',None)
        if layout:
            # Stop at the first mask/window boundary, with enough margin for
            # the entire drift envelope and largest particle. Swept boxes make
            # thin masks/gaps impossible to tunnel through between samples.
            radius=.052*1.3*a.settings.appearance.column_size
            start=z+.04
            low=start
            if not layout.clear_bounds((x-margin,y-margin,low-radius),(x+margin,y+margin,low+radius),visible=True):return None
            while low<top:
                high=min(top,low+.25)
                if not layout.clear_bounds((x-margin,y-margin,low-radius),(x+margin,y+margin,high+radius),visible=True):
                    top=low;break
                low=high
        if top-z<1:return None
        if a.settings.appearance.bubble_collisions:
            obstacles=getattr(a,'bubble_obstacles',None)
            return top if obstacles is None or obstacles.clear((x,y,z+.04),.091*a.settings.appearance.column_size) else None
        # Ignore moving fish and world boundary planes; never change their masks.
        for dx,dy in ((0,0),(-margin,0),(margin,0),(0,-margin),(0,margin)):
            result=a.sim.physics.world.rayTestAll(Point3(x+dx,y+dy,z+.08),Point3(x+dx,y+dy,top))
            if any(hit.getNode().getMass()==0 and hit.getNode().getName()!='tank-wall'
                   for hit in result.getHits()):return None
        return top

    def configure(self):
        from panda3d.core import TransparencyAttrib
        from .art import ellipsoid
        from .framing import at_depth
        a=self.app;p=a.settings.appearance
        if not hasattr(a,'water_lens'):return
        key=(tuple((k,v) for k,v in vars(p).items() if k.startswith('column_') or k.startswith('bubble_')),
             a.shelves.boxes,tuple(getattr(a.shelves,'surfaces',())),a.sim.physics.revision,
             getattr(getattr(a,'placement',None),'revision',0),tuple(a.water_lens.getFov()),
             tuple(a.sim.volume.regions),tuple(a.sim.volume.zones),tuple(a.sim.volume.origin),tuple(a.sim.volume.forward))
        if key==self.key:return
        self.key=key
        old=self.anchors if self.seed==(p.column_seed,p.column_placement) else ()
        self.seed=(p.column_seed,p.column_placement)
        self.anchors=place_emitters(p,surfaces(a.shelves.boxes,p.column_placement,getattr(a.shelves,'surfaces',None)),self.clear_path,old)
        from .bubble_physics import object_origins
        if p.column_placement in ('objects','all'):
            ports=[port for port in object_origins(a) if self.clear_path(*port[1:],p.column_width+.2)]
            limit=p.column_count if p.column_placement=='objects' else (p.column_count+1)//2
            selected=ports[:min(limit,p.column_particles)]
            self.anchors=selected if p.column_placement=='objects' else selected+self.anchors[:p.column_count-len(selected)]
        self.root.getChildren().detach();self.items=[];self.states=[]
        if self.anchors:
            tops={anchor:self.column_top(anchor[1],anchor[2],anchor[3],p.column_width+.2) for anchor in self.anchors}
            model=ellipsoid('column-bubble',(.04,.04,.052),(.42,.70,.73,.4),8)
            model.setTransparency(TransparencyAttrib.MAlpha)
            model.setDepthWrite(False)
            rng=random.Random(p.column_seed)
            for i in range(p.column_particles):
                anchor=self.anchors[i%len(self.anchors)]
                _,x,y,z=anchor
                top=tops[anchor]
                if top is None:continue
                node=model.copyTo(self.root)
                node.setScale(p.column_size*rng.uniform(.7,1.3))
                phase=rng.random()
                self.items.append((node,x,y,z+.04,top,phase,rng.uniform(.7,1.3),rng.random()*math.tau))
                self.states.append(dict(pos=(x,y,z+.04),age=0.,delay=phase*3))
        self.status=f'{len(self.anchors)}/{p.column_count} columns · {len(self.items)} bubbles'
        if p.column_count and not self.anchors:self.status+=' · no clear spawning surfaces'
        print('Appearance: '+self.status,flush=True)

    def update(self,dt):
        if getattr(getattr(self.app,'window_drag',None),'active',None):
            self.root.hide();return
        self.root.show()
        self.configure()
        self.time+=max(0,dt)
        p=self.app.settings.appearance
        dt=min(.1,max(0.,dt))
        obstacles=getattr(self.app,'bubble_obstacles',None)
        layout=getattr(getattr(self.app,'placement',None),'snapshot',None)
        for item,state in zip(self.items,self.states):
            node,x,y,z,top,phase,speed,drift=item
            if state['delay']>0:
                if dt:state['delay']=max(0.,state['delay']-dt)
                node.hide();continue
            node.show()
            start=state['pos']
            dynamic=1+.22*math.sin(self.time*1.3+drift) if p.bubble_dynamics else 1
            vx=p.column_width*math.cos(self.time*1.1+drift)
            vy=p.column_width*.3*math.sin(self.time+drift)
            end=(start[0]+vx*dt,start[1]+vy*dt,start[2]+dt*speed*p.column_speed*dynamic)
            if dt and p.bubble_collisions and obstacles:end=obstacles.move(start,end,.07*p.column_size*1.3)
            state['age']+=dt
            radius=.07*p.column_size*1.3
            outside=layout and not layout.clear_bounds(
                tuple(min(a,b)-radius for a,b in zip(start,end)),
                tuple(max(a,b)+radius for a,b in zip(start,end)),visible=True)
            # Finite lifetime releases bubbles trapped beneath a closed ceiling.
            expired=end[2]>top or state['age']>max(12,(top-z)/max(.07,speed*p.column_speed)*3) or outside
            if expired:
                end=(x,y,z);state['age']=0.;state['delay']=phase*.65 if p.bubble_dynamics else 0.
                node.hide()
            state['pos']=end
            node.setPos(*end)
            node.setColorScale(1,1,1,min(1,state['age']/.3))
