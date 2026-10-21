"""Local presentation-only journeys; never a roster event or a renewed visit.

One journey owns its original swimmer/model plus two physical corridor
reservations. Fish only relocate after the complete outline has left the image.
"""
from dataclasses import dataclass
import math
from panda3d.core import BitMask32, Vec3, TransformState
from panda3d.bullet import BulletBoxShape, BulletRigidBodyNode
from .topology import WaterTopology

MODES=('Off','Occasional','Frequent')
INTERVALS={'Occasional':(60.,120.),'Frequent':(20.,40.)}
DURATION=4.
COOLDOWN=300.


def mix(a,b,t):return tuple(x+(y-x)*t for x,y in zip(a,b))
def ease(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)


def corridor(a,b,radius):
    lo=tuple(min(x,y)-radius for x,y in zip(a,b))
    hi=tuple(max(x,y)+radius for x,y in zip(a,b))
    return (BulletBoxShape(Vec3(*((y-x)/2 for x,y in zip(lo,hi)))),
            tuple((x+y)/2 for x,y in zip(lo,hi)),(0,0,0))


@dataclass
class Route:
    landing: tuple
    hidden: tuple
    area: int


@dataclass
class Journey:
    owner: str
    source: Route
    target: Route
    revision: object
    hpr: tuple
    phase: str='exit'
    time: float=0.
    reservation: object=None
    position: object=None
    pose: object=None
    return_pose: object=None


