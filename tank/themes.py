"""Versioned data-only themes. No collection, settings or executable assets in packs."""
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from .appearance import Appearance, validate

STYLES = ('classic', 'rounded', 'faceted')
FIELDS = ('brightness','day_brightness','night_brightness','day_colour','night_colour',
          'ambient_strength','surface_strength','fill_strength','surface_heading','surface_elevation',
          'background_style','background_top','background_bottom','fog_colour','fog_density','sand_tint',
          'caustics_strength','caustics_speed','shafts_strength','plant_sway','plant_speed')
MAX_BYTES = 16384
MAX_CUSTOM = 128


def preset(key, name, **appearance):
    return dict(schema_version=1,id=key,name=name,extends='classic',appearance=appearance,fish_style='classic')


BUILTINS = {
    'classic': preset('classic','Classic'),
    'tropical': preset('tropical','Tropical shallows',background_style='gradient',background_top='#267f8f',
        background_bottom='#063544',fog_colour='#12505c',fog_density=.008,sand_tint='#fff0c2',day_colour='#fff5e3',surface_strength=1.15),
    'deep-sea': preset('deep-sea','Deep sea',background_style='gradient',background_top='#10344f',
        background_bottom='#020b20',fog_colour='#071d35',fog_density=.025,sand_tint='#718eaa',brightness=.7,caustics_strength=.35,shafts_strength=.5),
    'freshwater': preset('freshwater','Freshwater',background_style='gradient',background_top='#466f59',
        background_bottom='#0d2928',fog_colour='#233f35',fog_density=.018,sand_tint='#d5bc83',day_colour='#e8f4d6',caustics_strength=.6),
    'moonlit': preset('moonlit','Moonlit',background_style='gradient',background_top='#293f69',
        background_bottom='#080d22',fog_colour='#131e39',brightness=.5,sand_tint='#a6b5dc',day_colour='#b5caff',caustics_strength=.4,plant_speed=.6),
    'minimal': preset('minimal','Minimal',background_style='solid',background_top='#102b34',
        background_bottom='#102b34',fog_density=0.,sand_tint='#b7c5c7',caustics_strength=0.,shafts_strength=0.,plant_sway=.35),
}


def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,47}',value):
        raise ValueError('Theme ID must be 1–48 lowercase letters, numbers or hyphens; start with a letter')
    return value


def overrides(raw):
    if not isinstance(raw,dict) or raw.keys()-set(FIELDS):
        raise ValueError('Theme appearance contains unknown or non-theme fields')
    return {key:validate(key,value) for key,value in raw.items()}


def manifest(raw):
    if not isinstance(raw,dict) or raw.keys()-{'schema_version','id','name','extends','appearance','fish_style'}:
        raise ValueError('Expected a theme manifest, not settings or a collection')
    if type(raw.get('schema_version')) is not int or raw['schema_version']!=1:
        raise ValueError('Unsupported theme schema_version (expected 1)')
    key=identifier(raw.get('id'))
    if key=='current':raise ValueError('current is reserved for existing appearance settings')
    name=raw.get('name')
    if not isinstance(name,str) or not 1<=len(name.strip())<=64 or any(ord(c)<32 for c in name):
        raise ValueError('Theme name must be 1–64 printable characters')
    parent=raw.get('extends','classic')
    if not isinstance(parent,str) or parent not in BUILTINS:raise ValueError('Themes may extend one built-in only')
    style=raw.get('fish_style','classic')
    if style not in STYLES:raise ValueError('Unknown fish_style')
    return dict(schema_version=1,id=key,name=name.strip(),extends=parent,
                appearance=overrides(raw.get('appearance',{})),fish_style=style)


def decode(data):
    if len(data)>MAX_BYTES:raise ValueError('Theme manifest exceeds 16 KiB')
    try:return manifest(json.loads(data))
    except (UnicodeError,TypeError,RecursionError) as exc:raise ValueError('Invalid theme JSON') from exc


def encode(raw):return (json.dumps(manifest(raw),indent=2,ensure_ascii=False)+'\n').encode('utf-8')


def resolve(raw):
    raw=manifest(raw)
    defaults=asdict(Appearance())
    return {key:defaults[key] for key in FIELDS} | BUILTINS[raw['extends']]['appearance'] | raw['appearance']


def apply(settings,raw):
    """Copy aesthetic values, never schedule, visibility switches or performance budgets."""
    result=deepcopy(settings);raw=manifest(raw)
    for key,value in resolve(raw).items():setattr(result.appearance,key,value)
    result.fish_style=raw['fish_style'];result.theme_id=raw['id']
    return result


def from_settings(settings,key,name):
    return manifest(dict(schema_version=1,id=key,name=name,extends='classic',
        appearance={key:getattr(settings.appearance,key) for key in FIELDS},fish_style=settings.fish_style))


class ThemeLibrary:
    def __init__(self,root):self.root=Path(root)

    def read(self,key):
        identifier(key)
        if key in BUILTINS:return deepcopy(BUILTINS[key])
        path=self.root/(key+'.json')
        if path.is_symlink():raise ValueError('Theme symlinks are not supported')
        with path.open('rb') as stream:raw=decode(stream.read(MAX_BYTES+1))
        if raw['id']!=key:raise ValueError('Theme ID must match its filename')
        return raw

    def list(self):
        found=[dict(manifest=self.read(k),builtin=True,revision=None) for k in BUILTINS]
        warnings=[]
        for path in sorted(self.root.glob('*.json'))[:MAX_CUSTOM]:
            if path.stem in BUILTINS:
                warnings.append(f'{path.name}: built-in name is reserved');continue
            try:
                raw=self.read(path.stem)
                found.append(dict(manifest=raw,builtin=False,revision=self.revision(raw)))
            except (ValueError,OSError) as exc:warnings.append(f'{path.name}: {exc}')
        return found,warnings

    @staticmethod
    def revision(raw):return hashlib.sha256(encode(raw)).hexdigest()

    def save(self,raw,expected=None):
        raw=manifest(raw);key=raw['id'];data=encode(raw)
        if key in BUILTINS:raise ValueError('Built-ins are read-only; use a new theme ID')
        self.root.mkdir(parents=True,exist_ok=True)
        path=self.root/(key+'.json')
        if path.exists() or path.is_symlink():
            if expected is None or self.revision(self.read(key))!=expected:
                raise ValueError('Theme already exists or changed; reload before saving')
        elif len(list(self.root.glob('*.json')))>=MAX_CUSTOM:raise ValueError('Custom theme limit reached (128)')
        fd,temp=tempfile.mkstemp(prefix='.theme-',dir=self.root)
        try:
            with os.fdopen(fd,'wb') as stream:stream.write(data)
            os.replace(temp,path)
        finally:
            if os.path.exists(temp):os.unlink(temp)
        return raw
