"""Tidal Garden: original default reef scenery.

All shapes and surface detail are authored here (MIT); no external artwork.
The public scenery interface matches art.scenery so the study can reuse the
native windows, placement, lighting and swimming stack without changing it.
"""
from functools import lru_cache
import math
import random

from panda3d.core import NodePath, PNMImage, Texture, TransparencyAttrib, Vec3
from .art import mesh, floor_mesh, sand_texture
from .bubble_columns import floor_height

# Deliberately asymmetric: a weathered left outcrop and a lower right garden.
# Centre +/-5 units stays open. Coarse silhouettes do not change with quality.
ROCKS = (
    ((-14.8, 4.8, 1.6), (5.4, 2.7, 2.0), 11),
    ((-15.4, 5.0, 4.0), (3.8, 2.0, 2.8), 17),
    ((-13.4, 5.2, 6.4), (2.8, 1.7, 1.9), 23),
    ((-10.7, 4.4, 2.1), (3.0, 2.2, 2.6), 31),
    ((-18.9, 3.5, 1.0), (3.4, 2.5, 1.5), 37),
    ((11.5, 4.9, 1.1), (4.5, 2.6, 1.5), 41),
    ((15.2, 5.5, 2.6), (4.3, 2.5, 2.7), 43),
    ((19.4, 5.3, 1.4), (3.2, 2.1, 1.8), 47),
    ((-17.7, -3.4, .55), (3.3, 1.8, .8), 53),
    ((16.8, -2.9, .5), (3.8, 1.9, .7), 59),
)


@lru_cache(maxsize=1)
def reef_texture():
    """One shared 128px RGB mineral/polyp microtexture; no transparency."""
    size=128; image=PNMImage(size,size,3); rng=random.Random(9503)
    for y in range(size):
        for x in range(size):
            u=x/size*math.tau; v=y/size*math.tau
            grain=rng.random()
            vein=math.sin(u*7+math.sin(v*5)*1.6)*math.sin(v*9+math.cos(u*4))
            pore=max(0,(.12-grain))*1.9
            shade=.84+.08*vein+.10*grain-pore
            image.setXel(x,y,shade,shade*.99,shade*.96)
    texture=Texture('tidal-garden-mineral');texture.load(image)
    texture.setWrapU(Texture.WMRepeat);texture.setWrapV(Texture.WMRepeat)
    texture.setMinfilter(Texture.FTLinearMipmapLinear);texture.setMagfilter(Texture.FTLinear)
    return texture


def solid_hull(node):
    """Use the authored mesh's points, not a stale unrelated scenery proxy."""
    from panda3d.bullet import BulletConvexHullShape
    from panda3d.core import GeomNode, GeomVertexReader
    shape=BulletConvexHullShape()
    parts=list(node.findAllMatches('**/+GeomNode'))
    if isinstance(node.node(),GeomNode):parts.insert(0,node)
    if not parts:raise ValueError('Solid artwork has no geometry')
    for part in parts:
        for geom in part.node().getGeoms():
            reader=GeomVertexReader(geom.getVertexData(),'vertex')
            while not reader.isAtEnd():shape.addPoint(node.getRelativePoint(part,reader.getData3()))
    return shape


