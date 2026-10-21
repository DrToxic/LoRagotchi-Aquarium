"""Ephemeral, bounded channel chat; independent of fish identity and storage."""
from collections import OrderedDict, deque
from dataclasses import dataclass
import math
import re

from panda3d.core import TextNode, TransparencyAttrib

from .art import mesh
from .framing import at_depth
from .text import display_text

CHANNEL = "#loragotchi-DX"
MAX_PENDING = 24
MAX_ACTIVE = 4
MAX_AGE = 120.
SPACING = 5.


@dataclass(frozen=True)
class ChatMessage:
    sender: str
    text: str
    received: float


class ChatQueue:
    """Accept only plain messages from a resolved channel, with bounded dedup."""
    def __init__(self):
        self.pending = deque(maxlen=MAX_PENDING)
        self.seen = OrderedDict()
        self.enabled = True

    def accept(self, event, now):
        index = event.get("channel_index")
        if (event.get("kind") != "mesh" or type(index) is not int
                or event.get("route") != f"channel {index}"
                or event.get("channel_name", "").casefold() != CHANNEL.casefold()
                or event.get("text_type") != 0):
            return False
        raw = event.get("text", "")
        if not isinstance(raw, str):
            return False
        # Formatting controls never reach Panda. Keep valid Unicode/emoji.
        text = "".join(c if c.isprintable() else " " for c in raw[:160]).lstrip()
        sender, separator, body = text.partition(": ")
        if not separator or len(sender) > 48 or not sender:
            sender, body = "", text
        # LFG1 is the fish-transfer protocol, not channel conversation.
        if not body.strip() or re.match(r"^LFG1(?:[|:\s]|$)", body.strip(), re.I):
            return False
        key = (event.get("rx"), index, event.get("timestamp"), raw)
        if key in self.seen:
            return False
        self.seen[key] = None
        if len(self.seen) > 512:
            self.seen.popitem(last=False)
        if not self.enabled:
            return False
        self.pending.append(ChatMessage(sender, body.strip(), now))
        return True

    def pop(self, now):
        while self.pending and now-self.pending[0].received > MAX_AGE:
            self.pending.popleft()
        return self.pending.popleft() if self.pending else None

    def clear(self):
        self.pending.clear()


def rounded_card(name, width, height, radius, colour):
    """Small static rounded mesh in the text's X/Z plane, facing the camera."""
    points = []
    for x, z, start in ((width/2-radius, height/2-radius, 0),
                        (-width/2+radius, height/2-radius, 90),
                        (-width/2+radius, -height/2+radius, 180),
                        (width/2-radius, -height/2+radius, 270)):
        for i in range(9):
            a = math.radians(start+i*90/8)
            points.append((x+radius*math.cos(a), 0, z+radius*math.sin(a)))
    vertices = [((0, 0, 0), (0, -1, 0), colour, (.5, .5))]
    vertices += [(p, (0, -1, 0), colour, (.5, .5)) for p in points]
    triangles = [(0, i+1, (i+1) % len(points)+1) for i in range(len(points))]
    return mesh(name, vertices, triangles)


