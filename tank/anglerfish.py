"""Original low-cost Anglerfish art for explicitly received Water registry ID 14.

No identity guessing, per-fish lights, shaders, textures, tasks or moving vertices.
The lure is ordinary mesh emission (unlit), still multiplied by scene lighting.
"""
import math
from panda3d.core import NodePath, Vec3
from .art import colour, tint565, mesh, ellipsoid, fin
from .habitat import FISH_SCALES

SPECIES_ID = 14


def is_anglerfish(snapshot):
    return (getattr(snapshot, 'species_present', False) is True
            and type(getattr(snapshot, 'species_id', None)) is int
            and snapshot.species_id == SPECIES_ID)


def genetic_colour(snapshot, role):
    """H1 8..247 uses DX's exact integer HSV/RGB565 mapping, not legacy fallback.

    0..5 keep the Aquarium's established artistic palette; Mono 6 uses received
    tint. H1 is authoritative only when RX explicitly set its presence bit.
    P1 is source panel provenance, not a request to erase colour in a 3D scene.
    """
    allele = (getattr(snapshot, role+'_gene', None)
              if getattr(snapshot, 'genes_present', False) else None)
    if allele is None:
        allele = getattr(snapshot, role)
    if 8 <= allele <= 247:
        hue = allele-8
        sector, ramp = hue//40, (hue % 40)*255//40
        rgb = ((255,ramp,0), (255-ramp,255,0), (0,255,ramp),
               (0,255-ramp,255), (ramp,0,255), (255,0,255-ramp))[sector]
        genetic = tint565((rgb[0]>>3)<<11 | (rgb[1]>>2)<<5 | rgb[2]>>3)
    else:
        genetic = colour(allele, snapshot.tint)
    return allele, genetic


def colours(snapshot):
    values = {role: genetic_colour(snapshot, role) for role in ('body','scales','eyes')}
    if snapshot.stage >= 2:
        return tuple(values[role][1] for role in ('body','scales','eyes'))
    ivory = tint565(0xFFBC)
    def pale(role, weight):
        allele, rgb = values[role]
        return rgb if allele == 6 else tuple((rgb[k]*weight+ivory[k]*(8-weight))/8 for k in range(3))
    return (pale('body', 2 if snapshot.stage == 0 else 5),
            pale('body' if snapshot.stage == 0 else 'scales', 5 if snapshot.stage == 0 else 6),
            (.90,.90,.90))


