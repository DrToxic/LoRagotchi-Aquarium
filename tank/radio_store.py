"""Bounded local message history. Owned by the same SQLite worker as fish."""
import hashlib
import json
import time

MAX_HISTORY = 5000


class RadioHistory:
    def __init__(self, db):
        self.db = db
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS radio_messages(
              id INTEGER PRIMARY KEY AUTOINCREMENT, rx TEXT NOT NULL,
              conversation TEXT NOT NULL, fingerprint TEXT UNIQUE, body TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS radio_conversation ON radio_messages(rx,conversation,id);
        ''')
        # A previous process cannot still be awaiting an ACK; never retransmit.
        with self.db:
            for mid, body in self.db.execute('SELECT id,body FROM radio_messages').fetchall():
                record=json.loads(body)
                if record.get('status') in ('sending','pending'):
                    record['status']='unconfirmed'
                    self.db.execute('UPDATE radio_messages SET body=? WHERE id=?',(json.dumps(record),mid))

    def add(self, rx, conversation, record, incoming=False):
        item=dict(record, received=time.time())
        fingerprint = None
        if incoming:
            # Protocol delivery retries share sender timestamp/content. Receipt
            # clock/SNR/hop changes must not fabricate duplicate messages.
            content=[rx,conversation,item.get('sender_prefix'),item.get('timestamp'),
                     item.get('text_type',0),item.get('text')]
            fingerprint=hashlib.sha256(json.dumps(content,ensure_ascii=False).encode()).hexdigest()
        with self.db:
            cursor=self.db.execute('INSERT OR IGNORE INTO radio_messages(rx,conversation,fingerprint,body) VALUES(?,?,?,?)',
                                   (rx,conversation,fingerprint,json.dumps(item,ensure_ascii=False)))
            if not cursor.rowcount: return None
            mid=cursor.lastrowid
            self.db.execute('DELETE FROM radio_messages WHERE id NOT IN (SELECT id FROM radio_messages ORDER BY id DESC LIMIT ?)',(MAX_HISTORY,))
        return mid

    def update(self, mid, **changes):
        row=self.db.execute('SELECT body FROM radio_messages WHERE id=?',(mid,)).fetchone()
        if not row: return
        item=json.loads(row[0]); item.update(changes)
        with self.db: self.db.execute('UPDATE radio_messages SET body=? WHERE id=?',(json.dumps(item,ensure_ascii=False),mid))

    def messages(self, rx, conversation, before=None, limit=60):
        rows=self.db.execute('SELECT id,body FROM radio_messages WHERE rx=? AND conversation=? AND id<? ORDER BY id DESC LIMIT ?',
                             (rx,conversation,before or 2**63-1,min(100,limit))).fetchall()
        return [dict(json.loads(body),id=mid) for mid,body in reversed(rows)]

    def conversations(self, rx):
        return [row[0] for row in self.db.execute('SELECT conversation FROM radio_messages WHERE rx=? GROUP BY conversation ORDER BY MAX(id) DESC',(rx,))]

    def last_timestamp(self, rx):
        latest=0
        for row in self.db.execute('SELECT body FROM radio_messages WHERE rx=?',(rx,)):
            item=json.loads(row[0])
            if item.get('direction')=='out':latest=max(latest,int(item.get('timestamp',0)))
        return latest
