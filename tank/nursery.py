"""Local-only eggs with immutable parents; never a firmware or visit authority.

All SQLite access happens on NurseryWorker. No transport exists in this module;
claiming an egg is deliberately unsupported until a versioned DX handshake exists.
"""
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import queue
import random
import sqlite3
import struct
import threading
import time
import uuid
import hashlib

from .protocol import Snapshot

LOCAL_FRY_CAPACITY = 64


@dataclass(frozen=True)
class LocalFry(Snapshot):
    # Not a radio snapshot or a DX-owned pet. No birth/age clock exists.
    kind: str = "local_fry"
    generation: int = 1
    lifetime_hours: int = 0
    local_body_rgb: tuple = ()


def local_fry(value):
    value=dict(value);value["local_body_rgb"]=tuple(value["local_body_rgb"])
    return LocalFry(**value)


@dataclass
class NurserySettings:
    enabled: bool = False
    automatic: bool = False
    capacity: int = 6
    cooldown_minutes: int = 30

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value,dict) or value.keys()-{'enabled','automatic','capacity','cooldown_minutes'}:
            raise ValueError('Unknown nursery setting')
        result=cls(**value)
        if type(result.enabled) is not bool or type(result.automatic) is not bool:
            raise ValueError('Nursery switches must be true or false')
        if type(result.capacity) is not int or not 1<=result.capacity<=12:
            raise ValueError('Nursery capacity must be 1..12')
        if type(result.cooldown_minutes) is not int or not 1<=result.cooldown_minutes<=1440:
            raise ValueError('Breeding cooldown must be 1..1440 minutes')
        return result


def parent_key(parent):
    return f"{parent['owner']}:{parent['fish_id']}"


def eligible_parent(value):
    """Only received adult/elder stages; snapshots carry no age or generation."""
    stage=value.get('stage') if isinstance(value,dict) else getattr(value,'stage',None)
    kind=value.get('kind') if isinstance(value,dict) else getattr(value,'kind',None)
    return kind!='local_fry' and type(stage) is int and stage in (2,3)


def synthetic_parent(value):
    from .demo import RX, SYNTHETIC_OWNERS
    p=value if isinstance(value,dict) else asdict(value)
    return str(p.get('rx','')).lower()==RX or str(p.get('owner','')).lower() in SYNTHETIC_OWNERS


def validate_parent(value):
    from .protocol import Snapshot
    p=asdict(value) if isinstance(value,Snapshot) else dict(value)
    if p.get('kind')=='local_fry' or not eligible_parent(p):raise ValueError('Choose two adult or elder fish')
    # Reuse the wire codec's bounds without sending anything.
    from .protocol import encode_event, decode_event
    try:decode_event(p['rx'],encode_event(Snapshot(**p)))
    except (TypeError,struct.error,OverflowError) as exc:
        raise ValueError('Invalid parent snapshot') from exc
    if len(p['owner'])!=64 or len(bytes.fromhex(p['owner']))!=32:
        raise ValueError('Invalid full parent identity')
    p['owner']=bytes.fromhex(p['owner']).hex()
    p['rx']=bytes.fromhex(p['rx']).hex()
    return p


def preview_colour(a,b,seed):
    # Local preview only: linear-light sRGB interpolation, not a promised DX
    # genome. Preserve the samples/rule so a future contract cannot reroll eggs.
    palette=((.98,.32,.27),(1.,.56,.15),(.98,.81,.24),(.32,.84,.61),(.12,.64,.83),(.71,.43,.89))
    def rgb(p):
        t=p['tint']
        return palette[p['body']] if p['body']<6 else ((t>>11)/31,((t>>5)&63)/63,(t&31)/31)
    def linear(v):return v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4
    def srgb(v):return 12.92*v if v<=.0031308 else 1.055*v**(1/2.4)-.055
    fraction=random.Random(seed).random()
    colour=[srgb(linear(x)*(1-fraction)+linear(y)*fraction) for x,y in zip(rgb(a),rgb(b))]
    return dict(rule='local-linear-srgb-v1',fraction=fraction,body_rgb=colour,
                firmware_genome=None)


