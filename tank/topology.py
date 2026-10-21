"""Conservative, revision-cached connectivity of the physical desktop panorama.

Possible cells include uncertain curved boundaries. Distinct possible components
therefore prove separation; a coarse curve can only suppress a journey, never
invent one across a missed narrow connection. No per-fish navigation mesh.
"""
from bisect import bisect_right
from collections import deque
from .deadzones import covered


def intersection(a,b):
    r=(max(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),min(a[3],b[3]))
    return r if r[1]>r[0] and r[3]>r[2] else None


class WaterTopology:
    def __init__(self,volume):
        self.volume=volume
        regions=volume.regions
        zones=[z for z in volume.zones if z.enabled]
        boxes=[*regions,*(z.bounds() for z in zones)]
        self.xs=sorted({-1.,1.,*(i/12-1 for i in range(25)),*(x for b in boxes for x in b[:2])})
        self.ys=sorted({-1.,1.,*(i/8-1 for i in range(17)),*(y for b in boxes for y in b[2:])})
        self.cells={};self.free=set();self.components={}
        for i,(left,right) in enumerate(zip(self.xs,self.xs[1:])):
            for j,(bottom,top) in enumerate(zip(self.ys,self.ys[1:])):
                box=(left,right,bottom,top)
                # Topology uses cell interiors. Shared edges are tested below.
                e=min(right-left,top-bottom)*1e-7
                inner=(left+e,right-e,bottom+e,top-e)
                if not covered(inner,regions):continue
                blocked=any((not z.intersects(inner,volume.aspect) if z.inverted else
                             z.contains(inner,volume.aspect)) for z in zones)
                if blocked:continue
                self.cells[i,j]=box
                if not any(z.blocks(inner,volume.aspect) for z in zones):self.free.add((i,j))
        for start in self.cells:
            if start in self.components:continue
            component=len(set(self.components.values()))
            queue=deque([start]);self.components[start]=component
            while queue:
                i,j=queue.popleft()
                for nxt in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
                    if nxt not in self.cells or nxt in self.components:continue
                    # Cells meeting at a corner do not make a water passage.
                    self.components[nxt]=component;queue.append(nxt)
        self.areas={}
        for cell in self.free:self.areas.setdefault(self.components[cell],[]).append(self.cells[cell])
        self.count=len(self.areas)
        self.opaque=[z.bounds() for z in zones if z.blackout and not z.inverted and z.shape=='Rectangle']

    def component(self,point):
        u,v=self.volume.project(point)
        cell=(bisect_right(self.xs,u)-1,bisect_right(self.ys,v)-1)
        return self.components.get(cell) if cell in self.free else None

    def visible(self,box):
        """Any projected envelope left in an active, unoccluded output?"""
        return any(piece and not covered(piece,self.opaque)
                   for region in self.volume.regions if (piece:=intersection(box,region)))

    def passage(self,box,component):
        """All visible parts remain in this area, never another window/mask.

        Only rectangular opaque blackouts are portals in this pass. Other shapes
        still participate in topology and retain their exact avoidance semantics.
        """
        allowed=self.areas.get(component,[])+self.opaque
        for region in self.volume.regions:
            piece=intersection(box,region)
            if piece and not covered(piece,allowed):return False
        return True
