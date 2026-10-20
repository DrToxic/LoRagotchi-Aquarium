"""Renderer-only fish lifecycle; never touches a service, database or radio.

desired is authoritative, shown is the old snapshot until its exit completes.
Updates during an exit coalesce; an update during entry waits for that entry.
Every owner has exactly one model and at most one sequence in the shared world.
"""
from dataclasses import dataclass
import math
from pathlib import Path
import random

from panda3d.core import Filename, Point2, Point3, Vec3
from .framing import at_depth
from .habitat import FISH_SCALES

STYLES = ("shark","net","bag","bowl","cage")
STYLE_NAMES = ("Cartoon shark","Fish net","Water bag","Lift-out bowl","Open fish cage")
ASSETS = Path(__file__).parent/"assets"/"transitions"
ENTRY_SECONDS = 3.4
EXIT_SECONDS = 6.4
MAX_EXITS = 4


def ease(value):
    t=max(0.,min(1.,value))
    return t*t*(3-2*t)


def mix(a,b,t):
    return tuple(x+(y-x)*t for x,y in zip(a,b))


@dataclass
class Arrival:
    time: float = 0.
    landing: object = None
    retry: float = 0.
    route: object = None


@dataclass
class Departure:
    style: str
    origin: tuple
    hpr: tuple
    scale: tuple
    actor: object
    side: int
    time: float = 0.


