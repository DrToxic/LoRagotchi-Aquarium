"""Folder-based, static Panda models and matching solid-only collision proxies."""
from dataclasses import dataclass
import json
import math
from pathlib import Path

from panda3d.core import Filename, NodePath

LIBRARY = Path(__file__).parent / "assets" / "decorations"


def vector(value, label, positive=False):
    if not isinstance(value,list) or len(value)!=3:
        raise ValueError(f"{label} must have three numbers")
    if any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v)
           or abs(v)>1000 or (positive and v<=0) for v in value):
        raise ValueError(f"Invalid {label}")
    return tuple(value)


@dataclass(frozen=True)
class Decoration:
    key: str
    name: str
    description: str
    model: Path
    position: tuple
    hpr: tuple
    scale: float
    enabled: bool
    solids: tuple


def discover(directory=LIBRARY):
    """Bad optional assets produce a visible library error, not an app crash."""
    items, errors = [], []
    for manifest in sorted(Path(directory).glob("*/decoration.json")):
        try:
            raw=json.loads(manifest.read_text(encoding="utf-8"))
            name=raw["name"]
            if not isinstance(name,str) or not name.strip() or len(name)>60:raise ValueError("Invalid name")
            description=raw.get("description","")
            if not isinstance(description,str) or len(description)>300:raise ValueError("Invalid description")
            model=(manifest.parent/raw["model"]).resolve()
            if not model.is_relative_to(manifest.parent.resolve()) or model.suffix.lower() not in (".egg",".bam") or not model.is_file():
                raise ValueError("Model must be an .egg or .bam inside this decoration folder")
            scale=raw.get("scale",1.)
            if isinstance(scale,bool) or not isinstance(scale,(int,float)) or not math.isfinite(scale) or not .01<=scale<=20:
                raise ValueError("Scale must be 0.01..20")
            enabled=raw.get("enabled",False)
            if not isinstance(enabled,bool):raise ValueError("enabled must be true or false")
            solids=raw.get("solids",[])
            if not isinstance(solids,list) or len(solids)>256:raise ValueError("At most 256 solid boxes per object")
            solids=tuple((vector(s["center"],"solid centre"),vector(s["size"],"solid size",True),
                          vector(s.get("hpr",[0,0,0]),"solid rotation")) for s in solids)
            items.append(Decoration(manifest.parent.name,name,description,model,
                vector(raw.get("position",[0,0,0]),"position"),vector(raw.get("hpr",[0,0,0]),"rotation"),
                scale,enabled,solids))
        except (OSError,ValueError,TypeError,KeyError,AttributeError) as exc:
            errors.append(f"{manifest.parent.name}: {exc}")
    return items,errors


class DecorationLibrary:
    def __init__(self,app,directory=LIBRARY):
        self.app,self.directory=app,Path(directory)
        self.root=app.scene.attachNewNode("decoration-library")
        self.items={};self.nodes={};self.errors=[]
        self.refresh()

    def enabled(self,item):
        return self.app.settings.decorations.get(item.key,item.enabled)

    def refresh(self):
        for key,node in self.nodes.items():
            node.removeNode()
            self.app.sim.physics.replace_boxes("decoration:"+key,[])
        self.nodes={}
        items,self.errors=discover(self.directory)
        self.items={item.key:item for item in items}
        for item in items:
            try:
                node=self.app.loader.loadModel(Filename.fromOsSpecific(str(item.model)),noCache=True)
                if node is None or node.isEmpty():raise ValueError("Model did not load")
                node.reparentTo(self.root);node.setPos(*item.position);node.setHpr(*item.hpr);node.setScale(item.scale)
                self.nodes[item.key]=node
                self._apply(item)
            except (OSError,ValueError,TypeError) as exc:
                self.errors.append(f"{item.key}: {exc}")
        self.app.sim.obstacles_changed()

    def _apply(self,item):
        node=self.nodes.get(item.key)
        if node is None:return
        enabled=self.enabled(item)
        node.show() if enabled else node.hide()
        boxes=[]
        if enabled:
            for position,size,hpr in item.solids:
                transform=node.attachNewNode("solid-transform")
                transform.setPos(*position);transform.setHpr(*hpr)
                boxes.append((tuple(transform.getPos(self.app.render)),
                              tuple(v*item.scale for v in size),
                              tuple(transform.getHpr(self.app.render))))
                transform.removeNode()
        self.app.sim.physics.replace_boxes("decoration:"+item.key,boxes)

    def set_enabled(self,key,enabled):
        if key not in self.nodes:return
        self.app.settings.decorations[key]=bool(enabled)
        self._apply(self.items[key])
        self.app.sim.obstacles_changed()
        self.app.settings.save(self.app.args.settings)
