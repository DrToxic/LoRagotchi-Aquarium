"""Bounded synthetic visitors. No real device identity or radio messages."""
import hashlib
from .protocol import Snapshot, ReturnStatus

RX=hashlib.sha256(b"synthetic-rx-not-a-radio").hexdigest()
NAMES=("Coral", "Juniper", "Mango", "Lagoon", "Violet", "Ember", "Saffron", "Mint", "Pearl", "Indigo", "Copper", "Fern")

def visitors(count=12):
    if not 0<=count<=256:raise ValueError("Synthetic demo supports 0..256 fish; not a live population limit")
    for i in range(count):
        owner=hashlib.sha256(f"synthetic-owner-{i}".encode()).hexdigest()
        yield Snapshot(RX,2*i+1,owner,1000+i,2000+i,i%4,"C",i%6,(i+2)%6,(i+4)%6,65535,True,NAMES[i%len(NAMES)])


def events(count=12):
    for visitor in visitors(count):
        yield visitor
        yield ReturnStatus(RX,visitor.event_id+1,visitor.event_id,"delivery-confirmed",1)