class FishTransitions:
    def __init__(self,app,rng=None):
        self.app=app
        self.rng=rng or random.Random()
        self.shown={};self.desired={}
        self.arrivals={};self.departures={}
        self.root=app.scene.attachNewNode("fish-transitions")
        self.templates={}

    @property
    def enabled(self):
        return self.app.settings.fish_animations

    def enabled_styles(self):
        return [s for s in STYLES if self.app.settings.exit_styles.get(s,True)]

    def _release(self,owner):
        state=self.departures.pop(owner,None)
        if state:state.actor.removeNode()
        self.arrivals.pop(owner,None)
        self.shown.pop(owner,None)

    def _actor(self,style):
        if style not in self.templates:
            node=self.app.loader.loadModel(Filename.fromOsSpecific(str(ASSETS/(style+".bam"))))
            self.templates[style]=node
        return self.templates[style].copyTo(self.root)

    def _start_exit(self,owner):
        model=self.app.models[owner][0]
        styles=self.enabled_styles()
        if not styles:
            # If every pickup is deselected, a gentle swim upward still gives
            # updates an old-out/new-in sequence, not an in-place flash.
            style="swim"
            actor=self.root.attachNewNode("swim-out")
        else:
            style=self.rng.choice(styles);actor=self._actor(style)
        fish=self.shown[owner]
        scale=FISH_SCALES[fish.stage]
        actor.setScale(max(.65,scale))
        origin=tuple(model.getPos())
        projected=Point2()
        self.app.water_lens.project(self.app.camera.getRelativePoint(self.app.render,Point3(*origin)),projected)
        # Approach from the nearer horizontal edge; all views share this actor.
        side=1 if projected.x>0 else -1
        self.departures[owner]=Departure(style,origin,tuple(model.getHpr()),tuple(model.getScale()),actor,side)
        self.arrivals.pop(owner,None)

    def reconcile(self,roster):
        self.desired={f.owner:f for f in roster}
        changed=False
        if not self.enabled:
            changed=self.shown!=self.desired or bool(self.arrivals or self.departures)
            for owner,state in self.departures.items():
                if owner in self.app.models:self.app.models[owner][0].setScale(*state.scale)
                state.actor.removeNode()
            self.departures.clear();self.arrivals.clear();self.shown=dict(self.desired)
            for owner in self.app.sim.swimmers:self._hold(owner,False)
            return changed
        for owner in list(self.shown):
            if self.shown[owner]==self.desired.get(owner) or owner in self.departures:continue
            if owner in self.arrivals and owner in self.desired:continue
            swimmer=self.app.sim.swimmers.get(owner)
            # A hidden/parked fish has no visible old appearance to take out.
            if not self.app.views or swimmer is None or swimmer.parked or self.app.models[owner][0].isHidden():
                self._release(owner);changed=True
            elif len(self.departures)<MAX_EXITS:
                self._start_exit(owner);changed=True
        for owner,fish in self.desired.items():
            if owner not in self.shown:
                self.shown[owner]=fish
                self.arrivals[owner]=Arrival(-self.rng.uniform(0,.7))
                changed=True
        return changed

    def swimming(self):
        return [fish for key,fish in self.shown.items() if key not in self.departures]

    def _hold(self,owner,held):
        swimmer=self.app.sim.swimmers.get(owner)
        if swimmer is None:return
        swimmer.arriving=held
        body=self.app.sim.physics.bodies[owner].node()
        if body.isKinematic()!=held:
            body.setKinematic(held);body.setLinearVelocity(Vec3(0,0,0))

    def _clear_column(self,swimmer,point):
        start=self.top(point,3*FISH_SCALES[swimmer.stage])
        steps=max(1,math.ceil(math.dist(start,point)/.6))
        return all(self.app.sim.physics.clear_at(swimmer.stage,mix(start,point,i/steps),
                   swimmer.heading,static_only=True,ignore_walls=True) for i in range(steps+1))

    def _landing(self,owner,state):
        """Use an open descent column, including foreground shelf corridors."""
        s=self.app.sim.swimmers[owner]
        point=(s.x,s.y,s.z)
        physics=self.app.sim.physics
        route=(point,self.app.sim._view_config,physics.revision)
        if state.route==route:return True
        if not self._clear_column(s,point):
            candidates=[]
            for _ in range(32):
                candidate=self.app.sim.volume.candidate(s.rng,s.radius,outline=s.outline)
                if candidate is not None:candidates.append(candidate)
            # Prefer high, foreground arrivals; never drive through a shelf
            # just because the final swimming position below it is valid.
            candidates.sort(key=lambda p:p[1]-p[2])
            point=next((p for p in candidates if
                physics.clear_at(s.stage,p,s.heading,ignore=owner) and self._clear_column(s,p)),None)
            if point is None:
                state.landing=None;state.route=None
                return False
            s.x,s.y,s.z=point
            physics.bodies[owner].setPos(*point)
            s.remaining=0.
        state.landing=point
        state.route=(point,self.app.sim._view_config,physics.revision)
        return True

    def top(self,point,margin=3.):
        """Current combined-view top at this world depth, including resizing."""
        p=Point2()
        self.app.water_lens.project(self.app.camera.getRelativePoint(self.app.render,Point3(*point)),p)
        top=at_depth(self.app.water_lens,self.app.camera,self.app.render,p.x,1,point[1])
        return (point[0],point[1],max(point[2]+margin,top.z+margin))

    def side_point(self,point,side,margin=7.):
        p=Point2()
        self.app.water_lens.project(self.app.camera.getRelativePoint(self.app.render,Point3(*point)),p)
        edge=at_depth(self.app.water_lens,self.app.camera,self.app.render,side,p.y,point[1])
        return (edge.x+side*margin,point[1],point[2])

    def _entry(self,owner,state,dt):
        model=self.app.models[owner][0]
        swimmer=self.app.sim.swimmers[owner]
        self._hold(owner,True)
        if swimmer.parked or not self.app.views:
            model.hide();return False
        state.retry-=dt
        if state.retry>0 and state.landing is None:
            model.hide();return False
        if not self._landing(owner,state):
            state.retry=1.;model.hide();return False
        state.time+=dt
        target=(swimmer.x,swimmer.y,swimmer.z)
        start=self.top(target,3*FISH_SCALES[self.shown[owner].stage])
        t=ease(state.time/ENTRY_SECONDS)
        model.setPos(*mix(start,target,t))
        # Nose down on arrival; settle to the live swimmer's orientation.
        model.setHpr(math.degrees(swimmer.heading),swimmer.bank,
            -math.degrees(math.atan2(swimmer.vz,max(swimmer.speed,.01)))+55*math.sin(math.pi*t))
        if state.time<0:model.hide()
        else:model.show()
        return state.time>=ENTRY_SECONDS-1e-9

    def _exit(self,owner,state,dt):
        state.time+=dt
        model,tail,fins=self.app.models[owner]
        actor=state.actor;t=state.time
        origin=state.origin;scale=max(.65,FISH_SCALES[self.shown[owner].stage])
        model.show();model.setScale(*state.scale);model.setHpr(*state.hpr)
        tail.setH(math.sin(t*6)*20)
        for i,fin in enumerate(fins):fin.setH(math.sin(t*4+i)*12)
        if state.style=="shark":
            side=state.side
            # Shark faces the fish; its toothless mouth meets the whole body.
            mouth=(origin[0]+side*1.35*scale,origin[1],origin[2])
            approach=mix(self.side_point(origin,side),mouth,ease(t/2.6))
            destination=self.side_point(origin,-side,9.)
            position=mix(approach,destination,ease((t-3.3)/3.1)) if t>3.3 else approach
            actor.setPos(*position);actor.setH(180 if side>0 else 0)
            actor.find("**/tail").setH(math.sin(t*5)*17)
            actor.find("**/jaw").setZ(-.25*math.sin(math.pi*ease((t-2.2)/1.1)))
            gulp=ease((t-2.55)/.65)
            model.setPos(*origin)
            model.setScale(*(s*(1-.98*gulp) for s in state.scale))
            if gulp>=1:model.hide()
        elif state.style=="swim":
            model.setPos(*mix(origin,self.top(origin,5*scale),ease(t/EXIT_SECONDS)))
            model.setR(-50*math.sin(math.pi*ease(t/EXIT_SECONDS)))
        else:
            # Container is lowered beside the fish, then the passenger swims
            # into its opening before both are lifted beyond the current top.
            anchor=(origin[0]-state.side*2.5*scale,origin[1],origin[2])
            lower=mix(self.top(anchor,9*scale),anchor,ease(t/2.1))
            lifted=mix(anchor,self.top(anchor,9*scale),ease((t-3.5)/2.9))
            carrier=lower if t<2.1 else lifted
            actor.setPos(*carrier)
            # Cage doorway faces the starting fish. Bowls/bags enter from above.
            actor.setH(0 if state.side>0 else 180)
            boarding=ease((t-2.1)/1.4)
            point=mix(origin,anchor,boarding)
            arc=math.sin(math.pi*boarding)*(2.5*scale if state.style in ("bowl","bag") else .65*scale)
            point=(point[0],point[1],point[2]+arc)
            if t>=3.5:
                point=(lifted[0]+.10*scale*math.sin(t*3),lifted[1],lifted[2])
            model.setPos(*point)
            target_h=180 if state.side>0 else 0
            turn=(target_h-state.hpr[0]+180)%360-180
            model.setH(state.hpr[0]+turn*ease((t-1.7)/1.2))
            model.setR(-20*math.sin(math.pi*boarding))
        return t>=EXIT_SECONDS-1e-9

    def update(self,dt):
        dt=max(0.,min(.1,dt));changed=False
        for owner,state in list(self.arrivals.items()):
            if self._entry(owner,state,dt):
                self._hold(owner,False)
                self.arrivals.pop(owner);changed=True
        for owner,state in list(self.departures.items()):
            if self._exit(owner,state,dt):
                self._release(owner);changed=True
        if changed:
            self.reconcile(self.app.roster)
            self.app._sync_fish_nodes()
            # Place newly created arrivals/actors before their first frame.
            self.update(0.)

    def destroy(self):
        for node in self.templates.values():node.removeNode()
        self.templates.clear();self.arrivals.clear();self.departures.clear()
        self.shown.clear();self.desired.clear();self.root.removeNode()
