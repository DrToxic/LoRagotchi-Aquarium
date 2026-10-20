"""Single-worker MeshCore session multiplexed with the durable LRX client.

Every request finishes before another is sent. Long refreshes are split into
steps by Service so fish polling/lease renewal continues between channel reads.
"""
from collections import OrderedDict, deque
import struct
import time
from . import meshcore_protocol as wire
from .protocol import ProtocolError
from .radio_store import RadioHistory


class RadioSession:
    def __init__(self, client, emit, *, network=False, cancel=lambda: False):
        self.client, self.transport, self.emit, self.cancel = client, client.transport, emit, cancel
        self.history=RadioHistory(client.store.db)
        self.network=network
        self.writable=not network
        self.supported=bool(getattr(self.transport,'supports_mesh_messages',True))
        self.info={}; self.device={}; self.contacts={}; self.channels={}; self.discovered={}
        self.pending={}; self.early_acks=OrderedDict(); self.last_timestamp=self.history.last_timestamp(client.rx)
        self.tasks=deque(); self.loaded=False; self.loading=False
        self.active_conversation=None; self.before=None
        client.radio=self
        self.publish()

    def publish(self):
        # Copy snapshots across the worker/render boundary; never share mutable
        # contact dictionaries or channel secrets with DirectGUI.
        self.emit(dict(kind='radio_state',rx=self.client.rx,supported=self.supported,
                       writable=self.writable,loaded=self.loaded,loading=self.loading,
                       info=dict(self.info),device=dict(self.device),
                       contacts=[{k:v for k,v in c.items() if k!='raw'} for c in self.contacts.values()],
                       discovered=[{k:v for k,v in c.items() if k!='raw'} for c in self.discovered.values()],
                       channels=[dict(c) for c in self.channels.values()],
                       conversations=self.history.conversations(self.client.rx)))

    def notice(self, text): self.emit(dict(kind='radio_notice',text=text))

    def request(self, payload, expected=(0,), *, write=False, collect=False):
        if self.cancel(): raise ConnectionAbortedError('Radio operation cancelled')
        if not self.supported: raise ValueError('MeshCore client features need BLE MTU 179 or greater. USB is supported.')
        if write and not self.writable: raise ValueError('Bridge is read-only. Start it with --radio-control to enable writes.')
        if len(payload)>getattr(self.transport,'max_payload',176): raise ValueError('Command exceeds negotiated Bluetooth MTU. Use USB.')
        self.transport.send(payload)
        deadline=time.monotonic()+(8 if collect else 4)
        records=[]
        while time.monotonic()<deadline:
            if self.cancel(): raise ConnectionAbortedError('Radio operation cancelled')
            packet=self.transport.receive(max(.1,deadline-time.monotonic()))
            if not packet: continue
            if packet[0] in (1,15):
                detail=wire.ERRORS.get(packet[1] if len(packet)>1 else 0,'command disabled')
                raise wire.RadioRejected(f'Radio rejected operation: {detail}.')
            if collect and packet[0] in (2,3):
                if packet[0]==3:
                    records.append(wire.contact(packet))
                    if len(records)>510: raise ProtocolError('Contact list exceeds supported capacity')
                elif len(packet)!=5 or int.from_bytes(packet[1:],'little')>510:
                    raise ProtocolError('Invalid contact-list header')
                continue
            if packet[0] in expected: return records if collect else packet
            self.client._ordinary(packet)
        raise TimeoutError('Radio command timed out; result may be unknown. No automatic resend.')

    def schedule_refresh(self):
        if not self.supported: raise ValueError('MeshCore client features need BLE MTU 179 or greater. Use USB.')
        if self.loading: return
        self.loading=True
        self.tasks=deque(['bridge'] if self.network else [])
        self.tasks.extend(['device','self','contacts','battery','clock','finish'])
        self.publish()

    def step(self):
        self.expire()
        if not self.tasks: return
        task=self.tasks.popleft()
        try:
            if task=='bridge':
                result=self.request(wire.BRIDGE_CAPS,(0x70,))
                if result[:4]!=wire.BRIDGE_CAPS or len(result)!=5: raise ProtocolError('Update the LAN bridge for Radio tabs.')
                self.writable=bool(result[4])
            elif task=='device':
                self.device=wire.device_info(self.request(b'\x16\x0e',(13,)))
                for index in range(self.device['max_channels']):
                    self.tasks.insert(len(self.tasks)-1,('channel',index))
            elif task=='self':
                self.info=wire.self_info(self.request(b'\x01'+bytes(7)+b'Aquarium',(5,)))
                if self.info['key']!=self.client.rx: raise ProtocolError('Companion identity differs from RX identity')
            elif task=='contacts': self.refresh_contacts()
            elif task=='battery':
                packet=self.request(b'\x14',(12,))
                if len(packet) not in (3,11): raise ProtocolError('Invalid battery response')
                self.info['battery_mv']=struct.unpack_from('<H',packet,1)[0]
                if len(packet)==11:
                    self.info['storage_used_kb'],self.info['storage_total_kb']=struct.unpack_from('<II',packet,3)
            elif task=='clock':
                packet=self.request(b'\x05',(9,))
                if len(packet)!=5: raise ProtocolError('Invalid clock response')
                self.info['clock']=int.from_bytes(packet[1:],'little')
            elif isinstance(task,tuple) and task[0]=='channel':
                self.cache_channel(self.request(bytes([31,task[1]]),(18,)))
            elif isinstance(task,tuple) and task[0]=='contact':
                item=wire.contact(self.request(b'\x1e'+wire.public_key(task[1]),(3,)))
                self.contacts[item['key']]=item
            elif isinstance(task,tuple) and task[0]=='stats':
                values=wire.stats(self.request(bytes([56,task[1]]),(24,)))
                self.notice(' · '.join(f'{key}: {value}' for key,value in values.items()))
            elif task=='finish': self.loading=False; self.loaded=True; self.notice('Radio synchronized. Aquarium reception remains active.')
            self.publish()
        except wire.RadioRejected as exc:
            self.notice(str(exc))
            if task in ('bridge','device'):
                self.tasks.clear();self.loading=False
                self.notice('Radio setup unavailable. Update the bridge/firmware, then Refresh.')
            self.publish()

    def refresh_contacts(self):
        records=self.request(b'\x04',(4,),collect=True)
        self.contacts={c['key']:c for c in records}
        for key in self.contacts: self.discovered.pop(key,None)

    def cache_channel(self, packet):
        item=wire.channel(packet)
        self.channels[item['index']]=item
        self.client.channel_names[item['index']]=(item['name'],time.monotonic()+30)

    def conversation_channel(self, index):
        item=self.channels.get(int(index))
        if not item or not item['occupied']: raise ValueError('Refresh and choose a configured channel.')
        return f"channel:{item['index']}:{item['identity']}"

    def peer(self, key):
        wire.public_key(key)
        if key not in self.contacts: raise ValueError('Refresh and select a saved contact first.')
        matches=[k for k in self.contacts if k.startswith(key[:12])]
        if len(matches)!=1: raise ValueError('Ambiguous 6-byte contact prefix; sending is disabled.')
        return self.contacts[key]

    def incoming(self, message):
        if message.get('channel_index') is not None:
            index=message['channel_index']
            if index not in self.channels: return  # fail closed until metadata is verified
            conversation=self.conversation_channel(index)
        else: conversation='dm:'+message['sender_prefix']
        record=dict(message,direction='in',status='received')
        mid=self.history.add(self.client.rx,conversation,record,incoming=True)
        if mid:
            self.emit(dict(kind='radio_message',conversation=conversation,message=dict(record,id=mid)))
            if conversation==self.active_conversation and self.before is None:self.show_history(conversation)

    def show_history(self, conversation, before=None):
        if not isinstance(conversation,str) or len(conversation)>100: raise ValueError('Invalid conversation.')
        self.active_conversation,self.before=conversation,before
        self.emit(dict(kind='radio_history',conversation=conversation,
                       messages=self.history.messages(self.client.rx,conversation,before),before=before))

    def push(self, packet):
        if not packet or packet[0]<128:return False
        code=packet[0]
        if code==0x82 and len(packet)==9:
            ack=packet[1:5].hex()
            self.early_acks[ack]=time.monotonic()
            while len(self.early_acks)>128:self.early_acks.popitem(last=False)
            for mid,item in list(self.pending.items()):
                if item['ack']==ack:self.complete(mid,'delivered')
        elif code==0x8a:
            item=wire.contact(packet)
            self.discovered[item['key']]=item
            while len(self.discovered)>100:self.discovered.pop(next(iter(self.discovered)))
            self.publish()
        elif code in (0x80,0x81) and len(packet)==33:
            task=('contact',packet[1:].hex())
            if task not in self.tasks and len(self.tasks)<300:self.tasks.append(task)
        elif code==0x8f and len(packet)==33:
            self.contacts.pop(packet[1:].hex(),None);self.publish()
        elif code==0x90:self.notice('Radio contact table is full. Remove a contact to make room.')
        elif code in (0x85,0x86) and len(packet)>=8:
            self.notice(f"{packet[2:8].hex()}: remote login {'accepted' if code==0x85 else 'rejected'}.")
        elif code==0x87:
            try:self.notice(f'{packet[2:8].hex()}: '+wire.remote_status(packet))
            except ProtocolError as exc:self.notice(str(exc))
        elif code==0x8b and len(packet)>=8:
            try:self.notice(f'{packet[2:8].hex()}: '+wire.telemetry(packet[8:]))
            except (ProtocolError,ValueError,BufferError) as exc:self.notice(f'Telemetry not decoded: {exc}')
        elif code==0x8d and len(packet)>=10:
            self.notice(f'{packet[2:8].hex()}: route discovery response received. Refresh contacts for the learned path.')
        return True

    def complete(self, mid, status):
        item=self.pending.pop(mid)
        self.history.update(mid,status=status)
        self.emit(dict(kind='radio_delivery',id=mid,status=status,conversation=item['conversation']))
        if self.active_conversation==item['conversation'] and self.before is None:self.show_history(self.active_conversation)

    def expire(self):
        now=time.monotonic()
        for mid,item in list(self.pending.items()):
            if now>=item['deadline']:self.complete(mid,'unconfirmed')

    def close(self):
        for mid in list(self.pending):self.complete(mid,'unconfirmed')

    def send_message(self, route, target, text, cli=False):
        if not self.loaded: raise ValueError('Wait for Radio synchronization before sending.')
        if len(self.pending)>=32: raise ValueError('Wait for pending direct messages before sending more.')
        timestamp=max(int(time.time()),self.last_timestamp+1)
        if route=='channel':
            index=int(target);conversation=self.conversation_channel(index)
            # Group messages include the sender's node name on air (160 bytes).
            limit=158-len(self.info.get('name','').encode('utf-8'))
            raw=wire.text_bytes(text,limit,'Message')
            payload=bytes([3,0,index])+struct.pack('<I',timestamp)+raw
            expected=(0,)
        else:
            item=self.peer(target);conversation='dm:'+target[:12]
            raw=wire.text_bytes(text,160,'Message')
            txt_type=(3 if item['type']==1 else 1) if cli else 0
            payload=bytes([2,txt_type,0])+struct.pack('<I',timestamp)+wire.public_key(target)[:6]+raw
            expected=(6,)
        if not self.writable: raise ValueError('Bridge is read-only; enable --radio-control on the bridge.')
        if len(payload)>getattr(self.transport,'max_payload',176):raise ValueError('Message exceeds Bluetooth MTU. Shorten it or use USB.')
        record=dict(direction='out',text=text,timestamp=timestamp,status='sending',target=str(target),text_type=1 if cli else 0)
        mid=self.history.add(self.client.rx,conversation,record)
        self.last_timestamp=timestamp
        started=time.monotonic()
        try: result=self.request(payload,expected,write=True)
        except wire.RadioRejected:
            self.history.update(mid,status='failed');self.show_history(conversation);raise
        except Exception:
            self.history.update(mid,status='unconfirmed');self.show_history(conversation);raise
        if route=='channel' or cli:
            # Companion OK confirms enqueue, not RF reception by everyone.
            self.history.update(mid,status='sent' if route=='channel' else 'command sent')
        else:
            if len(result)!=10:
                self.history.update(mid,status='unconfirmed')
                raise ProtocolError('Invalid message acknowledgement')
            ack=result[2:6].hex();timeout=int.from_bytes(result[6:10],'little')/1000
            self.history.update(mid,status='pending')
            self.pending[mid]=dict(ack=ack,conversation=conversation,deadline=time.monotonic()+max(5,min(timeout+5,300)))
            if self.early_acks.get(ack,0)>=started:self.complete(mid,'delivered')
        self.show_history(conversation)
        self.publish()
        return 'Message accepted by radio.'

    def execute(self, action, data):
        if action=='refresh':self.schedule_refresh();return 'Reading radio…'
        if action=='history':self.show_history(data['conversation'],data.get('before'));return ''
        if action=='send':return self.send_message(data['route'],data['target'],data['text'])
        if not self.loaded:raise ValueError('Wait for Radio synchronization first.')
        if action=='contacts':self.refresh_contacts()
        elif action=='save_contact':
            item=self.contacts.get(data['key']) or self.discovered.get(data['key'])
            if not item:raise ValueError('Contact is no longer available. Refresh contacts.')
            payload=wire.contact_update(item,name=data.get('name'),flags=data.get('flags'),
                                        path=data.get('path'),path_width=data.get('path_width',1))
            self.request(payload,write=True);self.tasks.append('contacts')
        elif action in ('remove_contact','reset_path','share_contact','export_contact'):
            key=wire.public_key(data['key'])
            code={'remove_contact':15,'reset_path':13,'share_contact':16,'export_contact':17}[action]
            result=self.request(bytes([code])+key,(11,) if code==17 else (0,),write=code!=17)
            if code==17:
                self.emit(dict(kind='radio_export',text='meshcore://'+result[1:].hex()))
            else:self.tasks.append('contacts')
        elif action=='import_contact':
            uri=data['uri'].strip()
            if uri.startswith('meshcore://'):uri=uri[11:]
            try:raw=bytes.fromhex(uri)
            except ValueError:raise ValueError('Paste a MeshCore contact URL or advertisement hex.') from None
            if not 98<=len(raw)<=175:raise ValueError('Invalid contact advertisement size.')
            self.request(b'\x12'+raw,write=True);self.tasks.append('contacts')
        elif action in ('channel','clear_channel'):
            index=int(data['index'])
            if not 0<=index<self.device['max_channels']:raise ValueError('Channel slot is out of range.')
            self.request(wire.set_channel(index,data.get('name',''),data.get('secret',''),action=='clear_channel'),write=True)
            self.client.channel_names.pop(index,None);self.tasks.append(('channel',index))
        elif action=='name':
            self.request(b'\x08'+wire.text_bytes(data['name'],31,'Node name'),write=True);self.tasks.append('self')
        elif action=='radio':
            self.request(wire.radio_params(data['frequency'],data['bandwidth'],data['sf'],data['cr'],self.device.get('repeat',False)),write=True)
            self.tasks.append('self')
        elif action=='power':
            power=int(data['power'])
            if not -9<=power<=self.info['max_power']:raise ValueError(f"Power must be -9–{self.info['max_power']} dBm.")
            self.request(b'\x0c'+struct.pack('<b',power),write=True);self.tasks.append('self')
        elif action=='location':
            self.request(wire.coordinates(data['lat'],data['lon']),write=True);self.tasks.append('self')
        elif action=='preferences':
            manual=int(data['manual_add']);policy=int(data['location_policy'])
            if manual not in (0,1) or policy not in (0,1,2):raise ValueError('Invalid radio preference.')
            self.request(bytes([38,manual,self.info['telemetry'],policy,self.info['multi_acks']]),write=True)
            self.tasks.append('self')
        elif action=='clock':
            self.request(b'\x06'+struct.pack('<I',int(time.time())),write=True);self.tasks.append('clock')
        elif action=='advert':self.request(bytes([7,int(bool(data.get('flood')))]),write=True)
        elif action=='stats':
            for typ in range(3):self.tasks.append(('stats',typ))
        elif action in ('login','logout','status','telemetry','discover_path','command'):
            item=self.peer(data['key']);key=wire.public_key(item['key'])
            if action=='command':return self.send_message('direct',item['key'],data['text'],cli=True)
            payload={'logout':b'\x1d'+key,'status':b'\x1b'+key,
                     'telemetry':b'\x27'+bytes(3)+key,'discover_path':b'\x34\0'+key}.get(action)
            if action=='login':payload=b'\x1a'+key+wire.text_bytes(data.get('password',''),63,'Password',empty=True)
            self.request(payload,(0,) if action=='logout' else (6,),write=True)
            self.publish();return 'Request sent; remote response will appear in Activity.'
        else:raise ValueError('Unknown radio operation.')
        self.publish()
        return 'Radio operation completed.'
