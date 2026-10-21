"""Shared-world sand ledges for upper desktop rows, with open swim routes."""
from .art import mesh, sand_texture, plant_leaf
from .framing import at_depth, regions


def stacked_indices(rectangles):
    """Only an upper view with water below it gets shelves (not a side offset)."""
    return [i for i,(x,y,w,h) in enumerate(rectangles) if any(
        j!=i and yy>=y+h*.75 and min(x+w,xx+ww)-max(x,xx)>min(w,ww)*.2
        for j,(xx,yy,ww,hh) in enumerate(rectangles))]


def shelf_boxes(rectangles,lens,camera,render,*,keyed=False,view_ids=(),active=()):
    boxes=[]
    for i in stacked_indices(rectangles):
        if active and not active[i]:continue
        a,b,c,d=regions(rectangles)[i]
        v=c+(d-c)/3
        left=at_depth(lens,camera,render,a,v,5.)
        right=at_depth(lens,camera,render,b,v,5.)
        low,high=max(-21.,left.x),min(21.,right.x)
        surface=max(2.8,min(12.5,(left.z+right.z)/2))
        # Two shorter ledges, a body-sized central opening, and a completely
        # open foreground route at Y<2.5. No full-width ceiling between rows.
        middle=(low+high)/2;gap=max(4.8,(high-low)*.38)
        for side,(l,r) in enumerate(((low,middle-gap/2),(middle+gap/2,high))):
            if r-l<1.:continue
            box=((round((l+r)/2,3),6.,round(surface-.4,3)),(round(r-l,3),6.,.8),(0,0,0))
            boxes.append((f'shelf-stacked:{view_ids[i] if view_ids else i}:{side}',box) if keyed else box)
    # Identical overlapping outputs should not duplicate geometry or solids.
    return tuple(dict.fromkeys(boxes))


def edge_attached(zone,snapshot):
    """A zone actually intersects an exposed client edge, not a joined seam."""
    regions=snapshot.volume.regions
    zl,zr,zb,zt=zone.bounds()
    for a,b,c,d in regions:
        for side in range(4):
            low,high=(max(c,zb),min(d,zt)) if side<2 else (max(a,zl),min(b,zr))
            if high<=low:continue
            # Split at every other window edge, then test inside each segment.
            # This cannot miss a 1%-high zone or mistake a covered seam for air.
            cuts=sorted({low,high,*[v for r in regions for v in (r[2:] if side<2 else r[:2]) if low<v<high]})
            for start,end in zip(cuts,cuts[1:]):
                t=(start+end)/2;epsilon=1e-7
                x,y=((a,t),(b,t),(t,c),(t,d))[side]
                dx,dy=((-epsilon,0),(epsilon,0),(0,-epsilon),(0,epsilon))[side]
                if any(l<x+dx<r and bottom<y+dy<top for l,r,bottom,top in regions):continue
                if zone.intersects((x-dx,x-dx,y-dy,y-dy),snapshot.volume.aspect):return True
    return False


def shelf_envelope(box):
    pos,size,_=box
    return ((pos[0]-size[0]/2,pos[1]-size[1]/2,pos[2]-size[2]/2),
            (pos[0]+size[0]/2,pos[1]+size[1]/2,pos[2]+size[2]/2+.85))


def edge_shelf(zone,snapshot,lens,camera,render):
    if not zone.enabled:return None,'Zone disabled'
    if zone.inverted or zone.shape=='Ellipse':return None,'Needs a flat, non-inverted upper edge'
    if not edge_attached(zone,snapshot):return None,'Zone does not touch an exposed window edge'
    left,right,bottom,top=zone.bounds()
    if zone.shape=='Rounded rectangle':
        radius=min((right-left)*snapshot.volume.aspect/2,(top-bottom)/2)*.5
        left+=radius/snapshot.volume.aspect;right-=radius/snapshot.volume.aspect
    p=at_depth(lens,camera,render,left,top,6.)
    q=at_depth(lens,camera,render,right,top,6.)
    width=min(8.,q.x-p.x-.15)
    if width<1.4:return None,'Flat edge is too short'
    # Raise the whole rock, not just its sand cap, out of the mask. Only a
    # bounded near-edge search is permitted; a remote platform is not attached.
    for fraction in (.5,.3,.7):
        x=p.x+(q.x-p.x)*fraction
        for w in (width,width*.7,width*.45):
            if w<1.4:continue
            for rise in (.6,.9,1.2,1.5,1.8):
                box=((x,6.,(p.z+q.z)/2+rise),(w,2.5,.6),(0,0,0))
                low,high=shelf_envelope(box)
                if low[0]<-21 or high[0]>21 or high[2]>15.8:continue
                if snapshot.clear_bounds(low,high,visible=True):return box,'Placed'
    return None,'No clear water above the flat edge'


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
        self.surfaces=();self.keys=();self.status={}

    def layout(self,rectangles,lens,camera,render,*,snapshot=None,view_ids=(),active=()):
        from .bubble_columns import Surface
        candidates=list(shelf_boxes(rectangles,lens,camera,render,keyed=True,view_ids=view_ids,active=active)) if rectangles else []
        self.status={}
        if snapshot:
            if getattr(self.app.display,'protect_scenery',True):
                candidates=[(key,box) for key,box in candidates if snapshot.clear_bounds(*shelf_envelope(box))]
            for zone in snapshot.volume.zones:
                if not zone.edge_shelf:continue
                box,reason=edge_shelf(zone,snapshot,lens,camera,render)
                self.status[zone.uid]=reason
                if box:candidates.append(('shelf-edge:'+zone.uid,box))
        accepted=[]
        for key,box in candidates:
            if any(box==other for _,other in accepted):continue
            # New edge ledges must not intersect one another or existing ledges.
            if key.startswith('shelf-edge:'):
                low,high=shelf_envelope(box)
                if any(all(min(high[i],oh[i])>max(low[i],ol[i]) for i in range(3))
                       for _,other in accepted for ol,oh in [shelf_envelope(other)]):
                    self.status[key.removeprefix('shelf-edge:')]='Conflicts with another shelf';continue
            accepted.append((key,box))
        keys=tuple(key for key,_ in accepted);boxes=tuple(box for _,box in accepted)
        self.surfaces=tuple(Surface(key,pos[0],pos[1],pos[2]+size[2]/2,size[0],size[1])
                            for key,(pos,size,_) in accepted)
        if boxes==self.boxes and keys==self.keys:return
        self.boxes=boxes;self.keys=keys
        self.root.getChildren().detach()
        for pos,size,hpr in boxes:ledge(self.root,pos,size,self.texture)
        # Keep sand caps individually addressable for appearance tint updates.
        self.app.sim.physics.replace_boxes("sand-shelves",boxes)
        self.app.sim.obstacles_changed()
