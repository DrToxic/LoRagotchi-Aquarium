"""Headless trajectory/coverage probe. Simulated time is not a GPU FPS result."""
import argparse
import json
import time
from pathlib import Path
from tank.demo import visitors
from tank.simulation import Simulation


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fish',type=int,default=256)
    parser.add_argument('--seconds',type=int,default=120)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.seconds<2:parser.error('--seconds must be at least 2')
    sim=Simulation();sim.roster(visitors(args.fish));samples=[];max_depth=0.;start=time.perf_counter()
    for step in range(args.seconds*10):
        poses=sim.step(.1)
        if step>=args.seconds*5 and step%10==0:
            samples.extend((p.x,p.y,p.z) for p in poses.values())
        if hasattr(sim,'physics') and step%10==0:
            max_depth=max(max_depth,max((-d for a,b,d in sim.physics.penetrations(.001)),default=0))
    count=max(1,len(samples))
    report={'fish':len(sim.poses),'simulated_seconds':args.seconds,'sampled_fish_positions':len(samples),
            'outer_x_fraction':sum(abs(x)>10 for x,y,z in samples)/count,
            'upper_z_fraction':sum(z>9 for x,y,z in samples)/count,
            'post_solver_max_sampled_proxy_penetration':max_depth if hasattr(sim,'physics') else None,
            'wall_seconds_not_render_fps':time.perf_counter()-start}
    text=json.dumps(report,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text+'\n')
    print(text)


if __name__=='__main__':main()
