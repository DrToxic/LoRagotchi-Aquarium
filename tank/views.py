"""Native windows, desktop-aligned frusta and immutable name geometry.

Panda3D owns OS windows, render targets and text shaping. Scene cameras share the
same simulation; actual desktop rectangles (including negative origins and Y
offsets) define crops, masks and placement. The operator window is not a crop.
"""
import math
from panda3d.core import CardMaker, NodePath, PerspectiveLens, Point2, TextNode, TransparencyAttrib
from .text import display_text


def desktop_lenses(rectangles):
    """Map top-left-origin desktop client rectangles into one continuous frustum."""
    left = min(x for x, y, w, h in rectangles)
    top = min(y for x, y, w, h in rectangles)
    right = max(x+w for x, y, w, h in rectangles)
    bottom = max(y+h for x, y, w, h in rectangles)
    width, height = right-left, bottom-top
    base = PerspectiveLens()
    base.setAspectRatio(width/height)
    # Portrait layouts crop the sides of the familiar 16:9 water volume,
    # rather than exposing a huge empty sky above the bounded aquarium.
    base.setFov(math.degrees(2*math.atan(math.tan(math.pi/6)*min(1., width/height/(16/9)))))
    base.setNearFar(.1, 120)
    film = base.getFilmSize()
    focal = base.getFocalLength()
    lenses = []
    for x, y, w, h in rectangles:
        lens = base.makeCopy()
        lens.setFilmSize(film.x*w/width, film.y*h/height)
        lens.setFocalLength(focal)
        lens.setFilmOffset(film.x*((x-left+w/2)/width-.5),
                           film.y*(.5-(y-top+h/2)/height))
        lenses.append(lens)
    return lenses


class NameLabels:
    """Build text only on roster/name changes; animate NodePath transforms only."""
    def __init__(self, parent):
        self.root = parent.attachNewNode('fish-names')
        self.root.setLightOff()
        self.root.setDepthTest(False)
        self.root.setDepthWrite(False)
        self.root.setTransparency(TransparencyAttrib.MAlpha)
        self.root.hide()
        self.shown = False
        self.labels = {}
        self.geometry = {}
        self.builds = 0
        self.point = Point2()

    def sync(self, roster):
        names = {fish.owner: fish.name for fish in roster}
        for key in list(self.labels):
            if key not in names or self.labels[key][1] != names[key]:
                self.labels.pop(key)[0].removeNode()
        for key, name in names.items():
            if key in self.labels:
                continue
            if name not in self.geometry:
                text = TextNode('fish-name')
                text.setText(display_text(name))
                text.setAlign(TextNode.ACenter)
                text.setTextColor(.83, .93, .88, .9)
                self.geometry[name] = text.generate()
                self.builds += 1
            # Distinct transform per owner, even when names match. Attaching the
            # same PandaNode twice to one parent would collapse those labels.
            node = self.root.attachNewNode('name-'+key[:12])
            node.attachNewNode(self.geometry[name])
            node.setScale(.027)
            self.labels[key] = (node, name)
        active_names = set(names.values())
        self.geometry = {name: node for name, node in self.geometry.items() if name in active_names}

    def update(self, shown, lens, camera, render, models, aspect):
        if shown != self.shown:
            self.root.show() if shown else self.root.hide()
            self.shown = shown
        if not shown:
            return
        for key, (label, name) in self.labels.items():
            model = models[key][0]
            visible = lens.project(camera.getRelativePoint(render, model.getPos(render)), self.point)
            visible = visible and not model.isHidden() and abs(self.point.x) < 1.1 and abs(self.point.y) < 1.1
            if visible:
                label.setPos(self.point.x*aspect, 0, self.point.y+.07)
                if label.isHidden():
                    label.show()
            elif not label.isHidden():
                label.hide()

    def destroy(self):
        self.root.removeNode()
        self.labels.clear()
        self.geometry.clear()


class AquariumView:
    def __init__(self, app, window, primary=False):
        self.app = app
        self.window = window
        self.primary = primary
        self.view_id = 0
        self.input = None
        self.blackout = None
        self.buffer = self.camera = self.screen = self.overlay_camera = None
        self.internal_size = None
        self.output_size = None
        self.lens = PerspectiveLens()
        # The ShowBase primary window belongs exclusively to the operator.
        # Every aquarium, including the first, owns its own clean overlay.
        self.root = NodePath('aquarium-overlay')
        self.root.setDepthTest(False)
        self.root.setDepthWrite(False)
        self.overlay_camera = app.makeCamera2d(window)
        self.overlay_camera.node().setScene(self.root)
        self.aspect_root = self.root.attachNewNode('window-aspect')
        self.names = NameLabels(self.aspect_root)

    def resize(self, scale):
        width, height = self.window.getXSize(), self.window.getYSize()
        if width <= 0 or height <= 0:
            return
        self.aspect = width/height
        self.aspect_root.setScale(1/self.aspect, 1, 1)
        internal = (max(160, int(width*scale)), max(90, int(height*scale)))
        self.output_size = (width, height)
        if internal == self.internal_size:
            return
        if self.buffer and hasattr(self.buffer, 'setSize'):
            self.buffer.setSize(*internal)
            self.internal_size = internal
            return
        # Focus and move events must not tear down render targets.
        buffer = self.window.makeTextureBuffer('aquarium-internal', *internal)
        if not buffer:
            raise RuntimeError('Could not allocate aquarium render target; lower render scale/output size')
        self._remove_target()
        self.buffer = buffer
        self.internal_size = internal
        buffer.setSort(-100)
        buffer.setClearColor((.012, .075, .115, 1))
        self.camera = self.app.makeCamera(buffer, lens=self.lens)
        self.camera.node().setScene(self.app.render)
        maker = CardMaker('aquarium-composite')
        maker.setFrameFullscreenQuad()
        self.screen = self.root.attachNewNode(maker.generate())
        self.screen.setTexture(buffer.getTexture())
        self.screen.setBin('background', 0)
        self.screen.setDepthWrite(False)
        self.screen.setDepthTest(False)

    def set_lens(self, lens):
        self.lens = lens
        if self.camera:
            self.camera.node().setLens(lens)

    def set_blackout(self,geometry,rectangle):
        from .projection import attach_blackout
        if self.blackout:self.blackout.removeNode()
        self.blackout=attach_blackout(self.root,geometry,rectangle)

    def rectangle(self):
        props = self.window.getProperties()
        return (props.getXOrigin(), props.getYOrigin(), self.window.getXSize(), self.window.getYSize())

    def _remove_target(self):
        if self.screen:
            self.screen.removeNode()
        if self.camera:
            if self.camera in self.app.camList:
                self.app.camList.remove(self.camera)
            self.camera.removeNode()
        if self.buffer:
            self.buffer.setActive(False)
            self.buffer.removeAllDisplayRegions()
            self.app.graphicsEngine.removeWindow(self.buffer)
        self.screen = self.camera = self.buffer = None

    def destroy(self):
        if self.blackout:self.blackout.removeNode()
        self.blackout=None
        self._remove_target()
        self.names.destroy()
        self.aspect_root.removeNode()
        if self.overlay_camera:
            self.overlay_camera.node().setActive(False)
            self.overlay_camera.removeNode()
        self.root.removeNode()
