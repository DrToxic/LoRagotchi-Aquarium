"""Native before/after palettes, moving joints, mirrors and adult pixel parity.

Run with tools.run_native tools.juvenile_smoke --baseline-art /path/to/art.py
The baseline must be a saved pre-change art.py from the accepted source.
"""
import argparse
from dataclasses import replace
import importlib.util
import json
import math
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-art',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=Path('.local/juvenile'))
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    from panda3d.core import loadPrcFileData, OrthographicLens, AmbientLight, DirectionalLight, PNMImage, TextNode
    loadPrcFileData('', 'window-type onscreen\nwin-size 1600 1000\naudio-library-name null\nsync-video false\nshow-frame-rate-meter false')
    from direct.showbase.ShowBase import ShowBase
    from tank.art import fish_model
    from tank.demo import visitors
    from tank.themes import STYLES
    spec=importlib.util.spec_from_file_location('tank._juvenile_baseline',args.baseline_art)
    baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
    app=ShowBase();app.disableMouse();app.setBackgroundColor(.035,.09,.12,1)
    lens=OrthographicLens();lens.setFilmSize(25.6,16);app.cam.node().setLens(lens)
    app.camera.setPos(0,-35,0);app.camera.lookAt(0,0,0)
    ambient=AmbientLight('ambient');ambient.setColor((.72,.72,.72,1));app.render.setLight(app.render.attachNewNode(ambient))
    sun=DirectionalLight('sun');sun.setColor((.5,.5,.5,1));light=app.render.attachNewNode(sun);light.setHpr(-25,-45,0);app.render.setLight(light)
    seed=next(visitors(1))
    palettes=[('Red / teal',0,4,2,65535),('Orange / violet',1,5,4,65535),('Gold / red',2,0,5,65535),
              ('Mint / gold',3,2,0,65535),('Teal / orange',4,1,3,65535),('Violet / mint',5,3,2,65535),
              ('Mono white',6,6,6,65535),('Mono black',6,6,6,0)]
    def label(parent,text,x,z,size=.19):
        node=TextNode('label');node.setText(text);node.setAlign(TextNode.ACenter);node.setTextColor(.85,.93,.96,1)
        item=parent.attachNewNode(node);item.setPos(x,-1,z);item.setScale(size);item.setLightOff()
    def capture(path=None):
        for _ in range(3):app.graphicsEngine.renderFrame()
        image=PNMImage();assert app.win.getScreenshot(image)
        if path:assert image.write(str(path))
        return image
    def bytes_of(image):
        # Compare the actual RGB framebuffer, including all pixels, not a thumbnail.
        return bytes(v for y in range(image.getYSize()) for x in range(image.getXSize())
                     for v in (image.getRedVal(x,y),image.getGreenVal(x,y),image.getBlueVal(x,y)))
    def plate(factory,style,heading,phase):
        group=app.render.attachNewNode('plate');models=[]
        for stage in range(4):
            for column,(name,body,scales,eyes,tint) in enumerate(palettes):
                fish=replace(seed,stage=stage,body=body,scales=scales,eyes=eyes,tint=tint,mode='M' if body==6 else 'C')
                root,tail,fins=factory(fish,18,style);root.reparentTo(group)
                root.setScale(.82);root.setPos(-11.2+column*3.2,0,5.5-stage*3.5)
                root.setHpr(heading,math.sin(phase)*7,math.cos(phase)*4)
                tail.setH(math.sin(phase)*22)
                for i,fin in enumerate(fins):fin.setH(math.sin(phase*.65+i)*12)
                models.append((root,tail,fins))
        return group,models
    cases=[];adult_equal=0;moving=0
    for style in STYLES:
        for heading in (0,180):
            previous=None
            for phase in (.2,1.4):
                old,old_models=plate(baseline.fish_model,style,heading,phase);before=capture();old.removeNode()
                new,models=plate(fish_model,style,heading,phase);after=capture()
                # Bottom half contains adults/elders only, same scene/light/pose.
                for y in range(500,1000):
                    for x in range(1600):
                        assert before.getXelVal(x,y)==after.getXelVal(x,y),(style,heading,phase,x,y)
                adult_equal+=1
                encoded=bytes_of(after)
                if previous is not None:assert previous!=encoded;moving+=1
                previous=encoded
                assert bytes_of(before)!=encoded
                # Tail/fins remain attached under turns and body banking.
                for root,tail,fins in models:
                    assert tail.getParent()==root and all(fin.getParent()==root for fin in fins)
                if phase==1.4:
                    after.write(str(args.output/f'moving-{style}-{heading}.png'))
                cases.append(dict(style=style,heading=heading,phase=phase));new.removeNode()
                print(f'PASS native {style} heading={heading} phase={phase}: changed juveniles, identical adults/elders',flush=True)
    # A native-rendered, labelled comparison sheet: no mockup or recolouring.
    group=app.render.attachNewNode('comparison')
    label(group,'AGE-BASED GENETIC COLOURS  |  native Panda3D  |  before / after',0,7.4,.28)
    for column,(name,body,scales,eyes,tint) in enumerate(palettes):
        x=-11.2+column*3.2;label(group,name,x,6.8,.20)
        for row,(stage,is_new) in enumerate([(0,False),(0,True),(1,False),(1,True),(2,False),(2,True)]):
            z=5.5-row*2.25
            fish=replace(seed,stage=stage,body=body,scales=scales,eyes=eyes,tint=tint,mode='M' if body==6 else 'C')
            root,tail,fins=(fish_model if is_new else baseline.fish_model)(fish,18)
            root.reparentTo(group);root.setScale(.76);root.setPos(x,0,z)
            tail.setH(15)
            label(group,('Fry','Young','Adult')[stage]+(' - after' if is_new else ' - before'),x,z-.8,.17)
    capture(args.output/'before-after.png');group.removeNode()
    (args.output/'native-report.json').write_text(json.dumps(dict(cases=cases,palettes=palettes,adult_unchanged_frames=adult_equal,moving_frame_pairs=moving,renderer=app.win.getGsg().getDriverRenderer(),baseline=str(args.baseline_art)),indent=2)+'\n')
    app.destroy()


if __name__=='__main__':main()
