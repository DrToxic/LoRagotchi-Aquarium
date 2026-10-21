"""Compare the batched default reef against the original scenery construction."""
from pathlib import Path
import tempfile


def exercise(app):
    from panda3d.core import PNMImage
    from tank.art import scenery
    app.taskMgr.remove('aquarium-update')
    for model,_,_ in app.models.values():model.hide()
    app.decorations.root.hide();app.shelves.root.hide();app.columns.root.hide()
    root=app.scene.attachNewNode('legacy-reference')
    plants,caustic=scenery(root,app.settings)
    for node,_ in plants:node.hide()
    for node in root.findAllMatches('**/rippling-sand'):node.hide()
    if caustic:caustic.hide()
    root.hide()
    app.placement.batch.reparentTo(app.scene);app.decor.hide()
    def frame():
        for _ in range(3):app.graphicsEngine.renderFrame()
        im=PNMImage();assert app.aquarium_window.getScreenshot(im);return im
    current=frame()
    app.placement.batch.hide();root.show();original=frame()
    changed=sum(current.getXel(x,y)!=original.getXel(x,y) for x in range(current.getXSize()) for y in range(current.getYSize()))
    assert changed==0,changed
    print('PASS default static reef batching: zero changed pixels against original construction',flush=True)


def main():
    import sys
    from tank.aquarium import Aquarium
    from tank.__main__ import main as run
    from tank.settings import Settings
    Aquarium.run=exercise
    with tempfile.TemporaryDirectory(prefix='layout-baseline-') as directory:
        path=Path(directory)/'settings.json';settings=Settings();settings.apply('low');settings.vsync=False;settings.save(path)
        sys.argv=['baseline','--demo','0','--width','960','--height','540','--settings',str(path)];run()


if __name__=='__main__':main()
