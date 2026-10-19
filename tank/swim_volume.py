"""A view-aware water volume: goals use the visible water, not a central box."""
import math
from .habitat import TANK_LIMITS


class SwimVolume:
    def __init__(self):
        length = math.hypot(32, 6.5)
        self.configure((0., -32., 12.), (1., 0., 0.),
                       (0., 32/length, -6.5/length), (0., 6.5/length, 32/length),
                       math.tan(math.pi/6), math.tan(math.pi/6)/(16/9),
                       ((-1., 1., -1., 1.),))

    def configure(self, origin, right, forward, up, tan_x, tan_y, regions):
        self.origin, self.right, self.forward, self.up = map(tuple, (origin, right, forward, up))
        self.tan_x, self.tan_y = tan_x, tan_y
        self.regions = tuple(regions)

    def point(self, u, v, depth):
        return tuple(self.origin[i] + depth*(self.forward[i] + self.right[i]*u*self.tan_x
                                            + self.up[i]*v*self.tan_y) for i in range(3))

    def project(self, point):
        delta = tuple(point[i]-self.origin[i] for i in range(3))
        depth = max(.1, sum(delta[i]*self.forward[i] for i in range(3)))
        return (sum(delta[i]*self.right[i] for i in range(3))/(depth*self.tan_x),
                sum(delta[i]*self.up[i] for i in range(3))/(depth*self.tan_y))

    def cell(self, point):
        u, v = self.project(point)
        return (max(0, min(5, int((u+1)*3))), max(0, min(3, int((v+1)*2))))

    def candidate(self, rng, margin, cell=None):
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
                return point
        return None
