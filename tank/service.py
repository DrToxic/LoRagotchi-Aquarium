"""All radio and database I/O is owned by this worker, never the rendering loop."""
from dataclasses import asdict
import json
import contextlib
from pathlib import Path
import queue
import threading
import time
from .client import Client
from .demo import events
from .protocol import decode_event
from .store import Store
from .transport import open_transport

class Service:
    def __init__(self,args):
        self.args=args;self.events=queue.Queue();self.commands=queue.Queue();self.stop=threading.Event()
        self.thread=threading.Thread(target=self.run,daemon=True,name="rx-storage")
        self.thread.start()
    def notify(self,event):self.events.put(event)
    def run(self):
        store=Store(self.args.database,self.args.session)
        client=None
        try:
            if self.args.demo is not None:
                for event in events(self.args.demo):store.save(event)
                self.notify({"kind":"connection","text":"DEMO · synthetic visitors · no radio"})
            if self.args.replay:
                with open(self.args.replay,encoding="utf-8") as source:
                    for line in source:
                        record=json.loads(line)
                        store.save(decode_event(record["rx"],bytes.fromhex(record["payload"])))
                self.notify({"kind":"connection","text":"REPLAY · recorded snapshots · no radio"})
            self.notify({"kind":"roster","fish":store.roster()})
            reconnect=0;next_mesh=0
            token=Path(self.args.token_file).read_bytes() if self.args.token_file else None
            while not self.stop.is_set():
                while not self.commands.empty():
                    command=self.commands.get_nowait()
                    if command[0]=="remove":store.remove(command[1])
                    elif command[0]=="clear":store.end_session()
                    self.notify({"kind":"roster","fish":store.roster()})
                if self.args.connect and time.monotonic()>=reconnect:
                    try:
                        if client is None:
                            client=Client(open_transport(self.args.connect,token),store,self.notify)
                            caps=client.connect()
                            self.notify({"kind":"connection","text":f"RX {client.rx[:10]} · connected · {caps['capacity']} intake slots"})
                        changed=client.poll()
                        if changed:self.notify({"kind":"roster","fish":store.roster()})
                        if time.monotonic()>=next_mesh:
                            client.poll_messages();next_mesh=time.monotonic()+2
                    except Exception as exc:
                        self.notify({"kind":"connection","text":f"Radio offline · {type(exc).__name__}: {str(exc)[:100]}"})
                        if client:
                            with contextlib.suppress(Exception):client.transport.close()
                            client=None
                        reconnect=time.monotonic()+3
                self.stop.wait(.15)
        except Exception as exc:
            self.notify({"kind":"connection","text":f"Storage/replay error: {exc}"})
        finally:
            if client:client.close()
            store.close()
    def close(self):self.stop.set();self.thread.join(6)
