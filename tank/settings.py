from dataclasses import asdict, dataclass, field
import json
from pathlib import Path

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
    decorations:dict=field(default_factory=dict)
    fish_animations:bool=True
    exit_styles:dict=field(default_factory=dict)
    def apply(self,name):
        for k,v in PRESETS[name].items():setattr(self,k,v)
        self.preset=name
    def save(self,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(asdict(self),indent=2));temporary.replace(path)
    @classmethod
    def load(cls,path):
        try:
            raw=json.loads(Path(path).read_text());s=cls(**raw)
            if not .25<=s.scale<=2 or not 8<=s.detail<=48 or not 0<=s.plants<=100 or not 0<=s.bubbles<=100 or not 10<=s.fps<=240:raise ValueError()
            if not isinstance(s.decorations,dict) or not all(isinstance(k,str) and isinstance(v,bool) for k,v in s.decorations.items()):raise ValueError()
            if not isinstance(s.fish_animations,bool):raise ValueError()
            if not isinstance(s.exit_styles,dict) or not all(isinstance(k,str) and isinstance(v,bool) for k,v in s.exit_styles.items()):raise ValueError()
            return s
        except (OSError,ValueError,TypeError):return cls()
