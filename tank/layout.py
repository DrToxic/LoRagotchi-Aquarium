"""Shared projected placement policy, independent of the fish navigation policy."""
from itertools import product
from .deadzones import covered


class LayoutSnapshot:
    def __init__(self, volume, revision=0):
        # Capture values, not a mutable reference to the live swim volume.
        from .swim_volume import SwimVolume
        self.volume=SwimVolume()
        self.volume.configure(volume.origin,volume.right,volume.forward,volume.up,
                              volume.tan_x,volume.tan_y,volume.regions,volume.zones,True)
        self.revision=revision

    def footprint(self, low, high):
        points=[]
        for p in product(*zip(low,high)):
            depth=sum((p[i]-self.volume.origin[i])*self.volume.forward[i] for i in range(3))
            if depth<=.1:return (-1e6,1e6,-1e6,1e6)
            points.append(self.volume.project(p))
        return (min(p[0] for p in points),max(p[0] for p in points),
                min(p[1] for p in points),max(p[1] for p in points))

    def clear_box(self, box, *, visible=False):
        if visible and not covered(box,self.volume.regions):return False
        return not any(z.blocks(box,self.volume.aspect) for z in self.volume.zones)

    def visible(self, box):
        return any(min(box[1],b)>max(box[0],a) and min(box[3],d)>max(box[2],c)
                   for a,b,c,d in self.volume.regions)

    def clear_bounds(self, low, high, *, visible=False):
        return self.clear_box(self.footprint(low,high),visible=visible)
