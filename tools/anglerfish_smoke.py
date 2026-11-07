"""Native Anglerfish plates, prior-species pixel parity and frozen lure cost.

Run: python -m tools.run_native tools.anglerfish_smoke --baseline-art ... --output ...
This is software GL/Xvfb evidence, not a Pi performance or radio hardware claim.
"""
import argparse
from dataclasses import replace
import importlib.util
import json
import math
from pathlib import Path
import statistics
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-art',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData, OrthographicLens, AmbientLight, DirectionalLight, TextNode
    loadPrcFileData('', 'window-type onscreen\nwin-size 1600 1000\naudio-library-name null\nsync-video false\nshow-frame-rate-meter false')
    from direct.showbase.ShowBase import ShowBase
    from tank.art import fish_model
    from tank.anglerfish import animate
    from tank.demo import visitors
    spec=importlib.util.spec_from_file_location('tank._angler_baseline',args.baseline_art)
    baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
    app=ShowBase();app.disableMouse();app.setBackgroundColor(.025,.07,.10,1)
    lens=OrthographicLens();lens.setFilmSize(25.6,16);app.cam.node().setLens(lens)
    app.camera.setPos(0,-35,0);app.camera.lookAt(0,0,0)
    ambient=AmbientLight('ambient');ambient.setColor((.72,.72,.72,1));app.render.setLight(app.render.attachNewNode(ambient))
    sun=DirectionalLight('sun');sun.setColor((.5,.5,.5,1));light=app.render.attachNewNode(sun);light.setHpr(-25,-45,0);app.render.setLight(light)
    seed=next(visitors(1))
    palettes=[('Coral / lagoon',0,4,2,65535,False),('Mint / gold',3,2,0,65535,False),
              ('Violet / mint',5,3,2,65535,False),('Mono white',6,6,6,65535,False),
              ('Mono black',6,6,6,0,False),('H1 red / cyan',0,4,6,65535,True)]
    def label(parent,text,x,z,size=.23):
        node=TextNode('label');node.setText(text);node.setAlign(TextNode.ACenter);node.setTextColor(.85,.93,.96,1)
        item=parent.attachNewNode(node);item.setPos(x,-1,z);item.setScale(size);item.setLightOff()
    def capture(name=None):
        for _ in range(3):app.graphicsEngine.renderFrame()
        app.graphicsEngine.syncFrame()
        texture=app.win.getScreenshot();assert texture
        if name:assert texture.write(str(args.output/(name+'.png')))
        return bytes(texture.getRamImage())
    def plate(factory,style,heading,phase,species=14,flag=True):
        group=app.render.attachNewNode('plate');models=[]
        for stage in range(4):
            for column,(name,body,scales,eyes,tint,h1) in enumerate(palettes):
                fish=replace(seed,stage=stage,body=body,scales=scales,eyes=eyes,tint=tint,
                             species_id=species,species_present=flag,genes_present=h1,
                             body_gene=8 if h1 else None,scales_gene=128 if h1 else None,eyes_gene=6 if h1 else None)
                root,tail,fins=factory(fish,18,style);root.reparentTo(group)
                root.setScale(root.getScale()*.95);root.setPos(-10+column*4,0,5-stage*3.5)
                root.setHpr(heading,math.sin(phase)*7,math.cos(phase)*4)
                tail.setH(math.sin(phase)*22)
                for i,fin in enumerate(fins):fin.setH(math.sin(phase*.65+i)*12)
                animate(root,phase);models.append(root)
        return group,models
    parity=[];moving=[]
    for style in ('classic','rounded','faceted'):
        for heading in (0,180):
            # Every old registered Water identity (0..13), unknown, and absent
            # species shares unchanged art here; compare the actual framebuffer.
            for species in (*range(14),65535):
                old,_=plate(baseline.fish_model,style,heading,.8,species)
                before=capture();old.removeNode()
                new,_=plate(fish_model,style,heading,.8,species)
                after=capture();new.removeNode();assert before==after,(style,heading,species)
                parity.append(dict(style=style,heading=heading,species=species))
            old,_=plate(baseline.fish_model,style,heading,.8,14,False)
            before=capture();old.removeNode()
            new,_=plate(fish_model,style,heading,.8,14,False)
            after=capture();new.removeNode();assert before==after
            previous=None
            for phase in (.2,1.4):
                group,models=plate(fish_model,style,heading,phase)
                label(group,'ANGLERFISH  |  explicit Water ID 14  |  '+style,0,7.5,.31)
                for column,palette in enumerate(palettes):label(group,palette[0],-10+column*4,6.8,.24)
                for stage,text in enumerate(('Fry 0','Young 1','Adult 2','Elder 3')):label(group,text,-11.6,5-stage*3.5,.24)
                pixels=capture(f'angler-{style}-{heading}-{phase}')
                if previous is not None:assert pixels!=previous;moving.append((style,heading))
                previous=pixels;group.removeNode()
            print(f'PASS {style} / {heading}: prior species framebuffer identical, Anglerfish moves',flush=True)
    # Freeze geometry/poses; alternate emission animation off/on under identical
    # render settings, with no frame limit. Cost is host-observed, not Pi data.
    group,models=plate(fish_model,'classic',0,.8)
    timings=[]
    for enabled in (False,True,False,True):
        update=[];frame=[]
        for i in range(80):
            start=time.perf_counter()
            if enabled:
                for model in models:animate(model,i/30)
            if i>=20:update.append((time.perf_counter()-start)*1000)
            app.graphicsEngine.renderFrame();app.graphicsEngine.syncFrame()
            if i>=20:frame.append((time.perf_counter()-start)*1000)
        timings.append(dict(enabled=enabled,population=len(models),update_median_ms=statistics.median(update),
                            update_p95_ms=sorted(update)[56],frame_median_ms=statistics.median(frame),frame_p95_ms=sorted(frame)[56]))
    # Parent scale (same as AppearanceScene) must dim even the unlit bulb.
    app.setBackgroundColor(0,0,0,1)
    group.setColorScale(0,0,0,1);black=capture('angler-blackout')
    group.hide();hidden=capture();assert black==hidden
    report=dict(renderer=app.win.getGsg().getDriverRenderer(),prior_species_pixel_equal=parity,
                absent_species_pixel_equal_frames=6,moving_pairs=moving,blackout_including_lure=True,
                timings=timings,baseline=str(args.baseline_art))
    (args.output/'native-report.json').write_text(json.dumps(report,indent=2)+'\n')
    group.removeNode();app.destroy()


if __name__=='__main__':main()