class FishTravel:
    def __init__(self,transitions):
        self.transitions=transitions;self.app=transitions.app
        self.topology=None;self.topology_key=None;self.solve_count=0
        self.active=None;self.elapsed=0.;self.next_attempt=0.;self.cooldowns={}
        self.mode='Off';self.status='Transfers off';self.completed=0;self.attempts=0
        self.retry=0.
        self.population_key=None;self.population_revision=0

    def population_changed(self):
        """Called on roster sync, not per frame; arrivals may add new bodies."""
        key=tuple((owner,s.stage) for owner,s in self.app.sim.swimmers.items())
        if key!=self.population_key:
            self.population_key=key;self.population_revision+=1

    def refresh(self):
        sim=self.app.sim
        if self.topology_key!=sim._view_config or self.topology is None:
            self.topology_key=sim._view_config
            self.topology=WaterTopology(sim.volume);self.solve_count+=1
        return (sim._view_config,sim.physics.revision,self.population_revision)

    def reason(self):
        if not self.transitions.enabled:return 'Enable fish animations to allow transfers'
        if not self.app.display.constrain:return 'Enable window-edge protection to allow transfers'
        if not self.app.views or not self.app.sim.volume.regions:return 'Waiting for an aquarium window'
        if getattr(getattr(self.app,'window_drag',None),'active',False):return 'Waiting for the window move to finish'
        if self.topology.count<2:return 'No proven disconnected water areas'
        return ''

    def _route(self,s,point,area):
        v=self.app.sim.volume;topology=self.topology
        if not v.allows(point,s.outline):return None
        u,w=v.project(point)
        depth=sum((point[i]-v.origin[i])*v.forward[i] for i in range(3))
        edges=[*v.regions,*topology.opaque]
        candidates=[]
        for axis in (0,1):
            for boundary in sorted({p for box in edges for p in box[axis*2:axis*2+2]}):
                tangent=(v.tan_x,v.tan_y)[axis]
                # Distance to this perspective clipping plane, not an NDC
                # radius measured at the departure point (which changes near
                # the edge and could incorrectly reject a larger fish).
                margin=s.outline*math.sqrt(1+(boundary*tangent)**2)/(depth*tangent)+.015
                for sign in (-1,1):
                    uv=[u,w];uv[axis]=boundary+sign*margin
                    end=v.point(*uv,depth)
                    if topology.visible(v.footprint(end,s.outline)):continue
                    candidates.append((math.dist(point,end),end))
        for _,end in sorted(candidates):
            route=Route(tuple(point),end,area)
            if self._clear(s,route):return route
        return None

    def _clear(self,s,route):
        v=self.app.sim.volume;point,end=route.landing,route.hidden
        # Endpoint projections bound a straight swept sphere, including its
        # complete outline. The Bullet box also encloses the whole 3D sweep.
        steps=max(1,math.ceil(math.dist(point,end)/.4));previous=v.footprint(point,s.outline)
        for i in range(1,steps+1):
            box=v.footprint(mix(point,end,i/steps),s.outline)
            swept=(min(previous[0],box[0]),max(previous[1],box[1]),
                   min(previous[2],box[2]),max(previous[3],box[3]))
            if not self.topology.passage(swept,route.area):return False
            previous=box
        return self.app.sim.physics.shapes_clear([corridor(point,end,s.outline)],(0,0,0),ignore=(self._owner,))

    def _target(self,owner,source_area=None):
        self._owner=owner;s=self.app.sim.swimmers[owner]
        for _ in range(64):
            point=self.app.sim.volume.candidate(s.rng,s.radius,outline=s.outline)
            if point is None:continue
            area=self.topology.component(point)
            if area is None or area==source_area:continue
            route=self._route(s,point,area)
            if route:return route
        return None

    def _reserve(self,j):
        node=BulletRigidBodyNode('fish-travel-reservation')
        for route in (j.source,j.target):
            shape,pos,_=corridor(route.landing,route.hidden,self.app.sim.swimmers[j.owner].outline)
            node.addShape(shape,TransformState.makePos(Vec3(*pos)))
        j.reservation=self.app.sim.physics.root.attachNewNode(node)
        self.app.sim.physics.world.attachRigidBody(node)

    def _unreserve(self,j):
        if j.reservation is not None:
            self.app.sim.physics.world.removeRigidBody(j.reservation.node())
            j.reservation.removeNode();j.reservation=None

    def start(self,owner=None):
        """Bounded attempt; also used by the native regression harness."""
        revision=self.refresh()
        if self.active or self.app.display.transfers=='Off' or self.reason():return False
        self.attempts+=1
        eligible=[k for k,s in self.app.sim.swimmers.items() if not s.arriving and not s.parked and
                  k not in self.transitions.departures and self.elapsed>=self.cooldowns.get(k,0)]
        self.transitions.rng.shuffle(eligible)
        if owner is not None:eligible=[owner] if owner in eligible else []
        for key in eligible[:4]:
            s=self.app.sim.swimmers[key];self._owner=key;point=(s.x,s.y,s.z)
            area=self.topology.component(point)
            if area is None:continue
            source=self._route(s,point,area)
            if source is None:continue
            target=self._target(key,area)
            if target is None:continue
            hpr=tuple(self.app.models[key][0].getHpr())
            j=Journey(key,source,target,revision,hpr,position=point,pose=hpr)
            self._reserve(j);self.active=j
            s.travelling=True;self.transitions._hold(key,True)
            self.status='Travelling between water areas'
            return True
        self.status='Waiting for a clear exit and landing route'
        return False

    def _place(self,point):
        j=self.active;s=self.app.sim.swimmers[j.owner]
        s.x,s.y,s.z=point;s.parked=False;s.remaining=0.;s.vz=s.bank=0.
        body=self.app.sim.physics.bodies[j.owner]
        body.setPos(*point);body.node().setIntoCollideMask(BitMask32.allOn())
        body.node().setLinearVelocity(Vec3(0,0,0))

    def finish(self,restore=False):
        j=self.active
        if j is None:return
        self._unreserve(j)
        s=self.app.sim.swimmers.get(j.owner)
        if s:
            if restore:
                point=j.position or j.source.landing
                if self.app.sim.volume.allows(point,s.outline) and self.app.sim.physics.clear_at(
                    s.stage,point,s.heading,ignore=j.owner):self._place(point)
                else:
                    # Explicit animation opt-out / removed output: ordinary
                    # safe-placement recovery, never a voluntary teleport.
                    s.parked=True;self.app.sim._layout_dirty=True
            s.travelling=False;self.transitions._hold(j.owner,False);s.remaining=0.
        self.cooldowns[j.owner]=self.elapsed+COOLDOWN
        self.active=None

    def reconcile(self):
        self.cooldowns={k:t for k,t in self.cooldowns.items() if k in self.transitions.desired and t>self.elapsed}
        j=self.active
        if not j:return
        if j.owner not in self.transitions.desired:
            # Actual removal wins even while hidden. Do not resurrect an entry.
            self.finish(restore=True)
            self.transitions._release(j.owner)
        elif not self.transitions.enabled:self.finish(restore=True)

    def _recover(self,revision):
        j=self.active;s=self.app.sim.swimmers[j.owner]
        self._unreserve(j);self._owner=j.owner
        point=j.position
        # Unrelated edits and quality rebuilds need not interrupt the journey.
        valid=True
        for route in (j.source,j.target):
            route.area=self.topology.component(route.landing)
            valid=valid and route.area is not None and self.app.sim.volume.allows(route.landing,s.outline)
            valid=valid and not self.topology.visible(self.app.sim.volume.footprint(route.hidden,s.outline))
            valid=valid and self._clear(s,route)
        if valid and j.phase!='parked':
            j.revision=revision;self._reserve(j);return
        # If still fully visible in usable water, retreat from this exact pose
        # or reserve a new landing in the same area. Never snap a visible fish.
        if point and self.app.sim.volume.allows(point,s.outline) and self.app.sim.physics.clear_at(
            s.stage,point,s.heading,ignore=j.owner):
            self._place(point)
            model=self.app.models[j.owner][0];model.setPos(*point)
            if j.pose:model.setHpr(*j.pose)
            self.finish();return
        # A partially clipped fish can retreat smoothly if its original water
        # and the remaining swept corridor still exist after the edit.
        retreat=Route(j.source.landing,point,j.source.area) if point else None
        if retreat and retreat.area is not None and self.app.sim.volume.allows(retreat.landing,s.outline) and self._clear(s,retreat):
            j.source=j.target=retreat;j.phase='return';j.time=0.;j.revision=revision
            # update_fish has already written the held body's ordinary pose;
            # retain the previous *visual* pose rather than capturing that.
            j.return_pose=j.pose or j.hpr;self._reserve(j)
            self._place(retreat.landing);return
        # If an edit removed the current footprint, hide and enter through a
        # freshly validated portal. Keep identity even with every window shut.
        j.phase='parked';j.time=0.;j.revision=revision
        s.parked=True
        self.app.sim.physics.bodies[j.owner].node().setIntoCollideMask(BitMask32.allOff())
        self.app.models[j.owner][0].hide();self.retry=0.

    def _resume(self):
        j=self.active
        if not self.app.views or not self.app.sim.volume.regions:return
        target=self._target(j.owner)
        if target is None:return
        j.source=j.target=target;j.phase='entry';j.time=0.
        self._reserve(j);self._place(target.landing)

    def update(self,dt):
        self.elapsed+=dt
        revision=self.refresh();mode=self.app.display.transfers
        if mode!=self.mode:
            self.mode=mode;self.next_attempt=self.elapsed+self.transitions.rng.uniform(*INTERVALS.get(mode,(60,120)))
        j=self.active
        if j:
            if j.revision!=revision:self._recover(revision);j=self.active
            if j:
                model=self.app.models[j.owner][0]
                if j.phase=='hidden':
                    model.hide()
                    if dt>0:
                        latest=self.transitions.desired.get(j.owner)
                        if latest is not None and latest!=self.transitions.shown[j.owner]:
                            self.transitions.shown[j.owner]=latest
                            self.app._sync_fish_nodes()
                            self.transitions._hold(j.owner,True)
                            self._recover(revision)
                        else:j.phase='entry';j.time=0.
                    return
                if j.phase=='parked':
                    model.hide();self.retry-=dt
                    if self.retry<=0 and dt>0:
                        self.retry=1.;self._resume()
                    self.status='Waiting for a safe re-entry route'
                    return
                j.time+=dt
                route=j.source if j.phase=='exit' else j.target
                a,b=(route.landing,route.hidden) if j.phase=='exit' else (route.hidden,route.landing)
                t=ease(j.time/DURATION);point=mix(a,b,t);j.position=point
                model.setPos(*point)
                dx,dy,dz=(y-x for x,y in zip(a,b))
                h=math.degrees(math.atan2(dy,dx));r=-math.degrees(math.atan2(dz,max(.001,math.hypot(dx,dy))))
                # Absolute pose, including dt=0 and geometry rebuilds.
                turn=(h-j.hpr[0]+180)%360-180
                blend=math.sin(math.pi*t) if j.phase=='entry' else ease(t*4)
                j.pose=(j.hpr[0]+turn*blend,0,j.hpr[2]+(r-j.hpr[2])*blend)
                if j.phase=='return':
                    facing=(h,0,r)
                    start,end=(j.return_pose,facing) if t<.5 else (facing,j.hpr)
                    amount=ease(t*2 if t<.5 else (t-.5)*2)
                    j.pose=tuple(a+((b-a+180)%360-180)*amount for a,b in zip(start,end))
                model.setHpr(*j.pose)
                model.show()
                if j.time>=DURATION-1e-9:
                    if j.phase=='exit':
                        # Keep a real fully hidden frame before re-entry. The
                        # model and swimmer survive this coordinate change.
                        model.hide();j.phase='hidden';j.time=0.;j.position=j.target.hidden
                        self._place(j.target.landing)
                    elif j.phase in ('entry','return'):
                        self._place(j.target.landing)
                        if j.phase=='entry':self.completed+=1
                        self.finish()
                return
        reason=self.reason()
        if mode=='Off':self.status='Transfers off'
        elif reason:self.status=reason
        elif dt>0 and self.elapsed>=self.next_attempt:
            self.next_attempt=self.elapsed+self.transitions.rng.uniform(*INTERVALS[mode]);self.start()
        elif self.status in ('Transfers off','Travelling between water areas'):
            self.status=f'{self.topology.count} disconnected areas · waiting for next journey'

    def destroy(self):
        self.finish();self.cooldowns.clear()
