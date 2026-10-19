"""Seeded roaming across visible water with Bullet solid-body collisions."""
from dataclasses import dataclass
import hashlib
import math
import random
from .collision import CollisionWorld, body_dimensions
from .habitat import FISH_SCALES, TANK_LIMITS
from .swim_volume import SwimVolume


@dataclass
class Pose:
    x: float
    y: float
    z: float
    heading: float
    pitch: float
    bank: float
    phase: float
    speed: float


def clamp(value, low, high):
    return max(low, min(high, value))


class Swimmer:
    def __init__(self, owner, stage):
        self.rng = random.Random(int.from_bytes(hashlib.sha256(owner.encode()).digest(), 'big'))
        rng = self.rng
        self.stage = stage
        self.x = self.y = 0.; self.z = 7.
        self.heading = rng.uniform(-math.pi, math.pi)
        self.cruise = rng.uniform(.6, 1.35)
        self.speed = self.cruise
        self.turn_rate = rng.uniform(.5, .85)
        self.vz = self.bank = 0.
        self.phase = rng.uniform(0, math.tau)
        self.tail_rate = rng.uniform(4.5, 6.5)
        self.goal = (0., 0., 7.)
        self.remaining = 0.
        self.pace = self.cruise
        self.goal_cell = None
        self.obstacle_wait = rng.uniform(0, .2)
        self.obstacle_ahead = False
        self.radius = 1.1*FISH_SCALES[stage]