def anglerfish_model(snapshot, detail, style):
    # Fit inside the existing fish/contact + projected-fin envelopes at all ages.
    detail = max(8, min(detail, 10 if style == 'faceted' else 20))
    body, scales, eyes = colours(snapshot)
    juvenile = snapshot.stage < 2
    root = NodePath('fish-'+snapshot.owner[:8])
    root.setTag('fish-style', style)
    root.setTag('fish-species', '14')
    static = root.attachNewNode('static-angler-geometry')
    vertices, triangles = [], []
    for i in range(detail+1):
        u = i/detail
        x = -.87+1.75*u
        # Large forward head, narrow tail; not a spherical blowfish or a re-skin.
        radius = max(.018, math.sin(math.pi*u)**.6*(.55+.65*u))
        if style == 'rounded': x *= .92
        for j in range(detail+1):
            angle = math.tau*j/detail
            y, z = .39*radius*math.cos(angle), .52*radius*math.sin(angle)
            n = Vec3((u-.60)*.7, math.cos(angle), math.sin(angle)); n.normalize()
            blend = 0 if juvenile else (.42 if z < -.20 or (i+j//2)%5 == 0 else .08)
            light = .78+.22*(math.sin(angle)+1)/2
            rgb = tuple((body[k]*(1-blend)+scales[k]*blend)*light for k in range(3))
            vertices.append(((x,y,z),n,(*rgb,1),(u,j/detail)))
    for i in range(detail):
        for j in range(detail):
            a = i*(detail+1)+j; b = a+detail+1
            triangles.extend(((a,a+1,b),(a+1,b+1,b)))
    if style == 'faceted':
        flat=[]
        for indices in triangles:
            a,b,c = [Vec3(*vertices[k][0]) for k in indices]
            n = (b-a).cross(c-a)
            if n.lengthSquared() < 1e-12: continue
            n.normalize()
            rgb = tuple(sum(vertices[k][2][i] for k in indices)/3 for i in range(4))
            flat.extend((vertices[k][0],n,rgb,vertices[k][3]) for k in indices)
        vertices=flat;triangles=[(i,i+1,i+2) for i in range(0,len(flat),3)]
    mesh('angler-body',vertices,triangles).reparentTo(static)
    # Side-visible gape on both headings, with adult needle teeth (smaller young).
    for side in (-1,1):
        mouth = ellipsoid('angler-mouth',(.29,.025,.16),(.025,.035,.045),8)
        mouth.reparentTo(static);mouth.setPos(.57,side*.305,-.12)
        teeth = 2 if snapshot.stage == 0 else 3 if snapshot.stage == 1 else 5
        for i in range(teeth):
            x=.36+i*.095
            for sign in (-1,1):
                z=-.12+sign*.13
                length=.045 if juvenile else .095
                fin('angler-tooth',[(x-.025,side*.337,z),(x+.025,side*.337,z),
                                   (x,side*.34,z-sign*length)],(.90,.91,.80)).reparentTo(static)
        rim=ellipsoid('angler-eye-rim',(.11,.045,.11),eyes,8)
        rim.reparentTo(static);rim.setPos(.48,side*.35,.23)
        pupil=ellipsoid('angler-pupil',(.047,.026,.06),(.015,.025,.035),8)
        pupil.reparentTo(static);pupil.setPos(.50,side*.39,.23)
        glint=ellipsoid('angler-eye-glint',(.016,.012,.017),(.98,.99,.94),8)
        glint.reparentTo(static);glint.setPos(.52,side*.413,.25)
    fin('angler-dorsal',[(-.75,0,.15),(-.61,0,.54),(-.32,0,.34),(-.02,0,.48),(.17,0,.30)],scales).reparentTo(static)
    tail=root.attachNewNode('tail-joint');tail.setX(-.78)
    fin('angler-tail',[(0,0,0),(-.55,0,.32),(-.68,0,.18),(-.68,0,-.18),(-.55,0,-.32)],scales).reparentTo(tail)
    fins=[]
    for side in (-1,1):
        joint=root.attachNewNode('pectoral');joint.setPos(.03,side*.29,-.19)
        fin('angler-pectoral',[(0,0,0),(-.32,side*.30,-.20),(-.45,side*.15,.02)],scales).reparentTo(joint)
        fins.append(joint)
    static.flattenStrong()
    # A tapered, curved, six-sided stalk and a tiny bulb: one animated joint,
    # one pooled transform update per displayed fish, no light spill/bloom pass.
    lure=root.attachNewNode('angler-lure-joint');lure.setPos(.12,0,.37)
    points=[(0,0,0),(.025,0,.20),(.16,0,.37),(.40,0,.43),(.62,0,.35),(.68,0,.22)]
    verts=[];tris=[]
    for i,(x,y,z) in enumerate(points):
        radius=.024-i*.0018
        for j in range(6):
            angle=j*math.tau/6
            verts.append(((x+radius*math.cos(angle),y+radius*math.sin(angle),z),
                          (math.cos(angle),math.sin(angle),0),(*body,1),(j/6,i/5)))
    for i in range(len(points)-1):
        for j in range(6):
            a=i*6+j;b=i*6+(j+1)%6
            tris.extend(((a,b,a+6),(b,b+6,a+6)))
    mesh('angler-lure-stalk',verts,tris).reparentTo(lure)
    bulb=ellipsoid('angler-lure-bulb',(.085,.07,.085),
                   tuple(.65+.35*v for v in scales),8)
    bulb.reparentTo(lure);bulb.setPos(*points[-1]);bulb.setLightOff()
    size=FISH_SCALES[snapshot.stage]
    root.setScale(size,size,size*(1.1 if snapshot.stage == 3 else 1))
    return root,tail,fins


def animate(model, phase):
    """Use the existing identity-seeded swim clock; no new timer or task."""
    if model.getTag('fish-species') != '14': return
    # Direct children only; no PythonTag -> NodePath -> parent reference cycle.
    lure=model.find('angler-lure-joint');bulb=lure.find('angler-lure-bulb')
    lure.setH(math.sin(phase*.53)*8)
    lure.setR(math.sin(phase*.71)*3)
    pulse=.92+.08*math.sin(phase*.81)
    bulb.setColorScale(pulse,pulse,pulse,1)