def rock_model(scale, seed, detail, *, distant=False):
    """Coherent water-worn crags: shared seam/poles, layered mineral colours."""
    phase=seed*.73; radial=max(12,detail); rings=max(8,detail//2)
    vertices=[];triangles=[]
    for i in range(rings+1):
        p=math.pi*i/rings
        for j in range(radial+1):
            a=math.tau*j/radial
            n=Vec3(math.sin(p)*math.cos(a),math.sin(p)*math.sin(a),math.cos(p))
            # Continuous angular noise, fading at the poles: no split UV seam.
            r=1+math.sin(p)*(.11*math.sin(a*3+phase+p*2)+.08*math.cos(a*5-p*3+phase))
            xyz=(n.x*scale[0]*r+.12*scale[0]*math.sin(p*2+phase)*math.sin(p),
                 n.y*scale[1]*r,n.z*scale[2]*(1+.07*math.sin(a*4+phase)*math.sin(p)))
            normal=Vec3(n.x/scale[0],n.y/scale[1],n.z/scale[2]);normal.normalize()
            exposed=max(0,n.z)
            strata=.035*math.sin(xyz[2]*5+math.sin(xyz[0]*1.2))
            light=.58+.42*exposed+strata
            # Quiet olive/limestone with cooler shaded undersides.
            base=(.49,.50,.40) if not distant else (.17,.31,.32)
            col=tuple(c*light for c in base)+(1,)
            vertices.append((xyz,normal,col,(j/radial*3,i/rings*2)))
    for i in range(rings):
        for j in range(radial):
            a=i*(radial+1)+j;b=a+radial+1
            triangles.extend(((a,b,a+1),(a+1,b,b+1)))
    node=mesh('weathered-limestone',vertices,triangles)
    node.setTexture(reef_texture())
    return node


def plate_model(radius, colour, detail, seed):
    """Scalloped, shallow bowl/foliose coral with a shaded underside."""
    radial=max(20,detail*2); rings=max(4,detail//4);vertices=[];triangles=[]
    for lower in (False,True):
        start=len(vertices)
        for i in range(rings+1):
            t=i/rings
            for j in range(radial+1):
                a=math.tau*j/radial
                scallop=1+.08*math.sin(a*7+seed)+.045*math.sin(a*11-seed)
                r=radius*t*scallop
                z=.22*radius*t*t+.075*radius*math.sin(a*6+seed)*t*t
                if lower:z-=.10+.035*radius
                n=Vec3(-.3*t*math.cos(a),-.3*t*math.sin(a),-1 if lower else 1);n.normalize()
                ridge=.92+.08*math.cos(a*radial/2)
                brightness=(.45 if lower else .70+.30*t)*ridge
                vertices.append(((r*math.cos(a),r*math.sin(a)*.74,z),n,
                                 tuple(c*brightness for c in colour)+(1,),
                                 (.5+math.cos(a)*t,.5+math.sin(a)*t)))
        for i in range(rings):
            for j in range(radial):
                a=start+i*(radial+1)+j;b=a+radial+1
                triangles.extend(((a,b,a+1),(a+1,b,b+1)) if lower else ((a,a+1,b),(a+1,b+1,b)))
    stride=(rings+1)*(radial+1)
    for j in range(radial):
        a=rings*(radial+1)+j;b=a+stride
        triangles.extend(((a,b,a+1),(a+1,b,b+1)))
    node=mesh('scalloped-plate-coral',vertices,triangles);node.setTexture(reef_texture())
    return node


def tube_mesh(points, radii, colour, sides=7, name='coral-branch'):
    vertices=[];triangles=[]
    for i,point in enumerate(points):
        p=Vec3(*point)
        tangent=Vec3(*points[min(i+1,len(points)-1)])-Vec3(*points[max(i-1,0)])
        tangent.normalize();reference=Vec3(0,1,0) if abs(tangent.y)<.8 else Vec3(1,0,0)
        right=tangent.cross(reference);right.normalize();up=tangent.cross(right);up.normalize()
        for j in range(sides):
            a=math.tau*j/sides;n=right*math.cos(a)+up*math.sin(a)
            shade=.70+.30*max(0,n.z)
            vertices.append((p+n*radii[i],n,tuple(c*shade for c in colour)+(1,),(j/sides,i/(len(points)-1))))
    for i in range(len(points)-1):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides;c=a+sides;d=b+sides
            triangles.extend(((a,b,c),(b,d,c)))
    triangles.extend((0,j+1,j) for j in range(1,sides-1))
    top=(len(points)-1)*sides
    triangles.extend((top,top+j,top+j+1) for j in range(1,sides-1))
    return mesh(name,vertices,triangles)


def fan_model(height, colour, detail, seed):
    """A flattened sea fan with finite branching; flexible, not rigid scenery."""
    root=NodePath('sea-fan');rng=random.Random(seed)
    sides=5 if detail<16 else 7;levels=3 if detail<16 else 4
    def branch(start,direction,length,radius,depth):
        end=tuple(start[k]+direction[k]*length for k in range(3))
        middle=tuple((start[k]+end[k])*.5 for k in range(3))
        tube_mesh((start,middle,end),(radius,radius*.72,max(.012,radius*.42)),colour,sides).reparentTo(root)
        if depth and depth<=2:
            # Fine side branchlets suggest living polyps, not a bare winter tree.
            for sign in (-1,1):
                twig=(middle[0]+sign*length*.32,middle[1]-.015,middle[2]+length*.26)
                tube_mesh((middle,twig),(radius*.42,.012),tuple(min(1,c*1.12) for c in colour),5).reparentTo(root)
        if depth:
            for sign in (-1,1):
                angle=sign*rng.uniform(.30,.63)
                dx=direction[0]*math.cos(angle)+direction[2]*math.sin(angle)
                dz=-direction[0]*math.sin(angle)+direction[2]*math.cos(angle)
                branch(end,(dx,rng.uniform(-.12,.12),max(.15,dz)),length*.70,radius*.64,depth-1)
    branch((0,0,0),(0,0,1),height*.30,.105,levels)
    root.flattenStrong();return root


def sponge_model(height,radius,colour,detail,seed):
    """Closed wall + recessed open mouth: an actual tube, not a painted disk."""
    sides=max(12,detail);vertices=[];triangles=[]
    # The last two rings descend into the dark interior, ending in a small cap.
    rings=((0,.68,1),(.25,.84,1),(.7,1,1),(1,.91,1),(1,.65,.9),(.70,.54,.32),(.48,0,.13))
    for i,(z,r,shade) in enumerate(rings):
        for j in range(sides+1):
            a=math.tau*j/sides
            w=1+.045*math.sin(a*5+seed)
            x=math.cos(a)*radius*r*w+.13*height*z*z
            y=math.sin(a)*radius*r*w
            normal=Vec3(math.cos(a),math.sin(a),.12) if i<4 else Vec3(-math.cos(a),-math.sin(a),.2)
            normal.normalize()
            highlight=.82+.18*max(0,math.cos(a-1))
            col=tuple(c*shade*highlight for c in colour)+(1,)
            vertices.append(((x,y,height*z),normal,col,(j/sides*2,z*2)))
    for i in range(len(rings)-1):
        for j in range(sides):
            a=i*(sides+1)+j;b=a+sides+1
            triangles.extend(((a,a+1,b),(a+1,b+1,b)))
    node=mesh('open-tube-sponge',vertices,triangles);node.setTexture(reef_texture());return node


def seagrass_model(height, width, detail, seed):
    """Five folded, tapered blades: opaque vertex-shaded geometry, one sway node.

    The centre ridge catches light and the shaded roots sit naturally in sand.
    Curvature/twist and colour vary per blade; nothing is rebuilt during motion.
    """
    root=NodePath('reef-seagrass');rng=random.Random(seed)
    segments=max(5,min(10,detail//2))
    base=(rng.uniform(.18,.25),rng.uniform(.39,.49),rng.uniform(.25,.32))
    for blade in range(5):
        h=height*rng.uniform(.65,1.12);w=width*rng.uniform(.75,1.2)
        bend=rng.uniform(-.7,.7)*h*.3;curl=rng.uniform(-.5,.5)
        vertices=[];triangles=[]
        for i in range(segments+1):
            t=i/segments
            half=w*(.2+.8*math.sin(math.pi*t**.82))*(1-t**8)*.5+.002
            centre=bend*t*t
            shade=.46+.54*math.sin(t*math.pi*.65)
            for side in (-1,0,1):
                # A shallow V fold, with an asymmetric curl towards the tip.
                y=curl*t*t+abs(side)*half*.30
                normal=Vec3(side*.30,-1,2*curl*t/h);normal.normalize()
                rim=.80 if side else 1.12
                colour=tuple(min(1,c*shade*rim) for c in base)+(1,)
                vertices.append(((centre+side*half,y,h*t),normal,colour,((side+1)/2,t)))
        for i in range(segments):
            for side in range(2):
                a=i*3+side;b=a+3
                triangles.extend(((a,a+1,b),(a+1,b+1,b)))
        leaf=mesh('folded-seagrass-blade',vertices,triangles)
        leaf.setTwoSided(True);leaf.reparentTo(root)
        leaf.setH(blade*137.5+rng.uniform(-18,18))
        leaf.setPos(rng.uniform(-.15,.15),rng.uniform(-.15,.15),0)
    root.flattenStrong()
    return root


def seagrass_site(index):
    """Stable patches, ordered across both sides so low tiers keep the balance."""
    patches=(( -7.2,4.3,3.7), (7.4,5.0,3.9),
             (-19.5,1.0,4.5),(20.0,2.0,4.0),
             (-12.4,-3.6,2.0),(12.8,-3.6,2.2),
             (-6.8,-.9,2.5),(7.2,-1.1,2.5))
    x,y,height=patches[index%len(patches)]
    rng=random.Random(3800+index)
    x+=rng.uniform(-1.15,1.15);y+=rng.uniform(-.85,.85)
    return (x,y,floor_height(x,y)-.035),height*rng.uniform(.8,1.2)


def scenery(parent,settings,placement=None):
    """Build once; one soft tuft per configured plant animates per frame."""
    static=parent.attachNewNode('tidal-garden-static');plants=[]
    detail=min(28,settings.detail)
    floor=floor_mesh();floor.reparentTo(parent);floor.setTexture(sand_texture());floor.setTwoSided(True)
    caustic=None
    if settings.caustics:
        caustic=floor_mesh();caustic.reparentTo(parent);caustic.setZ(.025)
        caustic.setTexture(sand_texture(caustic=True));caustic.setTransparency(TransparencyAttrib.MAlpha)
        caustic.setLightOff();caustic.setDepthWrite(False)
    def place(key,node,pos,solid=False,sway=False):
        node.reparentTo(parent if sway else static);node.setPos(*pos)
        shapes=[(solid_hull(node),(0,0,0),(0,0,0))] if solid else []
        if placement:placement.register('reef:study:'+key,node,shapes,batched=not sway,sway=sway)
        return node
    for i,(pos,scale,seed) in enumerate(ROCKS):
        place('rock:'+str(i),rock_model(scale,seed,detail),pos,True)
    # Far cool silhouettes sit beyond the fish volume, in front of the water plane.
    # Their authored positions and full footprints still participate in mask placement.
    for i,(x,z,sx,sz) in enumerate(((-19,2.5,5.5,4.3),(-10,1.5,3.8,2.8),(7,1.8,4.3,2.8),(18,3.3,5.6,4.5))):
        n=rock_model((sx,1.0,sz),71+i,12,distant=True);n.setLightOff();n.clearTexture()
        place('distant:'+str(i),n,(x,10.5,z))
    plates=(
        ((-12.6,2.5,6.9),2.65,(.73,.54,.33),2),
        ((-14.5,2.8,5.5),2.8,(.63,.43,.30),4),
        ((-11.5,2.7,4.6),2.25,(.80,.62,.41),5),
        ((-9.9,2.1,2.9),1.95,(.55,.64,.44),7),
        ((12.8,2.3,3.8),2.25,(.49,.57,.38),11),
        ((14.8,2.9,4.9),2.5,(.62,.65,.42),13),
        ((17.0,2.5,3.1),2.2,(.44,.56,.46),17),
        ((11.1,1.6,1.8),1.6,(.73,.51,.39),19),
    )
    for i,(pos,radius,col,seed) in enumerate(plates):place('plate:'+str(i),plate_model(radius,col,detail,seed),pos,True)
    for i,(pos,h,col,seed) in enumerate((
        ((-18,3.7,4.0),5.1,(.65,.34,.30),51),
        ((-8.8,3.3,1.3),3.8,(.74,.42,.29),53),
        ((17.8,3.5,3.0),5.2,(.60,.40,.61),57),
        ((9.0,4.3,1.1),3.0,(.58,.32,.45),59))):
        place('fan:'+str(i),fan_model(h,col,detail,seed),pos)
    for i,(x,y,z,h,r) in enumerate(((-17,-2.2,1,2.4,.52),(-16,-2.4,.9,1.8,.42),(-18.0,-2.3,1,1.5,.45),
                                   (16.0,-1.5,.8,1.7,.48),(17.1,-1.4,.8,2.4,.58),(18.2,-1.4,.8,1.5,.4))):
        col=(.64,.40,.26) if x<0 else (.42,.43,.65)
        place('sponge:'+str(i),sponge_model(h,r,col,detail,i),(x,y,z),True)
    # Several low polyp colonies provide a fine-scale contrast to large plates.
    for i,(x,y) in enumerate(((-10,-1),(-8,1),(9,-.3),(19,-2))):
        colony=NodePath('low-coral-colony');rng=random.Random(320+i)
        for j in range(10 if detail<16 else 18):
            a=rng.random()*math.tau;r=rng.random()*.85;h=rng.uniform(.3,.8)
            p=(math.cos(a)*r,math.sin(a)*r,0)
            end=(p[0]*1.2,p[1]*1.2,h)
            tube_mesh((p,end),( .085,.04),(.62,.53,.35) if i%2 else (.42,.62,.53),6).reparentTo(colony)
        colony.flattenStrong();place('colony:'+str(i),colony,(x,y,.1))
    # Honour the normal plant budget (including zero) and existing sway controls.
    # One batched tuft/transform per plant; centre channel and focal rocks stay open.
    for i in range(settings.plants):
        pos,height=seagrass_site(i)
        n=seagrass_model(height,.30 if i%8<4 else .42,detail,800+i)
        place('grass:'+str(i),n,pos,sway=True)
        plants.append((n,random.Random(1800+i).random()*math.tau))
    rng=random.Random(912)
    for i in range(20 if detail<16 else 34):
        x=rng.uniform(-22,22);y=rng.uniform(-4,6)
        n=rock_model((rng.uniform(.10,.30),rng.uniform(.08,.22),.07),i,8)
        place('rubble:'+str(i),n,(x,y,.1))
    if not placement:static.flattenStrong()
    return plants,caustic
