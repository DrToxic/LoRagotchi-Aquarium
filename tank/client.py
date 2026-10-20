import secrets
import struct
import time
from collections import deque
from .protocol import MAGIC, ProtocolError, channel_info, decode_event, mesh_message

class Client:
    def __init__(self,transport,store,on_event=lambda e:None,token=None):
        self.transport,self.store,self.on_event=transport,store,on_event
        self.token=token or secrets.randbits(32) or 1
        self.rx=None
        self.messages=[]
        self.channel_names={}
        self.pending_messages=deque(maxlen=100)
        self.radio=None

    def command(self,op,args=b""):
        payload=MAGIC+bytes([op])+struct.pack("<I",self.token)+args
        self.transport.send(payload)
        end=time.monotonic()+4
        while time.monotonic()<end:
            packet=self.transport.receive(max(.1,end-time.monotonic()))
            if packet.startswith(MAGIC):
                if len(packet)<6 or packet[4]!=op:raise ProtocolError("Unexpected RX response")
                if packet[5]:raise ProtocolError({1:"Invalid RX command or lease expired",2:"RX already has an active consumer",3:"RX storage not ready"}.get(packet[5],"RX error"))
                return packet[6:]
            self._ordinary(packet)
        raise TimeoutError("RX command timeout")

    def _ordinary(self,packet):
        if self.radio and self.radio.push(packet):return
        msg=mesh_message(packet)
        if msg:
            msg["rx"]=self.rx
            # Never nest a companion command inside an in-flight LRX request.
            self.pending_messages.append(msg)

    def _channel_name(self,index):
        cached=self.channel_names.get(index)
        if cached and time.monotonic()<cached[1]:return cached[0]
        self.transport.send(bytes([31,index]))  # CMD_GET_CHANNEL; no radio writes.
        end=time.monotonic()+2
        while time.monotonic()<end:
            packet=self.transport.receive(max(.1,end-time.monotonic()))
            if packet[:1]==b"\x12":
                found,name=channel_info(packet)
                if found!=index:raise ProtocolError("Mismatched channel-info response")
                if self.radio:self.radio.cache_channel(packet)
                self.channel_names[index]=(name,time.monotonic()+30)
                return name
            if packet[:1]==b"\x01":  # Unsupported/missing channel: fail closed.
                self.channel_names[index]=("",time.monotonic()+30)
                return ""
            self._ordinary(packet)
        raise TimeoutError("Channel lookup timed out")

    def _flush_messages(self):
        # Bounded drain; asynchronous messages arriving during lookups wait
        # until the next poll. The cached table belongs to this connection only.
        for _ in range(len(self.pending_messages)):
            msg=self.pending_messages.popleft()
            msg["rx"]=self.rx
            if "channel_index" in msg:
                msg["channel_name"]=self._channel_name(msg["channel_index"])
            if self.radio:self.radio.incoming(msg)
            self.messages.append(msg);self.messages=self.messages[-100:];self.on_event(msg)

    def connect(self):
        capabilities=self.command(0)
        if len(capabilities)!=4 or capabilities[2]!=10:raise ProtocolError("Unsupported LRX capabilities")
        key=bytearray()
        while len(key)<32:
            part=self.command(1,bytes([len(key)]))
            if len(part)<3 or part[0]!=len(key) or part[1]!=32:raise ProtocolError("Invalid identity fragment")
            key.extend(part[2:])
        if len(key)!=32:raise ProtocolError("Invalid RX public key")
        self.rx=key.hex();self.capabilities=dict(capacity=capabilities[0],transports=capabilities[1],storage_ok=bool(capabilities[3]))
        return self.capabilities

    def poll(self):
        summary=self.command(2)
        if len(summary)!=6:raise ProtocolError("Invalid event summary")
        event_id,size=struct.unpack("<IH",summary)
        if not event_id:return False
        if not 0<size<=80:raise ProtocolError("Event too large")
        data=bytearray()
        while len(data)<size:
            chunk=self.command(3,struct.pack("<IH",event_id,len(data)))
            if len(chunk)<5:raise ProtocolError("Empty event fragment")
            offset,total=struct.unpack_from("<HH",chunk)
            if offset!=len(data) or total!=size:raise ProtocolError("Mismatched event fragment")
            data.extend(chunk[4:])
        if len(data)!=size:raise ProtocolError("Overlong event")
        event=decode_event(self.rx,bytes(data))
        if event.event_id!=event_id:raise ProtocolError("Event ID mismatch")
        changed=self.store.save(event)  # commit (FULL synchronous) before ACK
        self.command(4,struct.pack("<I",event_id))
        if changed:self.on_event(event)
        return True

    def poll_messages(self):
        if not getattr(self.transport,"supports_mesh_messages",True):return
        # The same consumer drains ordinary chat and LRX; no second port owner.
        self.transport.send(b"\x0a")
        end=time.monotonic()+2
        while time.monotonic()<end:
            packet=self.transport.receive(max(.1,end-time.monotonic()))
            if packet[:1] in (b"\x07",b"\x08",b"\x10",b"\x11",b"\x0a"):
                self._ordinary(packet);self._flush_messages();return packet[:1]!=b'\x0a'
            self._ordinary(packet)
        raise TimeoutError("Mesh message poll timed out")

    def close(self):
        try:self.command(5)
        except Exception:pass
        self.transport.close()
