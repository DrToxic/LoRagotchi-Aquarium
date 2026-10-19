"""SQLite is committed before RX ACK. A radio RETURN never removes a copy."""
from dataclasses import asdict
import json
import sqlite3
from .protocol import Snapshot, ReturnStatus, ProtocolError

class Store:
    def __init__(self, path, session="community"):
        self.session = session
        self.db = sqlite3.connect(str(path))
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS events(rx TEXT,event INTEGER,kind TEXT,body TEXT,
              received TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(rx,event));
            CREATE TABLE IF NOT EXISTS fish(session TEXT,owner TEXT,rx TEXT,event INTEGER,body TEXT,
              updated TEXT DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(session,owner));
            CREATE TABLE IF NOT EXISTS returns(rx TEXT,snapshot INTEGER,status TEXT,attempts INTEGER,
              PRIMARY KEY(rx,snapshot));
            CREATE TABLE IF NOT EXISTS hidden(session TEXT,owner TEXT,PRIMARY KEY(session,owner));
        """)

    def save(self, event):
        body = json.dumps(asdict(event), sort_keys=True)
        with self.db:
            old = self.db.execute("SELECT body FROM events WHERE rx=? AND event=?", (event.rx, event.event_id)).fetchone()
            if old:
                if old[0] != body:
                    raise ProtocolError("RX reused an event ID with different contents; not acknowledged")
                return False
            self.db.execute("INSERT INTO events(rx,event,kind,body) VALUES(?,?,?,?)", (event.rx,event.event_id,event.kind,body))
            if isinstance(event, Snapshot):
                previous = self.db.execute("SELECT body FROM fish WHERE session=? AND owner=?", (self.session,event.owner)).fetchone()
                appearance = asdict(event)
                if previous:
                    prev = json.loads(previous[0])
                    # Preserve known genes on incomplete re-share, without claiming they're fresh.
                    if not event.appearance:
                        for field in ("mode","body","scales","eyes","tint"):
                            appearance[field] = prev[field]
                    # RX replay must never roll a newer share backwards.
                    if prev["rx"] == event.rx and prev["event_id"] > event.event_id:
                        return False
                self.db.execute("INSERT INTO fish(session,owner,rx,event,body) VALUES(?,?,?,?,?) "
                    "ON CONFLICT(session,owner) DO UPDATE SET rx=excluded.rx,event=excluded.event,body=excluded.body,updated=CURRENT_TIMESTAMP",
                    (self.session,event.owner,event.rx,event.event_id,json.dumps(appearance)))
                self.db.execute("DELETE FROM hidden WHERE session=? AND owner=?", (self.session,event.owner))
            elif isinstance(event, ReturnStatus):
                self.db.execute("INSERT INTO returns VALUES(?,?,?,?) ON CONFLICT(rx,snapshot) DO UPDATE SET status=excluded.status,attempts=excluded.attempts",
                                (event.rx,event.snapshot_id,event.status,event.attempts))
        return True

    def roster(self):
        rows=self.db.execute("SELECT body FROM fish WHERE session=? AND owner NOT IN (SELECT owner FROM hidden WHERE session=?) ORDER BY owner",(self.session,self.session))
        return [Snapshot(**json.loads(row[0])) for row in rows]

    def remove(self, owner):
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO hidden VALUES(?,?)",(self.session,owner))

    def end_session(self):
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO hidden SELECT session,owner FROM fish WHERE session=?",(self.session,))

    def close(self):
        self.db.close()