class ChatBubbles:
    """One shared world-space layer: sand occludes it and all windows crop it."""
    DEPTH = -3.
    TEXT_SCALE = .40

    def __init__(self, parent, camera, render, enabled=True):
        self.root = parent.attachNewNode("channel-chat")
        self.root.setLightOff()
        self.root.setColorScaleOff(1)
        self.root.setFogOff()
        self.root.setTransparency(TransparencyAttrib.MAlpha)
        self.root.setDepthWrite(False)
        # Depth testing remains on: the actual sand/reef hides submerged text.
        self.root.setTwoSided(True)
        self.camera, self.render = camera, render
        self.queue = ChatQueue()
        self.queue.enabled = enabled
        self.active = []
        self.time = self.next_spawn = 0.
        self.serial = self.builds = 0
        self.lens = None

    def set_view(self, lens):
        self.lens = lens
        for bubble in self.active:
            bubble["top"] = self._exit_height(bubble["height"])
            bubble["node"].setQuat(self.camera.getQuat(self.render))

    def accept(self, event):
        return self.queue.accept(event, self.time)

    def set_enabled(self, enabled):
        self.queue.enabled = enabled
        if not enabled:
            self.clear()

    def clear(self):
        self.queue.clear()
        for bubble in self.active:
            bubble["node"].removeNode()
        self.active.clear()
        self.next_spawn = self.time

    def _at_depth(self, u, v):
        return at_depth(self.lens,self.camera,self.render,u,v,self.DEPTH)

    def _exit_height(self, height):
        # A full card-height margin also covers its camera-facing tilt/depth.
        return self._at_depth(0,1).z+height+.2

    def _spawn(self, message):
        left, right = self._at_depth(-.94, 0), self._at_depth(.94, 0)
        available = max(1., right.x-left.x)
        width = min(8., available*.85)
        scale = min(self.TEXT_SCALE, width/12)
        body = TextNode("chat-message")
        body.setText(display_text(message.text))
        body.setWordwrap((width-.7)/scale)
        body.setTextColor(.92, .98, .96, 1)
        body.setShadow(.035, .035)
        body.setShadowColor(.01, .06, .075, .7)
        rows = body.getNumRows()
        height = rows*scale+1.2
        node = self.root.attachNewNode(f"chat-{self.serial}")
        node.setQuat(self.camera.getQuat(self.render))
        radius = min(.6, height*.4, width*.2)
        rim = rounded_card("chat-rim", width+.055, height+.055, radius+.02, (.37,.71,.73,.8))
        rim.reparentTo(node)
        card = rounded_card("chat-glass", width, height, radius, (.025,.13,.17,.94))
        card.reparentTo(node);card.setY(-.012)
        label = node.attachNewNode(body.generate())
        label.setScale(scale);label.setPos(-width/2+.35, -.04, height/2-.87)
        header = TextNode("chat-sender")
        header.setText(display_text(message.sender or CHANNEL))
        header.setWordwrap((width-.7)/.28)
        header.setMaxRows(1)
        header.setTextColor(.45,.84,.8,1)
        title = node.attachNewNode(header.generate())
        title.setScale(.28);title.setPos(-width/2+.35, -.045, height/2-.4)
        # Translucent circular highlights make the rounded card read as a
        # rising air pocket, not a scrolling notification panel.
        for i, (x, z, size) in enumerate(((-width/2+.19, height/2-.19, .08),
                                        (width/2-.32, -height/2+.24, .045))):
            glint = rounded_card("chat-glint", size*2, size*2, size, (.7,.94,.93,.7))
            glint.reparentTo(node);glint.setPos(x,-.025,z)
        # Rotate lanes; reserve padding for drift so cards fit the water view.
        lane = (self.serial % 3)/2
        x = (left.x+width/2+.2)*(1-lane)+(right.x-width/2-.2)*lane
        bottom = -height-.65
        top = self._exit_height(height)
        duration = max(24., min(34., 22.+len(message.text)*.055))
        node.setPos(x, self.DEPTH, bottom)
        self.active.append(dict(node=node, x=x, bottom=bottom, top=top,
                                height=height, speed=(top-bottom)/duration,
                                age=0., duration=duration, phase=self.serial*2.4))
        self.serial += 1
        self.builds += 1

    def update(self, dt):
        self.time += max(0., dt)
        for bubble in self.active[:]:
            bubble["age"] += max(0., dt)
            z = bubble["node"].getZ()+bubble["speed"]*max(0.,dt)
            if z >= bubble["top"]:
                bubble["node"].removeNode()
                self.active.remove(bubble)
                continue
            # Constant upward travel; subtle independent sway, no text rebuild.
            bubble["node"].setPos(bubble["x"]+.15*math.sin(bubble["age"]*.65+bubble["phase"]),
                                  self.DEPTH, z)
        if self.lens and self.queue.enabled and len(self.active) < MAX_ACTIVE and self.time >= self.next_spawn:
            message = self.queue.pop(self.time)
            if message:
                self._spawn(message)
                self.next_spawn = self.time+SPACING

    def destroy(self):
        self.clear()
        self.root.removeNode()
