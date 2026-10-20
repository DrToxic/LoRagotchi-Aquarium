"""Author the bundled original low-poly models. Runtime loads the saved EGGs.

Run with python -m tools.build_decorations after editing this source.
No downloaded models, textures, scripts or third-party art.
"""
import json
import math
from pathlib import Path

from panda3d.core import Vec3, Quat
from tank.decorations import LIBRARY


class Model:
    def __init__(self):
        self.vertices=[];self.faces=[];self.solids=[]

    def face(self,points,color):
        normal=(Vec3(*points[1])-Vec3(*points[0])).cross(Vec3(*points[2])-Vec3(*points[0]))
        normal.normalize()
        ids=[]
        for p in points:
            ids.append(len(self.vertices));self.vertices.append((p,tuple(normal)))
        self.faces.append((ids,color))

    def box(self,center,size,color,hpr=(0,0,0),solid=True):
        quat=Quat();quat.setHpr(hpr)
        points=[tuple(Vec3(*center)+quat.xform(Vec3(x*size[0]/2,y*size[1]/2,z*size[2]/2)))
                for x,y,z in ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                              (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))]
        for indexes in ((0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)):
            self.face([points[i] for i in indexes],color)
        if solid:self.solids.append(dict(center=center,size=size,hpr=hpr))

    def beam(self,a,b,width,color,solid=False):
        midpoint=tuple((x+y)/2 for x,y in zip(a,b));delta=Vec3(*b)-Vec3(*a)
        length=delta.length()
        # Box's long axis is local Z. Pitch/roll orient it toward the endpoint.
        h=math.degrees(math.atan2(delta.y,delta.x))
        r=math.degrees(math.acos(delta.z/length))
        self.box(midpoint,(width,width,length),color,(h,0,r),solid)

    def ring(self,center,radius,thickness,color,segments=16,plane="xz"):
        for i in range(segments):
            angles=(math.tau*i/segments,math.tau*(i+1)/segments)
            points=[]
            for a in angles:
                offset=(radius*math.cos(a),0,radius*math.sin(a)) if plane=="xz" else (radius*math.cos(a),radius*math.sin(a),0)
                points.append(tuple(v+o for v,o in zip(center,offset)))
            self.beam(*points,thickness,color)

    def save(self,key,name,description,position,enabled=False,hpr=(0,0,0)):
        folder=LIBRARY/key;folder.mkdir(parents=True,exist_ok=True)
        lines=["<CoordinateSystem> { Z-up }","<VertexPool> vertices {"]
        for i,(point,normal) in enumerate(self.vertices):
            lines.append(f"  <Vertex> {i} {{ {' '.join(f'{v:.6f}' for v in point)} <Normal> {{ {' '.join(f'{v:.6f}' for v in normal)} }} }}")
        lines.append("}")
        for ids,color in self.faces:
            lines.append("<Polygon> { <RGBA> { "+" ".join(str(v) for v in (*color,1))+
                         " } <VertexRef> { "+" ".join(map(str,ids))+" <Ref> { vertices } } }")
        (folder/"model.egg").write_text("\n".join(lines)+"\n",encoding="utf-8")
        (folder/"decoration.json").write_text(json.dumps(dict(name=name,description=description,model="model.egg",
            position=position,hpr=hpr,scale=1.,enabled=enabled,solids=self.solids),indent=2)+"\n",encoding="utf-8")


