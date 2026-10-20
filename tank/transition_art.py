"""Original, editable pickup actors. No external art or runtime downloads.

Models face +X; the bowl/cage have an open +X entrance. Translucent surfaces
never write depth, so the passenger stays visible through its carrier.
"""
import math
from panda3d.core import NodePath, TransparencyAttrib, Vec3
from .art import ellipsoid, fin, mesh


def ball(parent, name, pos, size, colour):
    node = ellipsoid(name, size, colour, 16)
    node.reparentTo(parent); node.setPos(*pos)
    return node


def beam(parent, a, b, width, colour, name="frame"):
    delta = Vec3(*b)-Vec3(*a)
    node = ball(parent, name, tuple((x+y)/2 for x,y in zip(a,b)),
                (width, width, delta.length()/2+width), colour)
    node.setHpr(math.degrees(math.atan2(delta.y,delta.x)), 0,
                math.degrees(math.acos(delta.z/delta.length())))
    return node


def ring(parent, radius, z, colour, width=.045, yscale=1.):
    for i in range(24):
        a, b = math.tau*i/24, math.tau*(i+1)/24
        beam(parent, (radius*math.cos(a),radius*math.sin(a)*yscale,z),
             (radius*math.cos(b),radius*math.sin(b)*yscale,z), width, colour)


def translucent(node):
    node.setTransparency(TransparencyAttrib.MAlpha)
    node.setDepthWrite(False); node.setTwoSided(True)


def shell(parent, name, rings, colour):
    vertices, triangles = [], []
    for radius, z in rings:
        for j in range(33):
            angle = math.tau*j/32
            vertices.append(((radius*math.cos(angle),radius*math.sin(angle),z),
                             (math.cos(angle),math.sin(angle),.1),colour,(j/32,z)))
    for i in range(len(rings)-1):
        for j in range(32):
            a=i*33+j; b=a+33
            triangles.extend(((a,a+1,b),(a+1,b+1,b)))
    node=mesh(name,vertices,triangles);node.reparentTo(parent);translucent(node)


def make_actor(style):
    root=NodePath("pickup-"+style)
    blue=(.24,.54,.66); pale=(.76,.88,.87); cord=(.83,.73,.43)
    if style=="shark":
        ball(root,"shark-body",(-1.,0,0),(2.55,.85,1.02),blue)
        ball(root,"belly",(-.7,-.03,-.37),(2.15,.82,.63),pale)
        # Dark, toothless oval mouth and soft jaw. No injury/gore assets.
        ball(root,"mouth",(1.15,0,-.12),(.4,.69,.64),(.035,.09,.12))
        jaw=root.attachNewNode("jaw")
        ball(jaw,"chin",(.78,0,-.49),(.94,.73,.27),pale)
        fin("dorsal",[(-1.7,0,.65),(-1.5,0,2.05),(-.2,0,.78)],blue).reparentTo(root)
        tail=root.attachNewNode("tail");tail.setX(-3.3)
        fin("tail-fin",[(0,0,0),(-1.1,0,1.35),(-.7,0,0),(-1.1,0,-1.05)],blue).reparentTo(tail)
        for side in (-1,1):
            fin("flipper",[(-.2,side*.5,-.2),(-1.4,side*1.6,-.7),(-1.7,side*.55,-.2)],blue).reparentTo(root)
            ball(root,"eye-white",(.62,side*.70,.38),(.29,.12,.30),(1,1,.94))
            ball(root,"pupil",(.73,side*.79,.37),(.12,.07,.17),(.02,.05,.08))
            ball(root,"eye-glint",(.77,side*.84,.44),(.045,.025,.05),(1,1,1))
        return root
    if style=="net":
        # Broad open hoop with an actual mesh pocket underneath.
        ring(root,2.1,.55,cord,.065,yscale=.72)
        for i in range(13):
            angle=math.tau*i/13
            last=(2.1*math.cos(angle),1.51*math.sin(angle),.55)
            for radius,z in ((1.8,-.2),(1.2,-.9),(.25,-1.35)):
                point=(radius*math.cos(angle),radius*.72*math.sin(angle),z)
                beam(root,last,point,.017,pale,"net-mesh");last=point
        for radius,z in ((1.8,-.2),(1.2,-.9),(.5,-1.26)):
            ring(root,radius,z,pale,.018,yscale=.72)
        beam(root,(-2.1,0,.55),(-2.8,0,5.8),.10,cord,"handle")
    elif style=="bag":
        shell(root,"clear-bag",[(.5,-1.4),(1.6,-1.1),(1.9,.4),(1.1,1.7),(.3,2.3)],
              (.64,.91,.96,.18))
        ring(root,1.6,-1.05,pale,.025)
        ring(root,.3,2.3,cord,.08)
        shell(root,"water",[(1.6,-1.05),(1.85,.35)],(.12,.63,.80,.12))
        beam(root,(0,0,2.3),(0,0,7),.035,cord,"lift-cord")
    elif style=="bowl":
        shell(root,"glass-bowl",[(.85,-1.25),(1.7,-.85),(2.0,.1),(1.75,1.1),(1.3,1.65)],
              (.61,.91,.96,.16))
        ring(root,.85,-1.25,pale,.06);ring(root,1.3,1.65,pale,.055)
        shell(root,"water",[(1.65,-.8),(1.95,.45)],(.10,.60,.80,.10))
        for side in (-1,1):
            beam(root,(side*1.3,0,1.65),(0,0,4.3),.045,cord,"lifting-sling")
        beam(root,(0,0,4.3),(0,0,8),.035,cord,"lift-cord")
    elif style=="cage":
        # Open +X doorway: no bar across the passenger's entrance.
        for z in (-1.2,1.4):
            for a,b in (((-2,-1,z),(2,-1,z)),((-2,1,z),(2,1,z)),((-2,-1,z),(-2,1,z))):
                beam(root,a,b,.07,cord)
        for x in (-2,-1,0,1,2):
            for y in (-1,1):
                beam(root,(x,y,-1.2),(x,y,1.4),.035,pale,"cage-bar")
        for y in (-1,-.5,0,.5,1):
            beam(root,(-2,y,-1.2),(-2,y,1.4),.035,pale,"back-bar")
            beam(root,(-2,y,-1.2),(2,y,-1.2),.035,pale,"floor-bar")
        for side in (-1,1):
            beam(root,(side*1.8,0,1.4),(0,0,3.2),.045,cord,"sling")
        beam(root,(0,0,3.2),(0,0,7),.035,cord,"lift-cord")
    else:
        raise ValueError("Unknown pickup style: "+style)
    return root
