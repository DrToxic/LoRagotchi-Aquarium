"""Deterministic world-space paths, smooth turns, banking and local separation.

A single simulation feeds every viewport. No fish positions cross LoRa.
"""
from dataclasses import dataclass
import hashlib
import math

@dataclass
class Pose:
    x:float;y:float;z:float;heading:float;pitch:float;bank:float;phase:float;speed:float

class Simulation:
    def __init__(self):self.time=0.;self.fish=[];self.poses={}
    def roster(self,fish):self.fish=list(fish)
    def step(self,dt):
        self.time+=min(max(dt,0),.1)
        poses={}
        for fish in self.fish:
            seed=int(hashlib.sha256(fish.owner.encode()).hexdigest()[:8],16)
            a=(seed%10000)/10000*math.tau
            t=self.time*(.045+(seed%7)*.004)+a
            # A looping, depth-changing cruise has bounded speed/curvature, no
            # snap direction changes. Shorter secondary oscillations add variation.
            rx=8+(seed%80)/10;ry=2.0+(seed%20)/10
            x=rx*math.sin(t);y=ry*math.cos(t)
            z=2.5+(seed%55)/10+math.sin(t*1.7+a)*.7
            def smooth(v):
                v=min(1.,max(0.,v));return v*v*(3-2*v)
            # Static reef avoidance: softly raise cruising paths over the two
            # scenery banks, keeping the foreground and centre lanes open.
            reef=smooth((abs(x)-7)/3)*smooth((y+1)/3)
            z+=reef*max(0.,4.8-z)
            dx=rx*math.cos(t);dy=-ry*math.sin(t);dz=1.19*math.cos(t*1.7+a)
            heading=math.degrees(math.atan2(dy,dx))
            pitch=-math.degrees(math.atan2(dz,math.hypot(dx,dy)))
            phase=self.time*(5+(seed%5)*.35)+a
            poses[fish.owner]=Pose(x,y,z,heading,pitch,math.sin(t)*8,phase,.5+abs(dx)*.05)
        # Gentle presentation-space separation; all identities remain in the scene.
        # Spatial hash avoids O(n²) as event rosters grow.
        buckets={}
        for key,p in poses.items():
            cell=(int(p.x//2),int(p.y//2),int(p.z//2))
            for ox in (-1,0,1):
                for oy in (-1,0,1):
                    for oz in (-1,0,1):
                        for q in buckets.get((cell[0]+ox,cell[1]+oy,cell[2]+oz),[]):
                            d=math.sqrt((p.x-q.x)**2+(p.y-q.y)**2+(p.z-q.z)**2)
                            if d<1.2:p.z+=(1.2-d)*.35
            buckets.setdefault(cell,[]).append(p)
        self.poses=poses
        return poses
