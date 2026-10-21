from dataclasses import asdict, dataclass, field, fields
import json
import math
from pathlib import Path
from .appearance import Appearance

PRESETS={
    "compatibility":dict(scale=.5,detail=8,plants=8,bubbles=0,lighting=False,caustics=False,fps=30),
    "low":dict(scale=.65,detail=12,plants=16,bubbles=8,lighting=True,caustics=False,fps=30),
    "balanced":dict(scale=.85,detail=18,plants=32,bubbles=18,lighting=True,caustics=True,fps=45),
    "high":dict(scale=1.,detail=24,plants=48,bubbles=30,lighting=True,caustics=True,fps=60),
    "ultra":dict(scale=1.,detail=32,plants=72,bubbles=50,lighting=True,caustics=True,fps=60),
}
@dataclass
class Settings:
    preset:str="balanced"
    scale:float=.85
    detail:int=18
    plants:int=32
    bubbles:int=18
    lighting:bool=True
    caustics:bool=True
    fps:int=45
    vsync:bool=True
    chat_bubbles:bool=True
    show_names:bool=False
    decorations:dict=field(default_factory=dict)
    fish_animations:bool=True
    exit_styles:dict=field(default_factory=dict)
    appearance:Appearance=field(default_factory=Appearance)
    schema_version:int=2
    def apply(self,name):
        for k,v in PRESETS[name].items():setattr(self,k,v)
        self.preset=name
    def save(self,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        if getattr(self,'load_warnings',None) and path.exists():
            # Loading never edits a broken file. A later explicit save preserves
            # its exact original bytes first, without overwriting older backups.
            original=path.read_bytes()
            number=0
            while True:
                backup=path.with_name(path.name+'.pre-migration'+(f'.{number}' if number else '')+'.bak')
                try:
                    with backup.open('xb') as stream:stream.write(original)
                    break
                except FileExistsError:number+=1
        raw={**getattr(self,'_extra',{}),**asdict(self)}
        raw['appearance']={**getattr(self.appearance,'_extra',{}),**raw['appearance']}
        temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(raw,indent=2));temporary.replace(path)
        self.load_warnings=[]
    @classmethod
    def load(cls,path):
        s=cls();s.load_warnings=[]
        try:
            raw=json.loads(Path(path).read_text())
            if not isinstance(raw,dict):raise ValueError('Settings must be an object')
        except FileNotFoundError:return s
        except (OSError,ValueError,TypeError):
            s.load_warnings.append('Unreadable settings; using defaults without modifying the file')
            return s
        known={f.name for f in fields(cls)}
        s._extra={k:v for k,v in raw.items() if k not in known}
        for key,value in raw.items():
            if key not in known:continue
            try:
                if key=='appearance':
                    value=Appearance.from_dict(value,strict=False,warnings=s.load_warnings)
                else:value=validate_setting(key,value)
                setattr(s,key,value)
            except ValueError as exc:s.load_warnings.append(f'{key}: {exc}; default retained')
        s.schema_version=max(2,s.schema_version)
        return s


LIMITS={'scale':(.25,2,False),'detail':(8,48,True),'plants':(0,100,True),
        'bubbles':(0,100,True),'fps':(10,240,True)}


def validate_setting(key,value):
    if key in LIMITS:
        low,high,integer=LIMITS[key]
        if type(value) not in (float,int) or not math.isfinite(value) or not low<=value<=high or (integer and type(value) is not int):
            raise ValueError(f'Must be {low}..{high}'+(' (integer)' if integer else ''))
    elif key=='preset':
        if not isinstance(value,str) or value not in (*PRESETS,'custom'):raise ValueError('Unknown preset')
    elif key=='schema_version':
        if type(value) is not int or value<1:raise ValueError('Invalid schema version')
    elif key in ('decorations','exit_styles'):
        if not isinstance(value,dict) or not all(isinstance(k,str) and isinstance(v,bool) for k,v in value.items()):
            raise ValueError('Expected named on/off selections')
    elif not isinstance(value,bool):raise ValueError('Expected true or false')
    return value
