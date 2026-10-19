"""Independent, seeded cruise/glide steering in one shared world.

Waypoints, pace and dwell time belong to each identity, not to a global orbit.
Avoidance changes velocity, never teleports fish. No positions cross LoRa.
"""
from dataclasses import dataclass
import hashlib
import math
import random


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


class Swimmer:
    def __init__(self, owner):
        self.rng = random.Random(int.from_bytes(hashlib.sha256(owner.encode()).digest(), "big"))
        rng = self.rng
        self.x, self.y, self.z = rng.uniform(-14, 14), rng.uniform(-3, 3), rng.uniform(3.6, 8.8)
        self.heading = rng.uniform(-math.pi, math.pi)
        self.cruise = rng.uniform(.55, 1.35)
        self.speed = self.cruise
        self.turn_rate = rng.uniform(.45, .85)
        self.vz = self.bank = 0.
        self.phase = rng.uniform(0, math.tau)
        self.tail_rate = rng.uniform(4.5, 6.5)
        self.choose_goal()

    def choose_goal(self):
        rng = self.rng
        self.goal = (rng.uniform(-14, 14), rng.uniform(-3.2, 3.2), rng.uniform(2.4, 9.1))
        self.remaining = rng.uniform(5, 17)
        # Short lazy glides mixed into longer traverses; fish never stop dead.
        self.pace = self.cruise * (rng.uniform(.3, .55) if rng.random() < .23 else rng.uniform(.8, 1.2))


def clamp(value, low, high):
    return max(low, min(high, value))


class Simulation:
    def __init__(self):
        self.time = 0.
        self.fish = []
        self.poses = {}
        self.swimmers = {}

    def roster(self, fish):
        self.fish = list(fish)
        # Stable order and per-owner random streams: arrivals/renames don't reset
        # existing swimmers or make trajectories depend on database row order.
        owners = sorted({f.owner for f in self.fish})
        self.swimmers = {key: self.swimmers[key] if key in self.swimmers else Swimmer(key) for key in owners}

    def step(self, dt):
        dt = clamp(dt, 0., .1)
        steps = max(1, math.ceil(dt / (1 / 30)))
        for _ in range(steps):
            self._advance(dt / steps)
        self.time += dt
        self.poses = {
            key: Pose(s.x, s.y, s.z, math.degrees(s.heading),
                      -math.degrees(math.atan2(s.vz, s.speed)), s.bank, s.phase, s.speed)
            for key, s in self.swimmers.items()
        }
        return self.poses

    def _advance(self, dt):
        # Snapshot positions first so separation is symmetric and O(n + neighbours).
        buckets = {}
        for key, s in self.swimmers.items():
            cell = (int(s.x // 2), int(s.y // 2), int(s.z // 2))
            buckets.setdefault(cell, []).append((key, s.x, s.y, s.z))
        for key, s in self.swimmers.items():
            s.remaining -= dt
            gx, gy, gz = s.goal
            if s.remaining <= 0 or math.dist((s.x, s.y, s.z), s.goal) < 1.5:
                s.choose_goal()
                gx, gy, gz = s.goal
            dx, dy = gx - s.x, gy - s.y
            distance = max(.01, math.hypot(dx, dy))
            dx, dy = dx / distance, dy / distance
            sx = sy = sz = 0.
            cell = (int(s.x // 2), int(s.y // 2), int(s.z // 2))
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    for oz in (-1, 0, 1):
                        for other, x, y, z in buckets.get((cell[0]+ox, cell[1]+oy, cell[2]+oz), ()):
                            if other == key:
                                continue
                            ax, ay, az = s.x-x, s.y-y, s.z-z
                            d2 = ax*ax + ay*ay + az*az
                            if .0001 < d2 < 1.44:
                                d = math.sqrt(d2)
                                force = (1.2-d) / d
                                sx += ax*force
                                sy += ay*force
                                sz += az*force
            # Soft containment starts before the edge, leaving room to turn.
            wall_x = -math.copysign(max(0., abs(s.x)-12.) * .9, s.x)
            wall_y = -math.copysign(max(0., abs(s.y)-2.) * 1.8, s.y)
            dx += wall_x + clamp(sx, -1., 1.) * .65
            dy += wall_y + clamp(sy, -1., 1.) * .65
            desired = math.atan2(dy, dx)
            error = (desired - s.heading + math.pi) % math.tau - math.pi
            turn = clamp(error * 1.4, -s.turn_rate, s.turn_rate)
            s.heading = (s.heading + turn*dt + math.pi) % math.tau - math.pi
            target_speed = s.pace * (1 - .4*min(1., abs(error)/1.5))
            s.speed += (target_speed-s.speed) * (1-math.exp(-dt*1.2))
            s.x = clamp(s.x+math.cos(s.heading)*s.speed*dt, -16., 16.)
            s.y = clamp(s.y+math.sin(s.heading)*s.speed*dt, -4., 4.)
            reef = clamp((abs(s.x)-6)/4, 0., 1.) * clamp((s.y+2)/3, 0., 1.)
            floor = 1.8 + reef*3.1
            target_vz = clamp((max(gz, floor+.4)-s.z)*.45 + clamp(sz, -1., 1.)*.25, -.4, .4)
            if s.z < floor:
                target_vz = max(target_vz, .4)
            s.vz += (target_vz-s.vz) * (1-math.exp(-dt*2))
            s.z = clamp(s.z+s.vz*dt, 1.5, 10.)
            s.bank += (-turn*15-s.bank) * (1-math.exp(-dt*2.5))
            s.phase += dt*s.tail_rate*(.55 + s.speed*.65)
