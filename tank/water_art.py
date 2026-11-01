"""Procedural Water v1 creatures. Geometry remains within the fish collision envelope."""
import math
from panda3d.core import NodePath
from .habitat import FISH_SCALES
from .art import ellipsoid, fin, juvenile_colours, expressed_colour

NAMES = ('fish','blowfish','shark','dolphin','whale','seal','shrimp','squid','lobster','crab','octopus','jellyfish','shell-dweller','sea-star')

def creature_model(s, detail, species):
    root=NodePath('water-'+NAMES[species]); root.setTag('water-species',str(species))
    static=root.attachNewNode('static-water-geometry')
    body=expressed_colour(s,'body'); accent=expressed_colour(s,'scales'); eye=expressed_colour(s,'eyes')
    if s.stage in (0,1): body,accent=juvenile_colours(s); eye=(.9,.9,.9)
    detail=max(8,min(detail,20)); joints=[]
    def blob(name,xyz,scale,col=body,parent=static):
        n=ellipsoid(name,scale,col,detail); n.reparentTo(parent); n.setPos(*xyz); return n
    def poly(name,pts,col=accent,parent=static):
        n=fin(name,pts,col); n.reparentTo(parent); return n
    def joint(name,pos):
        n=root.attachNewNode(name); n.setPos(*pos); joints.append(n); return n
    def eyes(x,z,y=.32):
        for side in (-1,1):
            blob('eye-rim',(x,side*y,z),(.13,.05,.13),eye)
            blob('pupil',(x+.015,side*(y+.049),z),(.065,.025,.075),(.018,.03,.05))
    tail=joint('water-tail',(-.65,0,0))
    if species in (1,2,3,4,5):
        scales={1:(.68,.38,.63),2:(.9,.32,.38),3:(.88,.3,.37),4:(.95,.42,.48),5:(.76,.36,.42)}
        blob('body',(0,0,0),scales[species]); eyes(.44,.13,.29)
        if species==1:
            for i in range(10):
                a=math.tau*i/10; x=.68*math.cos(a); z=.63*math.sin(a)
                poly('spine',[(x*.92-.10*math.sin(a),0,z*.92+.10*math.cos(a)),(x*1.25,0,z*1.25),(x*.92+.10*math.sin(a),0,z*.92-.10*math.cos(a))])
        if species in (2,3):
            poly('dorsal',[(-.35,0,.25),(-.1,0,.8),(.25,0,.3)])
            poly('snout',[(.65,0,.15),(1.1,0,.03),(.66,0,-.16)],body)
        if species==4:
            blob('whale-head',(.55,0,.06),(.5,.38,.38)); poly('spout',[(.3,0,.38),(.18,0,.72),(.32,0,.62),(.45,0,.75),(.38,0,.36)])
        if species==5: blob('muzzle',(.7,0,-.12),(.25,.24,.16),accent)
        if species in (3,4):
            # Cetaceans have horizontal flukes; X/Y plane, not shark's vertical tail.
            poly('horizontal-fluke',[(0,0,0),(-.42,-.58,.08),(-.55,0,0),(-.42,.58,.08)],parent=tail)
        elif species==5:
            for side in (-1,1):
                poly('hind-flipper',[(0,0,0),(-.5,side*.34,-.18),(-.35,side*.45,-.32)],parent=tail)
        else:
            poly('tail',[(0,0,0),(-.55,0,.45),(-.4,0,0),(-.55,0,-.45)],parent=tail)
        for side in (-1,1):
            j=joint('flipper',(.0,side*.25,-.1));poly('flipper',[(0,0,0),(-.48,side*.50,-.45),(.20,side*.18,-.24)] if species==5 else [(0,0,0),(-.35,side*.38,-.38),(.25,side*.15,-.2)],parent=j)
    elif species in (6,8,9):
        blob('carapace',(0,0,0),(.42,.32,.32) if species==6 else ((.66,.38,.34) if species==8 else (.56,.43,.48))); eyes(.30,.20,.28)
        for i in range(3 if species!=9 else 4):
            for side in (-1,1):
                j=joint('leg',(-.38+i*.25,side*.25,-.14))
                poly('leg',[(0,0,0),(-.15,side*.22,-.25),(-.28,side*.28,-.38),(-.18,side*.14,-.26)],parent=j)
        if species in (8,9):
            for side in (-1,1):
                j=joint('claw',(.35,side*.29,0));blob('claw',(.30,side*.18,.22 if side<0 else -.2),(.30,.16,.20),accent,j)
                poly('pincer',[(.47,side*.18,.3 if side<0 else -.12),(.72,side*.18,.4 if side<0 else -.02),(.55,side*.18,.16 if side<0 else -.26)],parent=j)
        else:
            # Tapering abdominal segments curve down and then forward.
            for i,(x,z) in enumerate(((-.39,-.02),(-.57,-.12),(-.68,-.28),(-.65,-.43))):
                blob('shrimp-segment',(x,0,z),(.18-i*.02,.24-i*.03,.23-i*.025),accent if i%2 else body)
            poly('antenna',[(.3,-.05,.22),(.75,-.05,.55),(.4,-.05,.24)],accent)
        if species == 8: poly('tail-fan',[(0,0,0),(-.45,0,.3),(-.32,0,0),(-.45,0,-.3)],parent=tail)
    elif species in (7,10,11):
        blob('mantle',(0,0,.25),(.48,.35,.62) if species==7 else (.52,.4,.4))
        if species==7: poly('squid-tip',[(-.4,0,.5),(0,0,1.02),(.4,0,.5)])
        if species==11: blob('bell',(0,0,.25),(.7,.4,.36));
        if species!=11: eyes(.25,.26,.32)
        for i in range(8 if species==10 else 6):
            x=(i-(3.5 if species==10 else 2.5))*.15
            j=joint('tentacle',(x,0,-.08));poly('arm',[(0,0,0),(x*.3,0,-.52),(x*.5+.08,0,-.82),(x*.4+.13,0,-.5)],parent=j)
    elif species==12:
        blob('shell',(-.1,0,.08),(.67,.4,.52),accent);blob('shell-spiral',(-.12,-.39,.1),(.3,.045,.27),body)
        blob('dweller',(.48,0,-.22),(.36,.28,.2));eyes(.68,-.1,.22)
        for side in (-1,1):
            j=joint('foot',(.35,side*.18,-.3));poly('foot',[(0,0,0),(.28,side*.2,-.2),(-.25,side*.25,-.18)],parent=j)
    elif species==13:
        # Five individually triangulated arms avoid a concave polygon fan.
        for i in range(5):
            a=math.pi/2+i*math.tau/5
            tip=(.88*math.cos(a),0,.88*math.sin(a))
            left=(.31*math.cos(a-.52),0,.31*math.sin(a-.52))
            right=(.31*math.cos(a+.52),0,.31*math.sin(a+.52))
            poly('star-arm',[(-.01,0,0),left,tip,right],body)
        blob('centre',(0,-.04,0),(.30,.1,.30),body);eyes(.12,.1,.12)
        for i in range(5):
            a=math.tau*i/5;j=joint('arm-joint',(.3*math.cos(a),0,.3*math.sin(a)))
            blob('arm-tip',(.25*math.cos(a),0,.25*math.sin(a)),(.12,.07,.12),accent,j)
    static.flattenStrong();size=FISH_SCALES[s.stage];root.setScale(size,size,size*(1.1 if s.stage==3 else 1))
    return root,tail,[j for j in joints if j != tail]

def animate_water(root,tail,fins,phase,speed):
    species=int(root.getTag('water-species'))
    if species in (3,4,5): tail.setP(math.sin(phase)*20*speed)
    else: tail.setH(math.sin(phase)*22*speed)
    for i,node in enumerate(fins):
        wave=math.sin(phase*.65+i*1.1)
        if species in (7,10,11,13): node.setR(wave*(12 if species!=11 else 8))
        elif species in (6,8,9,12): node.setP(wave*18)
        else: node.setH(wave*12)
    if species==11:
        # Pulse only the mantle, retaining the simulation root scale and pose.
        bell=root.find('**/static-water-geometry')
        if not bell.isEmpty(): bell.setScale(1+.08*math.sin(phase*.6),1,1-.08*math.sin(phase*.6))
