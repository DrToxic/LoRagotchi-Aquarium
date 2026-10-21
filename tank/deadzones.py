"""Output-space keep-out shapes and portable, versioned display preferences.

No extra geometry dependency: rectangular union coverage uses exact interval
sweeps; rounded boxes and ellipses use analytic box intersection tests.
"""
from dataclasses import asdict, dataclass, field
import json
import math
import uuid
from pathlib import Path

SHAPES = ('Rectangle', 'Rounded rectangle', 'Ellipse')
MAX_WINDOWS = 8
MAX_ZONES = 16


@dataclass(frozen=True)
class Deadzone:
    shape: str = 'Rectangle'
    x: float = 35.
    y: float = 35.
    width: float = 30.
    height: float = 30.
    enabled: bool = True
    blackout: bool = False
    inverted: bool = False
    uid: str = ''
    edge_shelf: bool = False

    def __post_init__(self):
        if self.shape not in SHAPES:
            raise ValueError('Choose a supported shape.')
        if any(type(v) is not bool for v in (self.enabled,self.blackout,self.inverted,self.edge_shelf)):
            raise ValueError('Use on/off values for zone switches.')
        if not isinstance(self.uid,str) or len(self.uid)>80:raise ValueError('Invalid zone identity')
        if not all(math.isfinite(v) for v in (self.x, self.y, self.width, self.height)):
            raise ValueError('Coordinates must be finite numbers.')
        if not (0 <= self.x < 100 and 0 <= self.y < 100 and
                1 <= self.width <= 100-self.x and 1 <= self.height <= 100-self.y):
            raise ValueError('Use 0–100%; width/height at least 1%, inside the layout.')

    def bounds(self):
        return (self.x/50-1, (self.x+self.width)/50-1,
                1-(self.y+self.height)/50, 1-self.y/50)

    def intersects(self, box, aspect=1.):
        if not self.enabled:
            return False
        left, right, bottom, top = self.bounds()
        x0, x1, y0, y1 = box
        if x1 < left or x0 > right or y1 < bottom or y0 > top:
            return False
        if self.shape == 'Rectangle':
            return True
        # Work in physical screen proportions, not stretched NDC coordinates.
        cx, cy = (left+right)*aspect/2, (bottom+top)/2
        hx, hy = (right-left)*aspect/2, (top-bottom)/2
        dx = max(x0*aspect-cx, cx-x1*aspect, 0.)
        dy = max(y0-cy, cy-y1, 0.)
        if self.shape == 'Ellipse':
            return (dx/hx)**2+(dy/hy)**2 <= 1.
        radius = min(hx, hy)*.5
        return max(dx-(hx-radius), 0.)**2+max(dy-(hy-radius), 0.)**2 <= radius**2

    def contains(self, box, aspect=1.):
        """Whole-box containment in a convex shape, including curved corners."""
        left,right,bottom,top=self.bounds()
        x0,x1,y0,y1=box
        if x0<left or x1>right or y0<bottom or y1>top:return False
        if self.shape=='Rectangle':return True
        cx,cy=(left+right)*aspect/2,(bottom+top)/2
        hx,hy=(right-left)*aspect/2,(top-bottom)/2
        dx=max(abs(x0*aspect-cx),abs(x1*aspect-cx))
        dy=max(abs(y0-cy),abs(y1-cy))
        if self.shape=='Ellipse':return (dx/hx)**2+(dy/hy)**2<=1.
        radius=min(hx,hy)*.5
        return max(dx-(hx-radius),0.)**2+max(dy-(hy-radius),0.)**2<=radius**2

    def blocks(self, box, aspect=1.):
        return self.enabled and (not self.contains(box,aspect) if self.inverted else self.intersects(box,aspect))

    def outline(self, aspect=1., steps=48):
        left, right, bottom, top = self.bounds()
        cx, cy = (left+right)/2, (bottom+top)/2
        hx, hy = (right-left)/2, (top-bottom)/2
        if self.shape == 'Rectangle':
            return [(left,bottom),(right,bottom),(right,top),(left,top),(left,bottom)]
        if self.shape == 'Ellipse':
            return [(cx+hx*math.cos(i*math.tau/steps), cy+hy*math.sin(i*math.tau/steps)) for i in range(steps+1)]
        radius = min(hx*aspect,hy)*.5
        points = []
        for sx,sy,start in ((1,1,0),(-1,1,90),(-1,-1,180),(1,-1,270)):
            for i in range(steps//4+1):
                angle=math.radians(start+90*i/(steps//4))
                points.append((cx+sx*(hx-radius/aspect)+radius/aspect*math.cos(angle),
                               cy+sy*(hy-radius)+radius*math.sin(angle)))
        return points+[points[0]]


def covered(box, regions):
    """The entire box must lie in the union, including across adjoining seams."""
    left,right,bottom,top=box
    relevant=[r for r in regions if r[0] <= right and r[1] >= left and r[2] <= top and r[3] >= bottom]
    if any(a <= left and b >= right and c <= bottom and d >= top for a,b,c,d in relevant):
        return True
    cuts=sorted({left,right,*[max(left,min(right,v)) for r in relevant for v in r[:2]]})
    for a,b in zip(cuts,cuts[1:]):
        if b-a < 1e-12:continue
        x=(a+b)/2
        intervals=sorted((c,d) for l,r,c,d in relevant if l <= x <= r)
        end=bottom
        for c,d in intervals:
            if c > end+1e-10:break
            end=max(end,d)
        if end < top-1e-10:return False
    return bool(relevant)


@dataclass
class DisplayProfile:
    constrain: bool = True
    zones: list[Deadzone] = field(default_factory=list)
    windows: list[tuple[int,int,int,int]] = field(default_factory=list)
    protect_scenery: bool = True
    placements: dict = field(default_factory=dict)
    window_ids: list[str] = field(default_factory=list)

    def identities(self):
        from dataclasses import replace
        seen=set()
        for i,zone in enumerate(self.zones):
            if not zone.uid or zone.uid in seen:
                zone=replace(zone,uid=uuid.uuid4().hex);self.zones[i]=zone
            seen.add(zone.uid)
        while len(self.window_ids)<len(self.windows):self.window_ids.append(uuid.uuid4().hex)
        self.window_ids=self.window_ids[:len(self.windows)]

    @classmethod
    def load(cls,path):
        try:
            raw=json.loads(Path(path).read_text())
            if not isinstance(raw,dict) or raw.get('version') not in (1,2) or type(raw.get('constrain',True)) is not bool:raise ValueError()
            zones=[]
            for z in raw.get('zones',[]):
                z=dict(z)
                # Invalid new metadata never discards otherwise valid v1 geometry.
                if not isinstance(z.get('uid',''),str) or len(z.get('uid',''))>80:z['uid']=''
                if type(z.get('edge_shelf',False)) is not bool:z['edge_shelf']=False
                zones.append(Deadzone(**z))
            windows=[tuple(r) for r in raw.get('windows',[])]
            if len(zones)>MAX_ZONES or len(windows)>MAX_WINDOWS:raise ValueError()
            for r in windows:
                if len(r)!=4 or any(type(v) is not int for v in r):raise ValueError()
                x,y,w,h=r
                if not (-100000<=x<=100000 and -100000<=y<=100000 and 320<=w<=16384 and 180<=h<=16384):raise ValueError()
            protected=raw.get('protect_scenery',True)
            placements={}
            for key,item in (raw.get('placements',{}) if isinstance(raw.get('placements',{}),dict) else {}).items():
                if not isinstance(key,str) or len(key)>160 or not isinstance(item,dict):continue
                pos=item.get('position')
                if not isinstance(pos,list) or len(pos)!=3 or any(type(n) not in (int,float) or not math.isfinite(n) or abs(n)>1000 for n in pos):continue
                placements[key]={'position':list(pos),'pinned':item.get('pinned') is True,
                                 'support':str(item.get('support','floor'))[:160]}
                if len(placements)>=512:break
            ids=raw.get('window_ids',[])
            if not isinstance(ids,list) or any(not isinstance(v,str) or not v or len(v)>80 for v in ids) or len(set(ids))!=len(ids):ids=[]
            return cls(raw.get('constrain',True),zones,windows,protected if type(protected) is bool else True,placements,ids[:MAX_WINDOWS])
        except (OSError,ValueError,TypeError,KeyError):return cls()

    def save(self,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():
            try:
                if json.loads(path.read_text()).get('version')==1:
                    backup=path.with_suffix('.v1.json')
                    if not backup.exists():backup.write_bytes(path.read_bytes())
            except (ValueError,AttributeError):pass
        temporary=path.with_suffix('.tmp')
        temporary.write_text(json.dumps({'version':2,**asdict(self)},indent=2))
        temporary.replace(path)