def build():
    wood=(.36,.20,.10);light=(.49,.31,.16);dark=(.18,.12,.075);iron=(.15,.22,.23);gold=(.80,.59,.16)
    ship=Model()
    # Deliberately broken hull: low planks and end decks frame a large open
    # midsection. No invisible full-boat convex collider over this passage.
    for y in (-1.7,1.7):
        for z in (.35,.68,1.01):
            ship.box((0,y,z),(9.6,.20,.26),wood)
        ship.box((0,y,4.4),(9.8,.18,.18),light)
        for x in (-4.5,4.5):
            ship.box((x,y,2.5),(.28,.24,3.6),wood)
    ship.box((0,0,.26),(9.6,3.5,.3),dark)
    for x in (-4.55,4.55):
        ship.box((x,0,1.15),(1.25,3.6,.22),light)
        for y in (-1.4,0,1.4):
            ship.box((x,y,1.65),(.95,1.1,.65),wood)
    # Angled bow/stern, plank seams, a broken mast, crossbones pirate pennant.
    for x in (-5.4,5.4):
        ship.box((x,0,.65),(.9,2.8,.8),wood,hpr=(0,0,12 if x<0 else -12))
    # Tapered plank ends and upswept prow give the broken frame a boat outline.
    for side in (-1,1):
        for z in (.35,.68,1.01):
            ship.beam((4.8,side*1.7,z),(6.1,0,z+.7),.24,light,True)
            ship.beam((-4.8,side*1.7,z),(-5.65,side*.6,z+.55),.24,wood,True)
    ship.beam((5.7,0,1.1),(6.7,0,2.8),.25,wood,True)
    ship.box((-4.5,0,3.2),(1.5,3.3,.25),light)
    for y in (-1.5,1.5):
        ship.box((-4.5,y,2.65),(1.25,.18,.9),wood)
        ship.box((-4.52,y*1.08,2.7),(.40,.03,.35),(.04,.10,.12),solid=False)
    for x in (-3.5,-2.2,-.9,.4,1.7,3):
        ship.box((x,-1.82,.5),(.06,.04,.55),dark,solid=False)
    ship.box((.2,1.65,3.9),(.24,.24,7.4),wood)
    ship.box((.2,1.65,6.25),(3.8,.16,.16),light)
    ship.face([(.32,1.65,7.5),(2.6,1.65,7.25),(2.1,1.65,6.7),(.32,1.65,6.8)],(.07,.095,.105))
    ship.beam((.8,1.6,7.25),(1.75,1.6,6.9),.10,(.83,.82,.68))
    ship.beam((.8,1.6,6.9),(1.75,1.6,7.25),.10,(.83,.82,.68))
    ship.ring((1.25,1.59,7.23),.19,.14,(.83,.82,.68),10)
    for x in (-4.55,4.55):
        ship.ring((x,-1.82,1.65),.24,.07,iron,12)
    ship.save("pirate-ship","Pirate ship wreck","Broken hull, open middle and end decks; fish can cross through the hull.",(-2,2,.05),True,hpr=(-6,0,0))

    arch=Model();stone=(.35,.41,.37)
    arch.box((-2.4,0,2.1),(1.1,1.5,4.2),stone)
    arch.box((2.4,0,2.1),(1.1,1.5,4.2),stone)
    for x in (-1.6,0,1.6):arch.box((x,0,4.2),(1.7,1.6,.85),(.43,.46,.38),hpr=(0,0,8*x))
    for x in (-2.4,2.4):
        arch.box((x,0,.25),(1.5,1.85,.5),(.29,.36,.31))
        arch.box((x,0,3.6),(1.25,1.65,.25),(.48,.47,.36))
    arch.save("stone-arch","Ancient stone arch","A broad swim-through opening under a weathered lintel.",(6,5,.05))

    chest=Model()
    chest.box((0,0,.65),(2.2,1.5,1.3),wood)
    chest.box((0,.45,1.7),(2.2,1.55,.28),light,hpr=(0,-38,0))
    for x in (-.8,.8):
        chest.box((x,0,.65),(.16,1.55,1.35),gold)
        chest.box((x,.45,1.7),(.16,1.6,.32),gold,hpr=(0,-38,0))
    chest.box((0,-.79,.8),(.28,.1,.42),gold,solid=False)
    for x in (-.5,0,.45):
        for y in (-.3,.1):chest.box((x,y,1.34),(.37,.28,.08),gold,hpr=(x*30,0,0),solid=False)
    chest.save("treasure-chest","Treasure chest","An open wooden chest with brass bands and a few coins.",(4,-3,.05),True,hpr=(12,0,0))

    anchor=Model()
    anchor.box((0,0,1.9),(.23,.3,3.2),iron)
    anchor.box((0,0,2.8),(2.1,.28,.23),iron)
    anchor.ring((0,0,3.8),.42,.18,iron)
    for s in (-1,1):
        anchor.beam((0,0,.5),(s*1.35,0,1.1),.3,iron,True)
        anchor.beam((s*1.35,0,1.1),(s*1.55,0,1.7),.25,iron,True)
    anchor.save("anchor","Old anchor","A simple iron anchor half settled into the sand.",(8,-3,.1),hpr=(10,0,24))

    pots=Model()
    for x,zsize in ((-.7,1.7),(.8,1.1)):
        for i in range(12):
            angle=i*math.tau/12
            pots.box((x+.52*math.cos(angle),.52*math.sin(angle),zsize/2),(.3,.15,zsize),
                     (.52,.28,.16),hpr=(math.degrees(angle)+90,0,0))
        pots.ring((x,0,zsize),.56,.15,(.63,.38,.22),12,plane="xy")
    pots.save("clay-pots","Clay pots","Two low-poly terracotta jars, open at the rim.",(-8,-3,.05))


if __name__=="__main__":build()
