"""Native opaque cave, visible egg shelves and frozen parent portrait cards."""
from dataclasses import asdict
import time
import uuid
import math
from panda3d.core import NodePath, Vec3, CardMaker, Texture, PNMImage
from panda3d.bullet import BulletBoxShape
from .art import ellipsoid, mesh, colour
from .nursery import NurseryWorker, eligible_parent, validate_parent, synthetic_parent, local_fry


def box(name,size,color):
    x,y,z=(v/2 for v in size)
    vertices=[];triangles=[]
    faces=(((0,-1,0),((-x,-y,-z),(x,-y,-z),(x,-y,z),(-x,-y,z))),
           ((0,1,0),((x,y,-z),(-x,y,-z),(-x,y,z),(x,y,z))),
           ((-1,0,0),((-x,y,-z),(-x,-y,-z),(-x,-y,z),(-x,y,z))),
           ((1,0,0),((x,-y,-z),(x,y,-z),(x,y,z),(x,-y,z))),
           ((0,0,1),((-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z))),
           ((0,0,-1),((-x,y,-z),(x,y,-z),(x,-y,-z),(-x,-y,-z))))
    for normal,points in faces:
        i=len(vertices)
        vertices.extend((p,normal,tuple(color)+(1,),(0,0)) for p in points)
        triangles.extend(((i,i+1,i+2),(i,i+2,i+3)))
    return mesh(name,vertices,triangles)


