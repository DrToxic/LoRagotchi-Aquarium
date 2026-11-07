"""Bounded synthetic visitors. No real device identity or radio messages."""
import hashlib
from dataclasses import replace
from .protocol import Snapshot, ReturnStatus
from .species import LABELS

RX=hashlib.sha256(b"synthetic-rx-not-a-radio").hexdigest()
SYNTHETIC_OWNERS=frozenset(hashlib.sha256(f"synthetic-owner-{i}".encode()).hexdigest() for i in range(256))
NAMES=("Coral", "Juniper", "Mango", "Lagoon", "Violet", "Ember", "Saffron", "Mint", "Pearl", "Indigo", "Copper", "Fern")
DEFAULT_VISITOR_COUNT=len(LABELS)

def visitors(count=DEFAULT_VISITOR_COUNT):
    if not 0<=count<=256:raise ValueError("Synthetic demo supports 0..256 fish; not a live population limit")
    for i in range(count):
        owner=hashlib.sha256(f"synthetic-owner-{i}".encode()).hexdigest()
        fish=Snapshot(RX,2*i+1,owner,1000+i,2000+i,i%4,"C",i%6,(i+2)%6,(i+4)%6,65535,True,NAMES[i%len(NAMES)],species_id=i%len(LABELS),species_present=True)
        # Larger opt-in demos include all four Anglerfish ages; the default
        # still displays every pre-existing Water species.
        if count>=16 and i%16>=12:
            fish=replace(fish,species_id=14,species_present=True)
        yield fish


def events(count=DEFAULT_VISITOR_COUNT):
    for visitor in visitors(count):
        yield visitor
        yield ReturnStatus(RX,visitor.event_id+1,visitor.event_id,"delivery-confirmed",1)
