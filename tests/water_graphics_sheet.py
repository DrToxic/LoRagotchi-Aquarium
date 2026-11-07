"""Native offscreen Water catalogue: run under Xvfb with output path argument."""
import sys
from panda3d.core import loadPrcFileData,OrthographicLens,TextNode,AmbientLight,DirectionalLight
loadPrcFileData('', 'window-type offscreen\nwin-size 1400 750\naudio-library-name null\nframebuffer-multisample 0')
from direct.showbase.ShowBase import ShowBase
from types import SimpleNamespace
from tank.art import fish_model
from tank.water_art import NAMES,animate_water
app=ShowBase(windowType='offscreen');app.setBackgroundColor(.025,.12,.17,1)
lens=OrthographicLens();lens.setFilmSize(17,9.1);lens.setNearFar(1,100);app.cam.node().setLens(lens)
app.camera.setPos(0,-30,0);app.camera.lookAt(0,0,0)
a=AmbientLight('ambient');a.setColor((.75,.75,.75,1));app.render.setLight(app.render.attachNewNode(a))
d=DirectionalLight('sun');d.setColor((.7,.7,.7,1));n=app.render.attachNewNode(d);n.setHpr(-30,-40,0);app.render.setLight(n)
for i,name in enumerate(NAMES):
    x=-6.8+(i%7)*2.27; z=2.3-(i//7)*4.1
    s=SimpleNamespace(owner=str(i)*64,stage=2,body=i%6,scales=(i+2)%6,eyes=2,tint=65535,kind='snapshot',species_id=i)
    model,tail,fins=fish_model(s,12);model.reparentTo(app.render);model.setPos(x,0,z);model.setScale(.85)
    if i:animate_water(model,tail,fins,1.1,1.)
    t=TextNode('label');t.setText(str(i)+' '+name);t.setAlign(TextNode.ACenter);t.setTextColor(.85,.95,.95,1)
    node=app.render.attachNewNode(t);node.setScale(.22);node.setPos(x,-.2,z-1.35)
for _ in range(4):app.graphicsEngine.renderFrame()
app.win.saveScreenshot(sys.argv[1] if len(sys.argv)>1 else 'water-sheet.png')
app.destroy()
