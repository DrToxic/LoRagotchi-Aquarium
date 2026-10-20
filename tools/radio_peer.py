"""Deterministic companion peer for tests/screenshots. Never opens real radios."""
import hashlib
import struct
import time
from tank.demo import RX
from tank.simulator import SimulatedRadio

PEER='123456789abc'+('de'*26)
REPEATER='23456789abcd'+('ef'*26)
SECRET=bytes(range(16))


def contact_packet(key=PEER,name='Nickel 🐟',kind=1,flags=0,path=b'\x00\xaa',code=3):
    return bytes([code])+bytes.fromhex(key)+bytes([kind,flags,len(path)])+path.ljust(64,b'\0')+name.encode().ljust(32,b'\0')+struct.pack('<IiiI',1700000000,39950000,-75160000,1700000001)


def direct_message(text='Hello from the mesh 🐟',key=PEER,timestamp=1700000010,text_type=0):
    return b'\x10\x14\0\0'+bytes.fromhex(key)[:6]+bytes([255,text_type])+struct.pack('<I',timestamp)+text.encode()


def channel_message(text='Nickel: Hello reef 🐟',index=1,timestamp=1700000010):
    return b'\x11\x14\0\0'+bytes([index,255,0])+struct.pack('<I',timestamp)+text.encode()


class MeshRadio(SimulatedRadio):
    """Wire fields/layout follow companion firmware, not production decoders."""
    max_payload=176
    def __init__(self,count=3,contact_count=2,channel_count=8):
        super().__init__(count)
        self.name='Aquarium RX';self.frequency=869525;self.bandwidth=250000;self.sf=11;self.cr=5;self.power=20
        self.lat=39950000;self.lon=-75160000;self.manual=1;self.policy=0;self.clock=int(time.time())
        self.channel_count=channel_count;self.channel_records={1:('#loragotchi-dx',SECRET),2:('#general',b'g'*16)}
        self.contact_records={PEER:contact_packet(),REPEATER:contact_packet(REPEATER,'Roof repeater',2)}
        for i in range(max(0,contact_count-2)):
            key=(i+500).to_bytes(32,'little').hex()
            self.contact_records[key]=contact_packet(key,f'Mesh node {i+3}')
        self.reject_next=None;self.ack_early=False;self.tx_count=0

    def send(self,payload):
        if payload.startswith(b'\x70RX\x01') or payload==b'\x0a':return super().send(payload)
        self.commands.append(payload)
        code=payload[0]
        if self.reject_next==code:
            self.reject_next=None;self.replies.put(b'\x01\x06');return
        if code==22:
            self.replies.put(bytes([13,14,255,self.channel_count])+struct.pack('<I',123456)+b'2026-10-20\0\0'+b'Test RX'.ljust(40,b'\0')+b'v1.14-test'.ljust(20,b'\0')+bytes([0,0]));return
        if code==1:
            self.replies.put(bytes([5,1,self.power & 255,22])+bytes.fromhex(RX)+struct.pack('<iiBBBBIIBB',self.lat,self.lon,1,self.policy,0,self.manual,self.frequency,self.bandwidth,self.sf,self.cr)+self.name.encode());return
        if code==4:
            self.replies.put(b'\x02'+struct.pack('<I',len(self.contact_records)))
            for packet in self.contact_records.values():self.replies.put(packet)
            self.replies.put(b'\x04'+struct.pack('<I',1700000001));return
        if code==30:
            self.replies.put(self.contact_records.get(payload[1:].hex(),b'\x01\x02'));return
        if code==31:
            index=payload[1]
            if index>=self.channel_count:self.replies.put(b'\x01\x02');return
            name,secret=self.channel_records.get(index,('',bytes(16)))
            self.replies.put(bytes([18,index])+name.encode().ljust(32,b'\0')+secret);return
        if code==20:self.replies.put(b'\x0c'+struct.pack('<HII',4120,24,2048));return
        if code==5:self.replies.put(b'\x09'+struct.pack('<I',self.clock));return
        if code in (2,3):
            self.tx_count+=1
            if code==3:self.replies.put(b'\x00');return
            ack=hashlib.sha256(payload).digest()[:4]
            if self.ack_early:self.replies.put(b'\x82'+ack+struct.pack('<I',32))
            self.replies.put(b'\x06\x01'+ack+struct.pack('<I',100));return
        if code==9:
            raw=payload[1:]
            self.contact_records[raw[:32].hex()]=b'\x03'+raw;self.replies.put(b'\0');return
        if code==15:self.contact_records.pop(payload[1:].hex(),None)
        elif code==13:
            key=payload[1:].hex();packet=bytearray(self.contact_records[key]);packet[35]=255;self.contact_records[key]=bytes(packet)
        elif code==17:self.replies.put(b'\x0b'+bytes(range(100)));return
        elif code==32:self.channel_records[payload[1]]=(payload[2:34].split(b'\0')[0].decode(),payload[34:])
        elif code==8:self.name=payload[1:].decode()
        elif code==11:self.frequency,self.bandwidth,self.sf,self.cr=struct.unpack_from('<IIBB',payload,1)
        elif code==12:self.power=struct.unpack_from('<b',payload,1)[0]
        elif code==14:self.lat,self.lon=struct.unpack_from('<ii',payload,1)
        elif code==38:self.manual,self.policy=payload[1],payload[3]
        elif code==6:self.clock=int.from_bytes(payload[1:],'little')
        elif code==56:
            formats={0:struct.pack('<HIHB',4120,120,0,0),1:struct.pack('<hbbII',-110,-78,24,12,34),2:struct.pack('<IIIIII',20,10,8,2,12,8)}
            self.replies.put(bytes([24,payload[1]])+formats[payload[1]]);return
        elif code in (26,27,39,52):
            self.replies.put(b'\x06\0'+bytes(4)+struct.pack('<I',100));return
        elif code not in (7,16,18,29):self.replies.put(b'\x01\x01');return
        self.replies.put(b'\0')
