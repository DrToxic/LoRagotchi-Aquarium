"""Repeatable label-overhead probe on a frozen 256-fish scene.

Run from an active desktop: uv run python tools/benchmark_labels.py
Timings describe only the machine/renderer that ran them, never another GPU/Pi.
"""
import json
import math
import statistics
import time
from types import SimpleNamespace
from panda3d.core import ClockObject
from tank.aquarium import Aquarium
from tank.simulation import Pose


def benchmark(self):
    deadline=time.monotonic()+20
    while len(self.roster)!=self.args.demo and time.monotonic()<deadline:self.taskMgr.step()
    assert len(self.roster)==self.args.demo
    self.taskMgr.remove('aquarium-update')
    clock=ClockObject.getGlobalClock();clock.setMode(ClockObject.MNonRealTime);clock.setDt(1/60)
    # Same geometry/poses for old/new implementations and every label mode.
    poses={fish.owner:Pose((i%16-7.5)*1.7,(i//16%4-1.5)*1.4,2+(i//16)*.45,
                          (i%5-2)*12,0,0,i*.3,.8) for i,fish in enumerate(self.roster)}
    self.sim.step=lambda dt:poses
    results=[]
    for shown in (False,True,False,True):
        self.show_names=shown
        for _ in range(8):
            self.update(SimpleNamespace(cont='cont'));self.graphicsEngine.renderFrame()
        samples=[];updates=[]
        for _ in range(60):
            start=time.perf_counter()
            self.update(SimpleNamespace(cont='cont'))
            updates.append((time.perf_counter()-start)*1000)
            self.graphicsEngine.renderFrame()
            samples.append((time.perf_counter()-start)*1000)
        results.append({'names':shown,'update_median_ms':round(statistics.median(updates),3),
                        'frame_median_ms':round(statistics.median(samples),3),
                        'frame_p95_ms':round(sorted(samples)[56],3)})
    print(json.dumps({'renderer':self.win.getGsg().getDriverRenderer(),
                      'fish':len(self.roster),'samples_per_pass':60,'passes':results},indent=2))


Aquarium.run=benchmark
from tank.__main__ import main
if __name__=='__main__':main()