class Simulation:
    def __init__(self, reefs=True):
        self.time = 0.
        self.fish = []
        self.poses = {}
        self.swimmers = {}
        self.volume = SwimVolume()
        self.physics = CollisionWorld(reefs)
        self.occupancy = {}
        self.reservations = {}
        self._view_config = None

    def set_view(self, origin, right, forward, up, tan_x, tan_y, regions):
        config = (tuple(origin), tuple(right), tuple(forward), tuple(up), tan_x, tan_y, tuple(regions))
        if config == self._view_config:
            return
        self._view_config = config
        self.volume.configure(*config)
        # Replan soon after a real frustum change, without resetting positions.
        for s in self.swimmers.values():
            s.remaining = min(s.remaining, 2.)
            s.goal_cell = None
        self.reservations.clear()

    def _choose_goal(self, s):
        if s.goal_cell is not None:
            self.reservations[s.goal_cell] = max(0, self.reservations.get(s.goal_cell, 1)-1)
        # Prefer underused screen sectors, including edges/top/bottom. Nearby
        # low-density destinations win ties, avoiding endless centre crossings.
        candidates = []
        for x in range(6):
            for z in range(4):
                cell = (x, z)
                point = self.volume.candidate(s.rng, s.radius, cell)
                if point is None or not self.physics.clear_at(s.stage, point, s.heading, static_only=True):
                    continue
                distance = math.dist((s.x, s.y, s.z), point)
                if distance < 2.5:
                    continue
                score = self.occupancy.get(cell, 0) + self.reservations.get(cell, 0)*.8
                score += s.rng.uniform(0, 2) + distance*.08
                candidates.append((score, point, cell))
        if candidates:
            _, s.goal, s.goal_cell = min(candidates, key=lambda item: item[0])
        else:
            s.goal_cell = self.volume.cell(s.goal)
        self.reservations[s.goal_cell] = self.reservations.get(s.goal_cell, 0)+1
        # Finish a journey before choosing another; short global re-roll timers
        # disproportionately pulled the old fish back into the middle.
        s.pace = s.cruise*s.rng.uniform(.8, 1.15)
        s.remaining = max(15., math.dist((s.x, s.y, s.z), s.goal)/s.pace*2 + 8.)

    def roster(self, fish):
        self.fish = list(fish)
        by_owner = {f.owner: f for f in self.fish}
        for key in list(self.swimmers):
            if key not in by_owner:
                s = self.swimmers.pop(key)
                if s.goal_cell is not None:
                    self.reservations[s.goal_cell] = max(0, self.reservations.get(s.goal_cell, 1)-1)
                self.physics.remove(key)
        for key in sorted(by_owner):
            stage = by_owner[key].stage
            if key not in self.swimmers:
                s = Swimmer(key, stage)
                # Never cull an identity to make space. Try non-overlapping
                # arrivals first; Bullet separates pathological overcapacity.
                for _ in range(240):
                    point = self.volume.candidate(s.rng, s.radius)
                    if point is not None and self.physics.clear_at(stage, point, s.heading):
                        s.x, s.y, s.z = point
                        break
                self.swimmers[key] = s
                self.physics.add(key, stage, (s.x, s.y, s.z), s.heading)
                self._choose_goal(s)
            elif self.swimmers[key].stage != stage:
                s = self.swimmers[key]
                s.stage, s.radius = stage, 1.1*FISH_SCALES[stage]
                self.physics.add(key, stage, (s.x, s.y, s.z), s.heading)
        self.swimmers = dict(sorted(self.swimmers.items()))

    def step(self, dt):
        dt = clamp(dt, 0., .1)
        steps = max(1, math.ceil(dt/(1/60)))
        for _ in range(steps):
            self._advance(dt/steps)
        self.time += dt
        self.poses = {key: Pose(s.x, s.y, s.z, math.degrees(s.heading),
                               -math.degrees(math.atan2(s.vz, max(s.speed, .01))),
                               s.bank, s.phase, s.speed) for key, s in self.swimmers.items()}
        return self.poses

    def _advance(self, dt):
        buckets = {}
        self.occupancy = {}
        for key, s in self.swimmers.items():
            cell = (int(s.x//4), int(s.y//4), int(s.z//4))
            buckets.setdefault(cell, []).append((key, s.x, s.y, s.z, s.radius))
            sector = self.volume.cell((s.x, s.y, s.z))
            self.occupancy[sector] = self.occupancy.get(sector, 0)+1
        velocities = {}
        for key, s in self.swimmers.items():
            s.remaining -= dt
            distance = math.dist((s.x, s.y, s.z), s.goal)
            if s.remaining <= 0 or distance < 1.3:
                self._choose_goal(s)
            gx, gy, gz = s.goal
            dx, dy = gx-s.x, gy-s.y
            distance_xy = max(.01, math.hypot(dx, dy))
            dx, dy = dx/distance_xy, dy/distance_xy
            sx = sy = sz = 0.
            caution = 0.
            forward_x, forward_y = math.cos(s.heading), math.sin(s.heading)
            cell = (int(s.x//4), int(s.y//4), int(s.z//4))
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    for oz in (-1, 0, 1):
                        for other, x, y, z, radius in buckets.get((cell[0]+ox, cell[1]+oy, cell[2]+oz), ()):
                            if other == key:
                                continue
                            ax, ay, az = s.x-x, s.y-y, s.z-z
                            d2 = ax*ax+ay*ay+az*az
                            safe = s.radius+radius+.7
                            if .0001 < d2 < safe*safe:
                                d = math.sqrt(d2); threat = (safe-d)/safe
                                sx += ax/d*threat*2.5; sy += ay/d*threat*2.5; sz += az/d*threat
                                if -(ax*forward_x+ay*forward_y)/d > .3:
                                    # Consistent starboard pass breaks head-on
                                    # symmetry; collision response is not a bounce.
                                    sx += forward_y*threat*2
                                    sy -= forward_x*threat*2
                                    caution = max(caution, threat)
            # Preview solid scenery along the current course, not just neighbours.
            s.obstacle_wait -= dt
            if s.obstacle_wait <= 0:
                look = (s.x+forward_x*(s.speed*1.4+.4), s.y+forward_y*(s.speed*1.4+.4), s.z+s.vz)
                s.obstacle_ahead = not self.physics.clear_at(s.stage, look, s.heading, static_only=True)
                s.obstacle_wait = .2
            if s.obstacle_ahead:
                sx += forward_y*1.2; sy -= forward_x*1.2
                sz += .7
                caution = max(caution, .65)
            # Gentle wall approach. Bullet enforces the actual body clearance.
            wall = []
            for value, (low, high) in zip((s.x, s.y, s.z), TANK_LIMITS):
                wall.append(max(0., low+s.radius+2-value)-max(0., value-(high-s.radius-2)))
            dx += clamp(sx, -2., 2.) + wall[0]
            dy += clamp(sy, -2., 2.) + wall[1]
            desired = math.atan2(dy, dx)
            error = (desired-s.heading+math.pi)%math.tau-math.pi
            turn = clamp(error*1.4, -s.turn_rate, s.turn_rate)
            s.heading = (s.heading+turn*dt+math.pi)%math.tau-math.pi
            # Desynchronised short glides without discarding the destination.
            glide = .5 if math.sin(self.time*.19+s.phase*.025) > .92 else 1.
            target_speed = s.pace*glide*(1-.4*min(1., abs(error)/1.5))*(1-.7*caution)
            s.speed += (target_speed-s.speed)*(1-math.exp(-dt*2))
            target_vz = clamp((gz-s.z)*.5 + clamp(sz, -1., 1.)*.7 + wall[2], -.65, .65)
            s.vz += (target_vz-s.vz)*(1-math.exp(-dt*2))
            s.bank += (-turn*15-s.bank)*(1-math.exp(-dt*2.5))
            s.phase += dt*s.tail_rate*(.55+s.speed*.65)
            velocities[key] = (math.cos(s.heading)*s.speed, math.sin(s.heading)*s.speed, s.vz)
        self.physics.advance(self.swimmers, velocities, dt)
