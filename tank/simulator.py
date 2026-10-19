"""PC handoff simulator only, not a firmware simulator or physical-radio proof."""
import queue
import struct
from .protocol import MAGIC, encode_event
from .demo import events, RX

class SimulatedRadio:
    def __init__(self,count=8):
        self.events={e.event_id:encode_event(e) for e in events(count)}
        self.acked=set();self.replies=queue.Queue();self.lease=None
        self.fail_after_save=False
    def send(self,payload):
        if payload==b"\x0a":self.replies.put(b"\x0a");return
        if len(payload)<9 or not payload.startswith(MAGIC):raise ValueError("Invalid simulator command")
        op,token=payload[4],payload[5:9]
        header=MAGIC+bytes([op])
        if self.lease and self.lease!=token:self.replies.put(header+b"\x02");return
        if op==0:self.lease=token;data=bytes([4,1,10,1])
        elif token!=self.lease:self.replies.put(header+b"\x01");return
        elif op==1:
            offset=payload[9];data=bytes([offset,32])+bytes.fromhex(RX)[offset:offset+12]
        elif op==2:
            eid=next((i for i in self.events if i not in self.acked),0)
            data=struct.pack("<IH",eid,len(self.events[eid]) if eid else 0)
        elif op==3:
            eid,offset=struct.unpack("<IH",payload[9:]);event=self.events[eid]
            data=struct.pack("<HH",offset,len(event))+event[offset:offset+10]
        elif op==4:
            if self.fail_after_save:
                self.fail_after_save=False;raise ConnectionError("Injected PC crash after save/before ACK")
            self.acked.add(struct.unpack("<I",payload[9:])[0]);data=b""
        elif op==5:self.lease=None;data=b""
        else:self.replies.put(header+b"\x01");return
        self.replies.put(header+b"\x00"+data)
    def receive(self,timeout=2):
        try:return self.replies.get(timeout=timeout)
        except queue.Empty:raise TimeoutError from None
    def close(self):self.lease=None
