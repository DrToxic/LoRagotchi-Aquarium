"""Original procedural 3D aquarium art, distributed under this project's MIT licence.

No stock/SereneScreen assets. Meshes, colour masks, plants and textures are generated
from editable mathematical source; no network or external asset downloader.
"""
import math
import random
from .habitat import FISH_SCALES, reef_rocks, coral_branches
from panda3d.core import (GeomVertexFormat,GeomVertexData,GeomVertexWriter,GeomTriangles,Geom,GeomNode,
                         NodePath,PNMImage,Texture,TransparencyAttrib,CardMaker,Vec3)

PALETTE=[(.98,.32,.27), (1.,.56,.15), (.98,.81,.24), (.32,.84,.61), (.12,.64,.83), (.71,.43,.89)]

def tint565(value):
    return ((value>>11)/31,((value>>5)&63)/63,(value&31)/31)

def colour(index,tint=65535):return PALETTE[index] if index<6 else tint565(tint)

def mesh(name,vertices,triangles):
    data=GeomVertexData(name,GeomVertexFormat.getV3n3c4t2(),Geom.UHStatic)
    data.setNumRows(len(vertices))
    pos=GeomVertexWriter(data,"vertex");normal=GeomVertexWriter(data,"normal");color=GeomVertexWriter(data,"color");uv=GeomVertexWriter(data,"texcoord")
    for p,n,c,t in vertices:
        pos.addData3(*p);normal.addData3(*n);color.addData4(*c);uv.addData2(*t)
    primitive=GeomTriangles(Geom.UHStatic)
    for a,b,c in triangles:primitive.addVertices(a,b,c)
    primitive.closePrimitive();geom=Geom(data);geom.addPrimitive(primitive)
    node=GeomNode(name);node.addGeom(geom)
    return NodePath(node)


