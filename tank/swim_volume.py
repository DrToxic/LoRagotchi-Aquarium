"""A view-aware water volume: goals use the visible water, not a central box."""
import math
from .habitat import TANK_LIMITS
from .deadzones import covered


class SwimVolume:
    def __init__(self):
        length = math.hypot(32, 6.5)
        self.configure((0., -32., 12.), (1., 0., 0.),
                       (0., 32/length, -6.5/length), (0., 6.5/length, 32/length),
                       math.tan(math.pi/6), math.tan(math.pi/6)/(16/9),
                       ((-1., 1., -1., 1.),), constrain=False)

    def configure(self, origin, right, forward, up, tan_x, tan_y, regions, zones=(), constrain=True,
                  screen_regions=(), screen_aspect=None):
        self.origin, self.right, self.forward, self.up = map(tuple, (origin, right, forward, up))
        self.tan_x, self.tan_y = tan_x, tan_y
        self.regions = tuple(regions)
        self.zones, self.constrain = tuple(zones), constrain
        self.aspect = tan_x/tan_y
        self.screen_regions = tuple(screen_regions)
        self.screen_aspect = screen_aspect if screen_aspect is not None else self.aspect

    def point(self, u, v, depth):
        return tuple(self.origin[i] + depth*(self.forward[i] + self.right[i]*u*self.tan_x
                                            + self.up[i]*v*self.tan_y) for i in range(3))

    def project(self, point):
        delta = tuple(point[i]-self.origin[i] for i in range(3))
        depth = max(.1, sum(delta[i]*self.forward[i] for i in range(3)))
        return (sum(delta[i]*self.right[i] for i in range(3))/(depth*self.tan_x),
                sum(delta[i]*self.up[i] for i in range(3))/(depth*self.tan_y))

    def footprint(self, point, radius):
        delta=tuple(point[i]-self.origin[i] for i in range(3))
        depth=sum(delta[i]*self.forward[i] for i in range(3))
        if depth <= radius+.1:return (-1e6,1e6,-1e6,1e6)
        intervals=[]
        # Exact perspective bounds of a sphere enclosing body, fins and tail.
        for axis,tangent in ((self.right,self.tan_x),(self.up,self.tan_y)):
            value=sum(delta[i]*axis[i] for i in range(3))
            spread=radius*math.sqrt(depth*depth+value*value-radius*radius)
            divisor=(depth*depth-radius*radius)*tangent
            intervals.extend(((value*depth-spread)/divisor,(value*depth+spread)/divisor))
        return tuple(intervals)

    def allows_box(self, box):
        if self.constrain and not covered(box,self.regions):
            return False
        if not self.zones:
            return True
        if not self.screen_regions:
            return not any(zone.blocks(box,self.aspect) for zone in self.zones)
        # Optional compatibility mapping for callers with distinct water and
        # screen coordinates. The current app uses one physical panorama.
        # Test each visible piece of the footprint against the exact same
        # desktop coordinates used by that window's projector overlay.
        visible = False
        for water, screen in self.screen_regions:
            x0,x1,y0,y1 = water
            clipped = (max(box[0],x0),min(box[1],x1),max(box[2],y0),min(box[3],y1))
            if clipped[0] > clipped[1] or clipped[2] > clipped[3]:
                continue
            visible = True
            a,b,c,d = screen
            mapped = (a+(clipped[0]-x0)*(b-a)/(x1-x0),
                      a+(clipped[1]-x0)*(b-a)/(x1-x0),
                      c+(clipped[2]-y0)*(d-c)/(y1-y0),
                      c+(clipped[3]-y0)*(d-c)/(y1-y0))
            if any(zone.blocks(mapped,self.screen_aspect) for zone in self.zones):
                return False
        # Inverted keep-ins cannot be escaped by swimming entirely offscreen,
        # even when the separate window-edge protection switch is disabled.
        return visible or not any(zone.enabled and zone.inverted for zone in self.zones)

    def allows(self, point, radius):
        if not self.constrain and not self.zones:return True
        return self.allows_box(self.footprint(point,radius))

    def sweep_clear(self, start, end, radius):
        if not self.constrain and not self.zones:return True
        a,b=self.footprint(start,radius),self.footprint(end,radius)
        # Projection of a swept sphere is contained by the convex hull of its
        # endpoint projections. This box is conservative, including tiny gaps.
        return self.allows_box((min(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),max(a[3],b[3])))

    def path_clear(self, start, end, radius):
        if not self.constrain and not self.zones:return True
        steps=max(1,math.ceil(math.dist(start,end)/1.5))
        previous=start
        for i in range(1,steps+1):
            point=tuple(a+(b-a)*i/steps for a,b in zip(start,end))
            if not self.sweep_clear(previous,point,radius):return False
            previous=point
        return True

    def cell(self, point):
        u, v = self.project(point)
        return (max(0, min(5, int((u+1)*3))), max(0, min(3, int((v+1)*2))))

    def candidate(self, rng, margin, cell=None, outline=None):
        for _ in range(30):
            if cell is None:
                u, v = rng.uniform(-.9, .9), rng.uniform(-.86, .9)
            else:
                x, z = cell
                u = -.9+(x+rng.uniform(.08, .92))*.3
                v = -.86+(z+rng.uniform(.08, .92))*.44
            if not any(left <= u <= right and bottom <= v <= top for left, right, bottom, top in self.regions):
                continue
            point = self.point(u, v, rng.uniform(27.5, 39.))
            if all(low+margin <= value <= high-margin for value, (low, high) in zip(point, TANK_LIMITS)):
                if self.allows(point, outline if outline is not None else margin):
                    return point
        return None
