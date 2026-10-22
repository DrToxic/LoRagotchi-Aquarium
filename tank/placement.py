"""Event-driven scenery placement. Artwork and solid parts share one owner."""
from dataclasses import dataclass
import math
from panda3d.core import NodePath
from .bubble_columns import floor_height
from .layout import LayoutSnapshot


@dataclass
class PlacedObject:
    key: str
    node: object
    authored: tuple
    low: tuple
    high: tuple
    shapes: tuple
    batched: bool = False
    enabled: bool = True
    position: tuple | None = None
    support: str = 'floor'
    visible: bool = False
    reason: str = ''
    support_bottom: float = 0.

    def bounds(self, position):
        return (tuple(a+b for a,b in zip(position,self.low)),
                tuple(a+b for a,b in zip(position,self.high)))


class ScenePlacement:
    def __init__(self, app):
        self.app=app;self.records={};self.snapshot=None;self.revision=0
        self.sources=NodePath('scenery-source-geometry')
        self.batch=app.scene.attachNewNode('placed-static-reef')
        self.dirty=False;self.status='';self.running=False;self.solve_count=0
        self.pending=False

    def discard(self, prefix):
        for key in list(self.records):
            if key.startswith(prefix):
                record=self.records.pop(key)
                self.app.sim.physics.replace_shapes(key,[])
                record.node.removeNode()
        self.dirty=True

    def register(self,key,node,shapes=(),*,batched=False,enabled=True,sway=False):
        pos=tuple(node.getPos(self.app.scene))
        bounds=node.getTightBounds(self.app.scene)
        if bounds is None:return
        low,high=(tuple(v[i]-pos[i] for i in range(3)) for v in bounds)
        bottom=low[2]
        if sway:
            # Enclose all roll angles allowed by the appearance slider (±9°),
            # including the interior extrema, not just the current plant pose.
            radius=math.hypot(max(abs(low[0]),abs(high[0])),max(abs(low[2]),abs(high[2])))
            pad=radius*math.sin(math.radians(9))
            low=(low[0]-pad,low[1],low[2]-pad)
            high=(high[0]+pad,high[1],high[2]+pad)
        if key.startswith('reef:'):
            enabled=self.app.settings.scenery.get(key,enabled)
        record=PlacedObject(key,node,pos,low,high,tuple(shapes),batched,enabled)
        record.support_bottom=bottom
        hint=self.app.display.placements.get(key,{})
        record.position=tuple(hint.get('position',pos));record.support=hint.get('support','floor')
        self.records[key]=record
        if batched:node.reparentTo(self.sources)
        node.hide();self.dirty=True
        return record

    def set_enabled(self,key,enabled):
        if key in self.records:
            self.records[key].enabled=bool(enabled);self.apply()

    def pinned(self,key):return self.app.display.placements.get(key,{}).get('pinned',False)

    def pin(self,key,pinned):
        record=self.records.get(key)
        if record is None:return
        hint=self.app.display.placements.setdefault(key,{})
        hint.update(position=list(record.position or record.authored),support=record.support,pinned=bool(pinned))
        self.apply();self.app.save_display()

    def reset(self):
        for key,record in self.records.items():
            if not self.pinned(key):
                self.app.display.placements.pop(key,None)
                record.position=record.authored;record.support='floor'
                self._place(record,None,'Resetting placement')
        self.apply();self.app.save_display()

    def _place(self,record,position,reason='',support='floor'):
        visible=position is not None
        changed=record.visible!=visible or (visible and tuple(position)!=record.position)
        record.reason=reason
        if visible:
            record.position=tuple(position);record.support=support
            record.node.setPos(*position)
            record.node.show()
            hint=self.app.display.placements.setdefault(record.key,{})
            hint.update(position=list(position),support=support,pinned=hint.get('pinned',False))
        else:record.node.hide()
        record.visible=visible
        if changed:
            self.app.sim.physics.replace_shapes(record.key,[(shape,tuple(position[i]+offset[i] for i in range(3)),hpr)
                for shape,offset,hpr in record.shapes] if visible else [])
            self.dirty=True

    def _supported(self,record,position,support):
        low,high=record.bounds(position)
        if support=='floor':return True
        surface=next((s for s in self.app.shelves.surfaces if s.key==support),None)
        return bool(surface and low[0]>=surface.x-surface.width/2+.08 and high[0]<=surface.x+surface.width/2-.08
                    and low[1]>=surface.y-surface.depth/2+.08 and high[1]<=surface.y+surface.depth/2-.08
                    and abs(position[2]+record.support_bottom-surface.z-.03)<.02)

    def _valid(self,record,position,support,*,relocating=False):
        if not self._supported(record,position,support):return False
        low,high=record.bounds(position)
        box=self.snapshot.footprint(low,high)
        if self.app.display.protect_scenery and not self.snapshot.clear_box(box):return False
        if support=='floor' and self.app.shelves.boxes and not self.app.sim.physics.shapes_clear(record.shapes,position,only={'sand-shelves'}):return False
        if relocating:
            if not self.snapshot.visible(box):return False
            if low[0]<-22 or high[0]>22 or low[1]<-7 or high[1]>8 or high[2]>16:return False
            # New placements cannot occupy the central shared swimming lane.
            if low[0]<2.4 and high[0]>-2.4 and low[1]<2.5 and high[2]>1.5:return False
            ignore=[record.key]
            if support!='floor':ignore.append('sand-shelves')
            if not self.app.sim.physics.shapes_clear(record.shapes,position,ignore):return False
        return True

    def _candidates(self,record):
        x,y,z=record.position or record.authored
        ax,ay,az=record.authored
        points=[(ax,ay)]
        for distance in (1.5,3.,5.,8.):
            for i in range(8):points.append((x+distance*math.cos(i*math.tau/8),y+distance*math.sin(i*math.tau/8)))
        points+=sorted(((xx,yy) for xx in range(-18,19,3) for yy in (-5,-2,1,4,6)),
                       key=lambda p:(math.dist(p,(x,y)),p))
        for xx,yy in points:
            yield (xx,yy,az+floor_height(xx,yy)-floor_height(ax,ay)),'floor'
        for surface in self.app.shelves.surfaces:
            for dx,dy in ((0,0),(-.2,0),(.2,0),(0,-.2),(0,.2)):
                yield (surface.x+dx*surface.width,surface.y+dy*surface.depth,
                       surface.z-record.support_bottom+.03),surface.key

    def apply(self):
        if self.running:return
        self.running=True
        try:
            self.snapshot=LayoutSnapshot(self.app.sim.volume,self.revision+1)
            self.solve_count+=1
            pending=[]
            # Reserve all unchanged objects before searching, so an earlier
            # relocated object cannot displace an otherwise valid neighbour.
            for record in self.records.values():
                pos=record.position or record.authored
                if not record.enabled:self._place(record,None,'Disabled');continue
                if not self.snapshot.volume.regions:self._place(record,None,'No active aquarium view');continue
                if self._valid(record,pos,record.support):
                    self._place(record,pos,support=record.support)
                else:
                    self._place(record,None,'Pinned position conflicts' if self.pinned(record.key) else 'No supported space')
                    if not self.pinned(record.key):pending.append(record)
            pending.sort(key=lambda r:(-math.prod(max(.01,b-a) for a,b in zip(r.low,r.high)),r.key))
            defer=bool(getattr(getattr(self.app,'window_drag',None),'active',None))
            self.pending=bool(pending) and defer
            for record in (() if defer else pending):
                for index,(pos,support) in enumerate(self._candidates(record)):
                    if index>=160:break
                    if self._valid(record,pos,support,relocating=True):
                        self._place(record,pos,support=support);break
            if self.dirty:
                self.batch.getChildren().detach()
                for record in self.records.values():
                    if record.batched and record.visible:record.node.copyTo(self.batch)
                self.batch.flattenStrong()
                self.app.sim.obstacles_changed()
                self.revision+=1;self.dirty=False
            visible=sum(r.visible for r in self.records.values())
            waiting=sum(r.enabled and not r.visible for r in self.records.values())
            self.status=f'{visible} placed · {waiting} waiting for space'
        finally:self.running=False