class NurseryStore:
    def __init__(self,path,scope,mode='live'):
        if mode not in ('live','demo','replay'):raise ValueError('Invalid nursery mode')
        if str(path)!=':memory:':Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(str(path),timeout=5)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS eggs (scope TEXT NOT NULL, id TEXT PRIMARY KEY, created REAL NOT NULL, parents TEXT NOT NULL, preview TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS nursery_cooldowns (scope TEXT NOT NULL, parent TEXT NOT NULL, until REAL NOT NULL, PRIMARY KEY(scope,parent))')
        # Separate additive ledger: even legacy five-column egg inserts remain
        # compatible. Never change old IDs, parents, previews or cooldowns.
        self.db.execute('CREATE TABLE IF NOT EXISTS nursery_lineage (egg TEXT PRIMARY KEY, metadata TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS nursery_fry (collection TEXT NOT NULL, egg TEXT PRIMARY KEY, snapshot TEXT NOT NULL, created REAL NOT NULL, deleted INTEGER NOT NULL DEFAULT 0)')
        self.db.execute('CREATE TABLE IF NOT EXISTS nursery_imports (source TEXT PRIMARY KEY)')
        self.db.execute('CREATE TABLE IF NOT EXISTS nursery_hatched_eggs (scope TEXT NOT NULL, id TEXT PRIMARY KEY, created REAL NOT NULL, parents TEXT NOT NULL, preview TEXT NOT NULL)')
        self.db.commit();self.scope=scope;self.mode=mode
        self.scopes=[scope];self.collection=scope

    def migrate(self,path,old_scope,new_scope):
        """Additive, atomic import; retain original DB and immutable payload bytes."""
        if not Path(path).exists():return
        self.db.execute('ATTACH DATABASE ? AS legacy',(str(path),))
        key=str(Path(path).resolve())+':'+old_scope+':'+new_scope
        try:
            self.db.execute('BEGIN IMMEDIATE')
            if not self.db.execute('SELECT 1 FROM nursery_imports WHERE source=?',(key,)).fetchone():
                tables={r[0] for r in self.db.execute("SELECT name FROM legacy.sqlite_master WHERE type='table'")}
                if 'eggs' in tables:
                    self.db.execute('INSERT INTO eggs SELECT ?,id,created,parents,preview FROM legacy.eggs WHERE scope=?',(new_scope,old_scope))
                if 'nursery_cooldowns' in tables:
                    self.db.execute('INSERT INTO nursery_cooldowns SELECT ?,parent,until FROM legacy.nursery_cooldowns WHERE scope=?',(new_scope,old_scope))
                if 'nursery_lineage' in tables:
                    self.db.execute('INSERT INTO nursery_lineage SELECT l.* FROM legacy.nursery_lineage l JOIN legacy.eggs e ON e.id=l.egg WHERE e.scope=?',(old_scope,))
                self.db.execute('INSERT INTO nursery_imports VALUES(?)',(key,))
            self.db.commit()
        except Exception:
            self.db.rollback();raise
        finally:self.db.execute('DETACH DATABASE legacy')

    def fish(self):
        return [json.loads(row[0]) for row in self.db.execute('SELECT snapshot FROM nursery_fry WHERE collection=? AND deleted=0 ORDER BY created,egg',(self.collection,))]

    def hatch(self,ident,now=None):
        # Ledger is also the retry receipt: deleted fry never resurrect on retry.
        self.db.execute('BEGIN IMMEDIATE')
        try:
            receipt=self.db.execute('SELECT collection FROM nursery_fry WHERE egg=?',(ident,)).fetchone()
            if receipt:
                if receipt[0]!=self.collection:raise ValueError('Egg belongs to another collection')
                self.db.commit();return ident
            placeholders=','.join('?' for _ in self.scopes)
            row=self.db.execute(f'SELECT parents,preview FROM eggs WHERE id=? AND scope IN ({placeholders})',(ident,*self.scopes)).fetchone()
            if not row:raise ValueError('Egg is no longer available; refresh the nursery')
            count=self.db.execute('SELECT count(*) FROM nursery_fry WHERE collection=? AND deleted=0',(self.collection,)).fetchone()[0]
            if count>=LOCAL_FRY_CAPACITY:raise ValueError('Local fry collection is full (64); remove a local fry first')
            parents,preview=map(json.loads,row)
            rgb=tuple(preview['body_rgb'])
            if len(rgb)!=3 or any(not math.isfinite(c) or not 0<=c<=1 for c in rgb):raise ValueError('Egg preview is invalid; egg retained')
            owner=hashlib.sha256(('aquarium-local-fry:'+uuid.uuid4().hex).encode()).hexdigest()
            f=LocalFry(rx='local-nursery',event_id=0,owner=owner,fish_id=int(ident[:8],16),tx_id=0,stage=0,mode='C',body=parents[0]['body'],scales=parents[1]['scales'],eyes=parents[0]['eyes'],tint=parents[0]['tint'],appearance=True,name='Fry '+ident[:6],local_body_rgb=rgb)
            self.db.execute('INSERT INTO nursery_fry VALUES(?,?,?,?,0)',(self.collection,ident,json.dumps(asdict(f)),time.time() if now is None else now))
            self.db.execute('INSERT INTO nursery_hatched_eggs SELECT * FROM eggs WHERE id=?',(ident,))
            self.db.execute('DELETE FROM eggs WHERE id=?',(ident,))
            self.db.commit();return ident
        except Exception:
            self.db.rollback();raise

    def remove_fry(self,owner=None):
        with self.db:
            for egg,snapshot in self.db.execute('SELECT egg,snapshot FROM nursery_fry WHERE collection=? AND deleted=0',(self.collection,)).fetchall():
                if owner is None or json.loads(snapshot)['owner']==owner:
                    self.db.execute('UPDATE nursery_fry SET deleted=1 WHERE egg=?',(egg,))

    def eggs(self):
        return [dict(id=i,created=t,parents=json.loads(p),preview=json.loads(v),state='stored-local',
                     lineage=(dict(rule='demo-ancestry-v2',ancestry_depth=1,pet_generation=1,legacy_metadata=json.loads(lineage)) if lineage and json.loads(lineage).get('rule')=='demo-founders-v1' else json.loads(lineage) if lineage else None))
                for i,t,p,v,lineage in self.db.execute('SELECT e.id,e.created,e.parents,e.preview,l.metadata FROM eggs e LEFT JOIN nursery_lineage l ON l.egg=e.id WHERE e.scope IN ('+','.join('?' for _ in self.scopes)+') ORDER BY e.created,e.id',self.scopes)]

    def create(self,a,b,settings,now=None,egg_id=None):
        a,b=validate_parent(a),validate_parent(b)
        synthetic=[synthetic_parent(p) for p in (a,b)]
        if self.mode=='live' and any(synthetic):
            raise ValueError('Demo parents cannot breed in the live nursery')
        if self.mode=='demo' and not all(synthetic):
            raise ValueError('Only demo parents can breed in the demo nursery')
        if a['owner']==b['owner']:raise ValueError('Parents must have different full owner identities')
        if not settings.enabled:raise ValueError('Enable the nursery first')
        now=time.time() if now is None else now
        if not math.isfinite(now):raise ValueError('Invalid time')
        ident=egg_id or uuid.uuid4().hex
        if len(ident)!=32 or any(c not in '0123456789abcdef' for c in ident):raise ValueError('Invalid egg identity')
        parents=sorted((a,b),key=parent_key)
        keys=[parent_key(p) for p in parents]
        # Capacity, both parental cooldowns and the stored immutable result are
        # one transaction. Concurrent workers/retries cannot overfill or reroll.
        self.db.execute('BEGIN IMMEDIATE')
        try:
            existing=self.db.execute('SELECT scope,parents FROM eggs WHERE id=? UNION ALL SELECT scope,parents FROM nursery_hatched_eggs WHERE id=?',(ident,ident)).fetchone()
            if existing:
                if existing!=(self.scope,json.dumps(parents,sort_keys=True)):
                    raise ValueError('Egg request ID belongs to different parents')
                self.db.commit();return ident
            count=len(self.eggs())
            if count>=settings.capacity:raise ValueError('Nursery is full; existing eggs are retained')
            for key in keys:
                row=self.db.execute('SELECT until FROM nursery_cooldowns WHERE scope=? AND parent=?',(self.scope,key)).fetchone()
                if row and row[0]>now:raise ValueError('A parent is resting after breeding')
            preview=preview_colour(*parents,ident)
            # Local ancestry only, never a DX/player generation or firmware genome.
            lineage=(dict(rule='demo-ancestry-v2',ancestry_depth=1,pet_generation=1)
                     if self.mode=='demo' else None)
            self.db.execute('INSERT INTO eggs VALUES(?,?,?,?,?)',
                            (self.scope,ident,now,json.dumps(parents,sort_keys=True),json.dumps(preview)))
            if lineage:
                self.db.execute('INSERT INTO nursery_lineage VALUES(?,?)',(ident,json.dumps(lineage)))
            for key in keys:
                self.db.execute('INSERT OR REPLACE INTO nursery_cooldowns VALUES(?,?,?)',(self.scope,key,now+settings.cooldown_minutes*60))
            self.db.commit();return ident
        except Exception:
            self.db.rollback();raise

    def close(self):self.db.close()


class NurseryWorker:
    def __init__(self,args):
        self.args=args
        self.events=queue.Queue();self.commands=queue.Queue(maxsize=8)
        self.stop=threading.Event()
        self.thread=threading.Thread(target=self.run,name='nursery-storage',daemon=True)
        self.thread.start()

    def submit(self,action,**values):
        try:self.commands.put_nowait((action,values));return True
        except queue.Full:return False

    def run(self):
        store=None;context=None
        try:
            while not self.stop.is_set():
                try:action,data=self.commands.get(timeout=.2)
                except queue.Empty:continue
                try:
                    if action=='close':break
                    if action=='open':
                        if store:store.close()
                        store=None;context=data.get('context')
                        mode=data['mode']
                        if mode not in ('live','demo','replay'):raise ValueError('Invalid nursery mode')
                        base=Path(self.args.settings).parent
                        scope=str(getattr(self.args,'session','community'))
                        # Shared local eggs/fry, never visitor/receiver databases.
                        path=base/('nursery-replay.sqlite3' if mode=='replay' else 'nursery-local.sqlite3')
                        store=NurseryStore(path,scope+':'+mode,mode)
                        if mode!='replay':
                            for source in ('demo','live'):
                                store.migrate(base/('nursery-'+source+'.sqlite3'),scope,scope+':'+source)
                            store.scopes=[scope+':demo',scope+':live']
                            store.collection=scope
                    elif action=='create':
                        if store is None:raise ValueError('Nursery storage is not open')
                        if data.get('context')!=context:raise ValueError('Nursery source changed; choose parents again')
                        store.create(data['a'],data['b'],NurserySettings.from_dict(data['settings']),egg_id=data['id'])
                    elif action=='refresh':
                        if store is None or data.get('context')!=context:continue
                    elif action in ('hatch','remove_fry','clear_fry'):
                        if store is None or data.get('context')!=context:raise ValueError('Nursery source changed; refresh and try again')
                        if action=='hatch':store.hatch(data['id'])
                        else:store.remove_fry(data.get('owner') if action=='remove_fry' else None)
                    elif action=='adopt':raise ValueError('DX adoption is not connected; egg retained')
                    else:continue
                    self.events.put(dict(kind='nursery',action=action,context=context,eggs=store.eggs(),fish=store.fish(),text='Local eggs / permanent Gen 1 fry · no DX transfer'))
                except (ValueError,OSError,sqlite3.Error,TypeError,KeyError) as exc:
                    if action=='open' and store:
                        store.close();store=None
                    self.events.put(dict(kind='nursery',context=data.get('context'),text=str(exc),error=True))
        finally:
            if store:store.close()

    def close(self):
        # Drain accepted mutations before shutdown; no silently lost hatch.
        if not self.thread.is_alive():return
        self.commands.put(('close',{}),timeout=6);self.thread.join(12)
