"""Radio, discovery and SQLite I/O stay on one worker, never the render loop."""
import contextlib
import json
from pathlib import Path
import queue
import threading
import time
from collections import deque
from .client import Client
from .connection import ConnectionProfile, discover, live_database
from .demo import events
from .protocol import decode_event, ProtocolError
from .store import Store
from .transport import open_transport
from .radio import RadioSession


class Service:
    def __init__(self, args):
        self.args = args
        self.events = queue.Queue(); self.commands = queue.Queue(); self.stop = threading.Event()
        self.generation = 0
        self.radio_sequence = 0
        self.thread = threading.Thread(target=self.run, daemon=True, name='rx-storage')
        self.thread.start()

    def notify(self, event): self.events.put(event)

    def connect(self, profile):
        profile.uri()  # Cheap validation only; no I/O on caller's thread.
        self.generation += 1
        self.commands.put(('connect', self.generation, profile))

    def disconnect(self):
        self.generation += 1
        self.commands.put(('disconnect', self.generation))

    def radio_request(self, action, **data):
        if self.commands.qsize() >= 32: raise ValueError('Radio queue is busy. Wait for pending operations.')
        self.radio_sequence += 1
        self.commands.put(('radio',self.generation,self.radio_sequence,action,data))
        return self.radio_sequence

    def status(self, state, text, **extra):
        self.notify(dict(kind='connection', state=state, text=text, **extra))

    def run(self):
        store = client = target = token = None
        generation = 0
        radio_jobs=deque()
        last_history=last_rx=None
        mode = 'demo' if self.args.demo is not None else 'replay' if self.args.replay else 'live'

        def roster(): self.notify({'kind': 'roster', 'fish': store.roster(), 'mode': mode})

        def close_client(graceful=True):
            nonlocal client
            if client is not None:
                with contextlib.suppress(Exception):
                    if client.radio is not None: client.radio.close()
                with contextlib.suppress(Exception):
                    client.close() if graceful else client.transport.close()
                client = None

        try:
            store = Store(self.args.database, self.args.session)
            if mode == 'demo':
                for event in events(self.args.demo): store.save(event)
                self.status('idle', 'DEMO · synthetic visitors · no radio')
            elif mode == 'replay':
                with open(self.args.replay, encoding='utf-8') as source:
                    for line in source:
                        record = json.loads(line)
                        store.save(decode_event(record['rx'], bytes.fromhex(record['payload'])))
                self.status('idle', 'REPLAY · recorded snapshots · no radio')
            else: self.status('idle', 'Radio disconnected · saved copies remain')
            roster()
            if self.args.connect:
                try: self.connect(ConnectionProfile.from_uri(self.args.connect, self.args.token_file))
                except ValueError as exc: self.status('error', str(exc))
            reconnect = next_mesh = 0
            while not self.stop.is_set():
                while not self.commands.empty() and not self.stop.is_set():
                    command = self.commands.get_nowait()
                    if command[0] == 'remove': store.remove(command[1]); roster()
                    elif command[0] == 'clear': store.end_session(); roster()
                    elif command[0] == 'radio':
                        if command[1]==self.generation and not client and last_history and command[3]=='history':
                            data=command[4];conversation=data.get('conversation','')
                            if not isinstance(conversation,str) or len(conversation)>100:
                                self.notify(dict(kind='radio_result',id=command[2],ok=False,text='Invalid conversation.'))
                            else:
                                self.notify(dict(kind='radio_history',conversation=conversation,before=data.get('before'),
                                                 messages=last_history.messages(last_rx,conversation,data.get('before'))))
                                self.notify(dict(kind='radio_result',id=command[2],ok=True,text=''))
                        elif command[1]!=self.generation or not client or len(radio_jobs)>=32:
                            self.notify(dict(kind='radio_result',id=command[2],ok=False,text='Radio is disconnected or busy; action was not sent.'))
                        else:radio_jobs.append(command)
                    elif command[0] == 'scan':
                        kind = command[1]
                        if target or client:
                            self.notify(dict(kind='devices', transport=kind, devices=[], error='Disconnect before scanning.'))
                            continue
                        try: self.notify(dict(kind='devices', transport=kind, devices=discover(kind)))
                        except Exception as exc:
                            self.notify(dict(kind='devices', transport=kind, devices=[], error=f'Discovery unavailable: {exc}'))
                    elif command[0] in ('connect', 'disconnect'):
                        # Superseded clicks cannot start another connection.
                        if command[1] != self.generation: continue
                        generation = command[1]
                        while radio_jobs:
                            old=radio_jobs.popleft()
                            self.notify(dict(kind='radio_result',id=old[2],ok=False,text='Connection changed; action was not sent.'))
                        if command[0] == 'disconnect':
                            target = None; close_client()
                            self.status('idle', 'Radio disconnected · displayed copies remain')
                            continue
                        profile = command[2]
                        try:
                            uri = profile.uri(); new_token = profile.token()
                            new_store = None
                            if mode != 'live':
                                path = Path(getattr(self.args, 'live_database', None) or live_database())
                                if str(path) == ':memory:' or path.resolve() == Path(self.args.database).resolve():
                                    raise ValueError('Live storage must be separate from the demo/replay database.')
                                path.parent.mkdir(parents=True, exist_ok=True)
                                new_store = Store(path, self.args.session)
                        except Exception as exc:
                            self.status('connected' if client else 'error', f'Connection settings: {exc}')
                            continue
                        close_client()
                        if new_store is not None:
                            store.close(); store = new_store; mode = 'live'; roster()
                        target = uri; token = new_token; reconnect = next_mesh = 0
                        try: profile.save(Path(self.args.settings).with_name('rx-connection.json'))
                        except OSError: self.notify(dict(kind='notice', text='Connection details could not be saved.'))
                        self.status('connecting', 'Connecting to RX…', endpoint=target)
                if self.stop.is_set(): break
                if target and generation == self.generation and time.monotonic() >= reconnect:
                    try:
                        if client is None:
                            self.status('connecting', 'Connecting to RX…', endpoint=target)
                            client = Client(open_transport(target, token,
                                            cancel=lambda:self.stop.is_set() or generation!=self.generation), store, self.notify)
                            if generation != self.generation or self.stop.is_set():
                                close_client(False); continue
                            caps = client.connect()
                            if generation != self.generation or self.stop.is_set():
                                close_client(); continue
                            RadioSession(client,self.notify,network=target.startswith('tcp:'),
                                         cancel=lambda:self.stop.is_set() or generation!=self.generation)
                            last_history,last_rx=client.radio.history,client.rx
                            self.status('connected', f'RX {client.rx[:10]} · connected · {caps["capacity"]} intake slots',
                                        endpoint=target, rx=client.rx)
                        if client.poll(): roster()
                        if generation != self.generation or self.stop.is_set(): continue
                        if time.monotonic() >= next_mesh:
                            more=client.poll_messages(); next_mesh = time.monotonic()+(.1 if more else 1)
                        client.radio.expire()
                        if radio_jobs:
                            job=radio_jobs.popleft()
                            if job[1]!=self.generation:
                                self.notify(dict(kind='radio_result',id=job[2],ok=False,text='Connection changed; action was not sent.'))
                            else:
                                try:
                                    text=client.radio.execute(job[3],job[4])
                                    self.notify(dict(kind='radio_result',id=job[2],ok=True,text=text))
                                except ProtocolError:
                                    self.notify(dict(kind='radio_result',id=job[2],ok=False,text='Invalid radio response; reconnecting without resending.'))
                                    raise
                                except ValueError as exc:
                                    self.notify(dict(kind='radio_result',id=job[2],ok=False,text=str(exc)))
                                except Exception:
                                    self.notify(dict(kind='radio_result',id=job[2],ok=False,text='Radio interrupted; result may be unknown. Nothing will be resent automatically.'))
                                    raise
                        elif generation==self.generation:client.radio.step()
                    except Exception as exc:
                        while radio_jobs:
                            old=radio_jobs.popleft()
                            self.notify(dict(kind='radio_result',id=old[2],ok=False,text='Connection lost; queued action was not sent.'))
                        close_client(False)
                        if generation == self.generation and not self.stop.is_set():
                            self.status('retrying', f'Radio offline · {type(exc).__name__}: {str(exc)[:180]} · retrying in 3s')
                        reconnect = time.monotonic()+3
                self.stop.wait(.1)
        except Exception as exc:
            self.status('fatal', f'Storage/replay error: {exc}. Resolve it and restart the aquarium.')
        finally:
            close_client()
            if store is not None: store.close()

    def close(self):
        self.generation += 1; self.stop.set(); self.thread.join(6)