def ellipsoid(name,scale,color,detail=16,rough=0,seed=0):
    rng=random.Random(seed);verts=[];tri=[];rings=max(6,detail//2)
    for i in range(rings+1):
        p=math.pi*i/rings
        for j in range(detail+1):
            a=math.tau*j/detail
            n=(math.sin(p)*math.cos(a),math.sin(p)*math.sin(a),math.cos(p))
            r=1+rough*(rng.random()-.5)
            xyz=tuple(n[k]*scale[k]*r for k in range(3))
            light=.8+.2*max(n[2],0)
            c=tuple(v*light for v in color[:3])+(color[3] if len(color)==4 else 1,)
            normal=Vec3(*(n[k]/max(scale[k],.01) for k in range(3)));normal.normalize()
            verts.append((xyz,normal,c,(j/detail,i/rings)))
    for i in range(rings):
        for j in range(detail):
            a=i*(detail+1)+j;b=a+detail+1
            tri.extend(((a,b,a+1),(a+1,b,b+1)))
    return mesh(name,verts,tri)


def fin(name,points,color):
    verts=[(p,(0,-1,0),tuple(color)+(0.82,),(.5,.5)) for p in points]
    node=mesh(name,verts,[(0,i,i+1) for i in range(1,len(points)-1)])
    node.setTwoSided(True);node.setTransparency(TransparencyAttrib.MAlpha)
    return node


def fish_model(snapshot,detail,style='classic'):
    from .themes import STYLES
    if style not in STYLES:raise ValueError('Unknown fish style')
    # Every variant stays inside Classic's body/contact and projected fin envelope.
    rounded=style=='rounded';faceted=style=='faceted'
    if faceted:detail=min(detail,10)
    root=NodePath("fish-"+snapshot.owner[:8]);body=colour(snapshot.body,snapshot.tint);scales=colour(snapshot.scales,snapshot.tint);eye=colour(snapshot.eyes,snapshot.tint)
    root.setTag("fish-style",style)
    static=root.attachNewNode("static-fish-geometry")
    # Fusiform body, elliptical in section; bands are vertex-coloured masks.
    verts=[];tri=[];rings=detail;radial=max(8,detail)
    for i in range(rings+1):
        u=i/rings;x=-1.0+2*u
        radius=max(.025,math.sin(math.pi*u)**(.4 if rounded else .72))
        if rounded:x*=.82
        for j in range(radial+1):
            angle=math.tau*j/radial
            y=.38*radius*math.cos(angle);z=.58*radius*math.sin(angle)
            normal=Vec3((u-.5)*.8,math.cos(angle),math.sin(angle));normal.normalize()
            # Fine dorsal stripe and alternating glimmering scale rows.
            blend=.55 if (int(u*12)+int(j/2))%3==0 else .13
            if z>.28:blend=.65
            brightness=.75+.25*(math.sin(angle)+1)/2
            col=tuple((body[k]*(1-blend)+scales[k]*blend)*brightness for k in range(3))+(1,)
            verts.append(((x,y,z),normal,col,(u,j/radial)))
    for i in range(rings):
        for j in range(radial):
            a=i*(radial+1)+j;b=a+radial+1;tri.extend(((a,a+1,b),(a+1,b+1,b)))
    if faceted:
        # Flat per-face normals, not just fewer smooth triangles.
        flat=[]
        for indices in tri:
            a,b,c=[Vec3(*verts[k][0]) for k in indices]
            normal=(b-a).cross(c-a)
            if normal.lengthSquared()<1e-12:continue
            normal.normalize()
            colour_mean=tuple(sum(verts[k][2][i] for k in indices)/3 for i in range(4))
            flat.extend((verts[k][0],normal,colour_mean,verts[k][3]) for k in indices)
        verts=flat;tri=[(i,i+1,i+2) for i in range(0,len(flat),3)]
    mesh("body",verts,tri).reparentTo(static)
    # Tail assembly has its own joint, with another small tip joint.
    tail=root.attachNewNode("tail-joint");tail.setX(-.72 if rounded else -.88)
    fin("tail",([(0,0,0),(-.28,0,.25),(-.5,0,.5),(-.6,0,.35),(-.55,0,0),(-.6,0,-.35),(-.5,0,-.5),(-.28,0,-.25)] if rounded else [(0,0,0),(-.65,0,.58),(-.53,0,0),(-.65,0,-.58)]),scales).reparentTo(tail)
    fin("dorsal",[(-.65,0,.32),(-.48,0,.87),(.38,0,.63),(.65,0,.31)],scales).reparentTo(static)
    fin("ventral",[(-.5,0,-.35),(-.45,0,-.74),(.2,0,-.48)],scales).reparentTo(static)
    fins=[]
    for side in (-1,1):
        finnode=root.attachNewNode("pectoral");finnode.setPos(.15,side*.31,-.03)
        fin("pectoral",[(0,0,0),(-.35,side*.4,-.27),(-.48,side*.12,.05)],body).reparentTo(finnode);fins.append(finnode)
        eyeNode=ellipsoid("eye-rim",(.14,.055,.14),eye,max(8,detail//2));eyeNode.reparentTo(static);eyeNode.setPos(.53 if rounded else .65,side*(.31 if rounded else .27),.18)
        pupil=ellipsoid("eye",(.07,.035,.085),(.018,.03,.05),max(8,detail//2));pupil.reparentTo(static);pupil.setPos(.55 if rounded else .67,side*(.356 if rounded else .316),.18)
        glint=ellipsoid("eye-glint",(.023,.013,.025),(1.,1.,.94),8);glint.reparentTo(static);glint.setPos(.57 if rounded else .69,side*(.384 if rounded else .344),.21);glint.setLightOff()
    static.flattenStrong()
    size=FISH_SCALES[snapshot.stage];root.setScale(size, size, size*(1.1 if snapshot.stage==3 else 1))
    return root,tail,fins


def sand_texture(size=256,caustic=False):
    rng=random.Random(73);image=PNMImage(size,size,4 if caustic else 3)
    for y in range(size):
        for x in range(size):
            if caustic:
                wave=abs(math.sin(x*.075+2*math.sin(y*.035))*math.sin(y*.08+math.cos(x*.04)))
                line=max(0,1-wave*15)**2
                image.setXelA(x,y,.47,.88,.79,line*.35)
            else:
                n=rng.random()*.07+.04*math.sin(y*.32+math.sin(x*.03)*2)
                image.setXel(x,y,.48+n,.49+n,.37+n)
    tex=Texture("caustics" if caustic else "sand");tex.load(image);tex.setWrapU(Texture.WMRepeat);tex.setWrapV(Texture.WMRepeat)
    return tex


def floor_mesh():
    verts=[];tri=[];nx=50;ny=20
    for j in range(ny+1):
        for i in range(nx+1):
            x=(i/nx-.5)*70;y=(j/ny-.5)*50
            z=.13*math.sin(x*.3)+.07*math.cos(y*.5+x*.2)
            verts.append(((x,y,z),(0,0,1),(1,1,1,1),(i/nx*5,j/ny*3)))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+nx+1;tri.extend(((a,a+1,b),(a+1,b+1,b)))
    return mesh("rippling-sand",verts,tri)


def plant_leaf(height,width,bend,color,detail=10):
    verts=[];tri=[]
    for i in range(detail+1):
        t=i/detail;half=width*math.sin(math.pi*t)*.5+.005
        center=bend*t*t+math.sin(t*4)*width
        for side in (-1,1):verts.append(((center+side*half,math.sin(t*5)*.08,height*t),(0,-1,.15),(*color,1),(side/2+.5,t)))
    for i in range(detail):
        a=i*2;tri.extend(((a,a+1,a+2),(a+1,a+3,a+2)))
    leaf=mesh("ribbon-leaf",verts,tri);leaf.setTwoSided(True);return leaf


def scenery(parent,settings,placement=None):
    rng=random.Random(101)
    static=parent.attachNewNode("static-reef")
    floor=floor_mesh();floor.reparentTo(parent);floor.setTexture(sand_texture());floor.setTwoSided(True)
    caustic=None
    if settings.caustics:
        caustic=floor_mesh();caustic.reparentTo(parent);caustic.setZ(.025);caustic.setTexture(sand_texture(caustic=True));caustic.setTransparency(TransparencyAttrib.MAlpha);caustic.setLightOff();caustic.setDepthWrite(False)
    # Tiered rock clusters frame a clear centre swimming space.
    for index,(pos,scale,heading,colour,seed) in enumerate(reef_rocks(rng)):
        rock=ellipsoid("reef-stone",scale,colour,max(8,settings.detail),.18,seed)
        rock.reparentTo(static);rock.setPos(*pos);rock.setH(heading)
        if placement:
            from .collision import ellipsoid_hull
            placement.register(f'reef:rock:{index}',rock,[(ellipsoid_hull(scale,1.12),(0,0,0),(heading,0,0))],batched=True)
    plants=[]
    for i in range(settings.plants):
        side=-1 if i%2 else 1;x=side*(10+rng.random()*10);y=-2+rng.random()*10
        node=parent.attachNewNode("plant");node.setPos(x,y,.1);node.setH(rng.randrange(360));plants.append((node,rng.random()*math.tau))
        col=(.10+rng.random()*.13,.34+rng.random()*.16,.22+rng.random()*.15)
        for j in range(3):
            leaf=plant_leaf(1.2+rng.random()*4,.25+rng.random()*.35,rng.uniform(-1,1),col,max(4,settings.detail//2));leaf.reparentTo(node);leaf.setH(j*110)
        if placement:placement.register(f'reef:plant:{i}',node,sway=True)
    # Original branching coral, low in the tank, cool/warm accents.
    coral_groups={}
    for index,(pos,scale,roll) in enumerate(coral_branches()):
        coral=(.58,.26,.30) if pos[0]<0 else (.40,.31,.57)
        stalk=ellipsoid("coral-branch",scale,coral,max(8,settings.detail//2))
        stalk.reparentTo(static);stalk.setPos(*pos);stalk.setR(roll)
        if placement:
            from .collision import ellipsoid_hull
            group=index//5
            if group not in coral_groups:
                root=static.attachNewNode('coral-cluster');root.setPos(pos[0],pos[1],0)
                coral_groups[group]=(root,[])
            root,shapes=coral_groups[group]
            stalk.wrtReparentTo(root)
            shapes.append((ellipsoid_hull(scale,1.06),tuple(stalk.getPos()),(0,0,roll)))
    if placement:
        for index,(root,shapes) in coral_groups.items():placement.register(f'reef:coral:{index}',root,shapes,batched=True)
    # Tiny scattered pebbles are merged by Panda's static scene flattening.
    for i in range(70 if settings.detail>12 else 20):
        rock=ellipsoid("pebble",(.09+rng.random()*.18,.09,.055),(.37,.40,.32),8)
        rock.reparentTo(static);rock.setPos(rng.uniform(-20,20),rng.uniform(-7,5),.15)
        if placement:placement.register(f'reef:pebble:{i}',rock,batched=True)
    if not placement:static.flattenStrong()
    return plants,caustic
