"""Shared-world sand ledges for upper desktop rows, with open swim routes."""
from .art import mesh, sand_texture, plant_leaf
from .framing import at_depth, regions


def stacked_indices(rectangles):
    """Only an upper view with water below it gets shelves (not a side offset)."""
    return [i for i,(x,y,w,h) in enumerate(rectangles) if any(
        j!=i and yy>=y+h*.75 and min(x+w,xx+ww)-max(x,xx)>min(w,ww)*.2
        for j,(xx,yy,ww,hh) in enumerate(rectangles))]


def shelf_boxes(rectangles,lens,camera,render):
    boxes=[]
    for i in stacked_indices(rectangles):
        a,b,c,d=regions(rectangles)[i]
        v=c+(d-c)/3
        left=at_depth(lens,camera,render,a,v,5.)
        right=at_depth(lens,camera,render,b,v,5.)
        low,high=max(-21.,left.x),min(21.,right.x)
        surface=max(2.8,min(12.5,(left.z+right.z)/2))
        # Two shorter ledges, a body-sized central opening, and a completely
        # open foreground route at Y<2.5. No full-width ceiling between rows.
        middle=(low+high)/2;gap=max(4.8,(high-low)*.38)
        for l,r in ((low,middle-gap/2),(middle+gap/2,high)):
            if r-l<1.:continue
            boxes.append(((round((l+r)/2,3),6.,round(surface-.4,3)),
                          (round(r-l,3),6.,.8),(0,0,0)))
    # Identical overlapping outputs should not duplicate geometry or solids.
    return tuple(dict.fromkeys(boxes))


def ledge(parent,position,size,texture):
    x,y,z=position;w,d,h=size
    bottom=[(x-w*.40,y-d*.40,z-h*.5),(x+w*.40,y-d*.40,z-h*.5),
            (x+w*.40,y+d*.40,z-h*.5),(x-w*.40,y+d*.40,z-h*.5)]
    top=[(x-w/2,y-d/2,z+h/2),(x+w/2,y-d/2,z+h/2),
         (x+w/2,y+d/2,z+h/2),(x-w/2,y+d/2,z+h/2)]
    vertices=[];triangles=[]
    for i in range(4):
        j=(i+1)%4;n=((0,-1,0),(1,0,0),(0,1,0),(-1,0,0))[i]
        base=len(vertices)
        vertices.extend((p,n,(.24,.30,.27,1),(0,0)) for p in (bottom[i],bottom[j],top[j],top[i]))
        triangles.extend(((base,base+1,base+2),(base,base+2,base+3)))
    mesh("shelf-rock",vertices,triangles).reparentTo(parent)
    cap=mesh("shelf-sand",[(p,(0,0,1),(1,1,1,1),uv) for p,uv in zip(top,((0,0),(w/9,0),(w/9,d/9),(0,d/9)))],
             [(0,1,2),(0,2,3)])
    cap.reparentTo(parent);cap.setTexture(texture)
    for offset in (-.3,.3):
        leaf=plant_leaf(.8, .18, offset, (.13,.35,.25),5)
        leaf.reparentTo(parent);leaf.setPos(x+offset*w/2,y+1,z+h/2)


class SandShelves:
    def __init__(self,app):
        self.app=app;self.root=app.scene.attachNewNode("sand-shelves")
        self.texture=sand_texture();self.boxes=()

    def layout(self,rectangles,lens,camera,render):
        boxes=shelf_boxes(rectangles,lens,camera,render) if rectangles else ()
        if boxes==self.boxes:return
        self.boxes=boxes
        self.root.getChildren().detach()
        for pos,size,hpr in boxes:ledge(self.root,pos,size,self.texture)
        # Keep sand caps individually addressable for appearance tint updates.
        self.app.sim.physics.replace_boxes("sand-shelves",boxes)
        self.app.sim.obstacles_changed()