def portrait(parent):
    """Raster portrait from the immutable breeding-time appearance, not live fish."""
    image=PNMImage(96,56,3);image.fill(.035,.10,.13)
    body=colour(parent['body'],parent['tint']);scales=colour(parent['scales'],parent['tint'])
    eyes=colour(parent['eyes'],parent['tint'])
    for y in range(56):
        for x in range(96):
            u=(x-49)/29;v=(y-28)/17
            if u*u+v*v<=1:
                blend=.55 if (x//6+y//5)%3==0 else .13
                rgb=tuple((body[k]*(1-blend)+scales[k]*blend)*(.85+.15*(1-y/56)) for k in range(3))
                image.setXel(x,y,*rgb)
            elif 7<=x<27 and abs(y-28)<(27-x)*.7:
                image.setXel(x,y,*scales)
            if (x-66)**2+(y-23)**2<16:image.setXel(x,y,*eyes)
            if (x-67)**2+(y-23)**2<5:image.setXel(x,y,.01,.025,.03)
    texture=Texture('frozen-parent');texture.load(image)
    return texture


class NurseryScene:
    def __init__(self,app):
        self.app=app;self.worker=NurseryWorker(app.args)
        self.mode=None;self.context=0;self.eggs=[];self.fish=[];self.status='Nursery off'
        self.root=None;self.egg_root=None;self.key=None;self.pending=None
        self.elapsed=0.;self.next_attempt=20.;self.pending_request=False;self.refresh_in=2.;self.open_retry=False

    def bind(self,owner):
        if self.root and not self.root.isEmpty():self.root.removeNode()
        root=self.root=self.app.decor.attachNewNode('breeding-cave-and-nursery')
        root.setPos(-4.8,-1.8,.15)
        shapes=[]
        from .reef_art import rock_model, solid_hull
        stones=[((-1.7,0,1.85),(.43,1.65,1.95)),((1.7,0,1.85),(.43,1.65,1.95)),
                ((0,0,4.0),(2.1,1.65,.45)),((0,1.45,1.85),(1.7,.35,1.95))]
        # Separate rough stone solids form a genuinely hollow, opaque cave.
        for i,(pos,size) in enumerate(stones):
            n=rock_model(size,740+i,min(self.app.settings.detail,18))
            n.reparentTo(root);n.setPos(*pos)
            shapes.append((solid_hull(n),(pos),(0,0,0)))
        for z in (.2,1.15,2.1):
            n=box('nursery-shelf',(3.6,1.25,.15),(.36,.43,.37));n.reparentTo(root);n.setPos(4,0,z)
            shapes.append((BulletBoxShape(Vec3(1.8,.625,.075)),(4,0,z),(0,0,0)))
        self.egg_root=root.attachNewNode('stored-eggs')
        root.setPythonTag('bubble-origins',[('cave-roof',(0,0,4.6))])
        owner.register('nursery:cave',root,shapes,enabled=self.app.settings.nursery.enabled)
        self.key=None;self.render_eggs()

    def render_eggs(self):
        key=tuple(e['id'] for e in self.eggs)
        if self.egg_root is None or self.key==key:return
        self.key=key;self.egg_root.getChildren().detach()
        for i,egg in enumerate(self.eggs[:12]):
            x=2.65+(i%4)*.9;z=.52+(i//4)*.95
            n=ellipsoid('stored-local-egg',(.22,.22,.29),egg['preview']['body_rgb'],12)
            n.reparentTo(self.egg_root);n.setPos(x,0,z)
            for j,parent in enumerate(egg['parents']):
                cm=CardMaker('parent-portrait');cm.setFrame(-.19,.19,-.12,.12)
                card=self.egg_root.attachNewNode(cm.generate());card.setPos(x+(j-.5)*.40,-.67,z-.18)
                card.setTexture(portrait(parent));card.setLightOff();card.setTwoSided(True)

    def request_hatch(self,ident):
        if self.pending_request:raise ValueError('Nursery storage is busy')
        if ident not in {e['id'] for e in self.eggs}:raise ValueError('Choose an available stored egg')
        if not self.worker.submit('hatch',id=ident,context=self.context):raise ValueError('Nursery storage is busy; try again')
        self.pending_request=True;self.status='Hatching locally; no companion transfer'

    def remove_fry(self,owner=None):
        if not self.worker.submit('remove_fry' if owner else 'clear_fry',owner=owner,context=self.context):
            self.status='Nursery storage is busy; try again';return False
        self.pending_request=True;return True

    def request_pair(self,a,b):
        if self.pending_request or self.pending:raise ValueError('Nursery storage or pair is busy')
        settings=self.app.settings.nursery
        if not settings.enabled:raise ValueError('Enable the nursery first')
        pa,pb=validate_parent(a),validate_parent(b)
        if pa['owner']==pb['owner']:raise ValueError('Choose two different adult or elder fish')
        if a not in self.app.roster or b not in self.app.roster:
            raise ValueError('Parent changed or departed; choose again')
        if self.mode=='live' and any(synthetic_parent(f) for f in (a,b)):
            raise ValueError('Demo parents cannot breed in the live nursery')
        if self.mode=='demo' and not all(synthetic_parent(f) for f in (a,b)):
            raise ValueError('Only demo parents can breed in the demo nursery')
        if len(self.eggs)>=settings.capacity:raise ValueError('Nursery is full; existing eggs are retained')
        self.pending=(a,b);self.elapsed=0.;self.ready_time=0.;self.routes={};self.route_wait={};self.visit_time={};self.visited=set()
        self.status='Pair visiting the breeding cave'

    def roster_mode(self,mode):
        if self.mode==mode:return
        self.mode=mode;self.context+=1;self.eggs=[];self.fish=[];self.pending=None
        self.pending_request=True;self.status='Opening isolated nursery'
        self.open_retry=not self.worker.submit('open',mode=mode,context=self.context)
        if self.open_retry:self.status='Nursery storage is busy; retrying source open'
        self.key=None
        self.render_eggs()

    def update(self,dt):
        settings=self.app.settings.nursery
        if self.open_retry:
            self.open_retry=not self.worker.submit('open',mode=self.mode,context=self.context)
        self.refresh_in-=dt
        if self.refresh_in<=0 and not self.pending_request:
            self.refresh_in=2.
            self.worker.submit('refresh',context=self.context)
        for swimmer in self.app.sim.swimmers.values():swimmer.courtship=None
        while not self.worker.events.empty():
            event=self.worker.events.get_nowait()
            if event.get('context')!=self.context:continue
            if event.get('action')!='refresh':self.status=event['text'];self.pending_request=False
            if 'eggs' in event:self.eggs=event['eggs'];self.render_eggs()
            if 'fish' in event:
                fish=[local_fry(f) for f in event['fish']]
                if fish!=self.fish:
                    self.fish=fish
                    if hasattr(self.app,'merge_local_fish'):self.app.merge_local_fish()
        owner=getattr(self.app,'placement',None) or getattr(self.app,'scenery_objects',None)
        record=getattr(owner,'records',{}).get('nursery:cave')
        visible=bool(record and record.enabled and getattr(record,'visible',True))
        if not settings.enabled or not visible:
            self.pending=None;return
        self.next_attempt-=dt
        if self.pending is None and not self.pending_request and settings.automatic and self.next_attempt<=0:
            self.next_attempt=60.
            adults=[f for f in self.app.roster if eligible_parent(f)]
            if len(adults)>=2 and len(self.eggs)<settings.capacity:
                # Rotate candidates; the durable store enforces each parent's rest.
                index=int(self.app.sim.time//60)%len(adults)
                try:self.request_pair(adults[index],adults[(index+1)%len(adults)])
                except ValueError as exc:self.status=str(exc)
        if not self.pending:return
        roster={f.owner:f for f in self.app.roster}
        if any(roster.get(f.owner)!=f for f in self.pending):
            self.pending=None;self.status='Breeding cancelled: parent changed or departed';return
        self.elapsed+=dt
        # Approach the open front, obeying normal steering and collisions. Never
        # teleport or take ownership of a real arrival/departure/transfer.
        position=tuple(self.root.getPos(self.app.scene));ready=True
        for i,fish in enumerate(self.pending):
            s=self.app.sim.swimmers.get(fish.owner)
            target=(position[0]+(i-.5)*2.2,position[1]-2.6,position[2]+2.5)
            if s is None or s.parked or s.arriving or s.travelling:
                ready=False;continue
            start=(s.x,s.y,s.z)
            # Forced vertical ascent could be outside projected water at the
            # current depth, so the old route never started. No teleport or
            # collision bypass: direct approach or bounded two-leg detour.
            def clear(a,b):
                if not self.app.sim.volume.path_clear(a,b,s.outline):return False
                physics=getattr(self.app.sim,'physics',None)
                if physics is None:return True
                heading=math.atan2(b[1]-a[1],b[0]-a[0])
                steps=max(1,math.ceil(math.dist(a,b)/.65))
                return all(physics.clear_at(s.stage,tuple(x+(y-x)*j/steps for x,y in zip(a,b)),heading,static_only=True) for j in range(1,steps+1))
            self.route_wait[fish.owner]=self.route_wait.get(fish.owner,0)-dt
            waypoint=self.routes.get(fish.owner,target)
            if self.route_wait[fish.owner]<=0 or math.dist(start,waypoint)<1.5:
                self.route_wait[fish.owner]=2.
                if clear(start,target):waypoint=target
                elif hasattr(self.app.sim.volume,'candidate'):
                    candidates=[self.app.sim.volume.candidate(s.rng,s.radius,outline=s.outline) for _ in range(12)]
                    candidates=[p for p in candidates if p is not None and clear(start,p) and clear(p,target)]
                    if candidates:waypoint=min(candidates,key=lambda p:math.dist(start,p)+math.dist(p,target))
                self.routes[fish.owner]=waypoint
            if not self.app.sim.volume.path_clear(start,waypoint,s.outline):ready=False;continue
            s.activity='cruise';s.activity_left=0.;s.activity_wait=5.;s.pace_factor=.75
            s.goal=waypoint;s.courtship=waypoint;s.remaining=3.;s.replan_wait=.8
            near=sum((a-b)**2 for a,b in zip((s.x,s.y,s.z),target))<=5
            self.visit_time[fish.owner]=self.visit_time.get(fish.owner,0.)+dt if near else 0.
            if self.visit_time[fish.owner]>=6:self.visited.add(fish.owner)
            if fish.owner not in self.visited:ready=False
        if ready:
            a,b=self.pending
            accepted=self.worker.submit('create',a=asdict(a),b=asdict(b),settings=asdict(settings),id=uuid.uuid4().hex,context=self.context)
            if accepted:self.pending=None;self.pending_request=True;self.status='Storing local egg'
        elif self.elapsed>180:
            self.pending=None;self.status='Pair could not reach cave; no egg created'

    def close(self):self.worker.close()
