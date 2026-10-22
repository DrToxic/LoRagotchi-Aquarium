"""Local-only eggs with immutable parents; never a firmware or visit authority.

All SQLite access happens on NurseryWorker. No transport exists in this module;
claiming an egg is deliberately unsupported until a versioned DX handshake exists.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import queue
import random
import sqlite3
import threading
import time
import uuid


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


def validate_parent(value):
    from .protocol import Snapshot
    p=asdict(value) if isinstance(value,Snapshot) else dict(value)
    # Reuse the wire codec's bounds without sending anything.
    from .protocol import encode_event, decode_event
    decode_event(p['rx'],encode_event(Snapshot(**p)))
    if len(p['owner'])!=64 or len(bytes.fromhex(p['owner']))!=32 or p['stage']<2:
        raise ValueError('Choose two adult or elder fish')
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
    def __init__(self,path,scope):
        if str(path)!=':memory:':Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(str(path),timeout=5)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS eggs (scope TEXT NOT NULL, id TEXT PRIMARY KEY, created REAL NOT NULL, parents TEXT NOT NULL, preview TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS nursery_cooldowns (scope TEXT NOT NULL, parent TEXT NOT NULL, until REAL NOT NULL, PRIMARY KEY(scope,parent))')
        self.db.commit();self.scope=scope

    def eggs(self):
        return [dict(id=i,created=t,parents=json.loads(p),preview=json.loads(v),state='stored-local')
                for i,t,p,v in self.db.execute('SELECT id,created,parents,preview FROM eggs WHERE scope=? ORDER BY created,id',(self.scope,))]

    def create(self,a,b,settings,now=None,egg_id=None):
        a,b=validate_parent(a),validate_parent(b)
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
            existing=self.db.execute('SELECT scope,parents FROM eggs WHERE id=?',(ident,)).fetchone()
            if existing:
                if existing!=(self.scope,json.dumps(parents,sort_keys=True)):
                    raise ValueError('Egg request ID belongs to different parents')
                self.db.commit();return ident
            count=self.db.execute('SELECT count(*) FROM eggs WHERE scope=?',(self.scope,)).fetchone()[0]
            if count>=settings.capacity:raise ValueError('Nursery is full; existing eggs are retained')
            for key in keys:
                row=self.db.execute('SELECT until FROM nursery_cooldowns WHERE scope=? AND parent=?',(self.scope,key)).fetchone()
                if row and row[0]>now:raise ValueError('A parent is resting after breeding')
            preview=preview_colour(*parents,ident)
            self.db.execute('INSERT INTO eggs VALUES(?,?,?,?,?)',(self.scope,ident,now,json.dumps(parents,sort_keys=True),json.dumps(preview)))
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
        store=None
        try:
            while not self.stop.is_set():
                try:action,data=self.commands.get(timeout=.2)
                except queue.Empty:continue
                try:
                    if action=='open':
                        if store:store.close()
                        mode=data['mode']
                        # Synthetic modes never load or write the live nursery.
                        base=Path(self.args.settings).parent
                        path=base/('nursery-live.sqlite3' if mode=='live' else 'nursery-'+mode+'.sqlite3')
                        if mode!='live' and str(self.args.database)==':memory:':path=':memory:'
                        scope=str(getattr(self.args,'session','community'))
                        store=NurseryStore(path,scope)
                    elif action=='create' and store:
                        store.create(data['a'],data['b'],NurserySettings.from_dict(data['settings']),egg_id=data['id'])
                    else:continue
                    self.events.put(dict(kind='nursery',eggs=store.eggs(),text='Local nursery · DX transfer not connected'))
                except (ValueError,OSError,sqlite3.Error,TypeError,KeyError) as exc:
                    self.events.put(dict(kind='nursery',text=str(exc),error=True))
        finally:
            if store:store.close()

    def close(self):
        self.stop.set();self.thread.join(6)
