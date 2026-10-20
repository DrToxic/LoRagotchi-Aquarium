"""LRX/1 extension. Audited against local MeshCore 6a7b41a (commands 1..66).

0x70 is a *local experimental allocation*, not an upstream registered command.
No extension request/response exceeds the default BLE ATT payload of 20 bytes.
"""
from dataclasses import dataclass, asdict
import struct

MAGIC = b"\x70RX\x01"
MAX_FRAME = 176

class ProtocolError(ValueError):
    pass

class StreamFrames:
    """Existing companion framing: > from radio, < from client, uint16 LE length."""
    def __init__(self, direction=b">"):
        self.direction = direction
        self.buffer = bytearray()

    def feed(self, data):
        self.buffer.extend(data)
        frames = []
        while self.buffer:
            pos = self.buffer.find(self.direction)
            if pos < 0:
                self.buffer.clear()
                break
            del self.buffer[:pos]
            if len(self.buffer) < 3:
                break
            size = int.from_bytes(self.buffer[1:3], "little")
            if not 0 < size <= MAX_FRAME:
                del self.buffer[0]
                continue
            if len(self.buffer) < 3 + size:
                break
            frames.append(bytes(self.buffer[3:3+size]))
            del self.buffer[:3+size]
        return frames


def frame(payload, direction=b"<"):
    if not 0 < len(payload) <= MAX_FRAME:
        raise ProtocolError("Invalid companion frame size")
    return direction + struct.pack("<H", len(payload)) + payload


@dataclass(frozen=True)
class Snapshot:
    rx: str
    event_id: int
    owner: str
    fish_id: int
    tx_id: int
    stage: int
    mode: str
    body: int
    scales: int
    eyes: int
    tint: int
    appearance: bool
    name: str
    kind: str = "snapshot"


@dataclass(frozen=True)
class ReturnStatus:
    rx: str
    event_id: int
    snapshot_id: int
    status: str
    attempts: int
    kind: str = "return_status"


def decode_event(rx, data):
    if len(rx) != 64:
        raise ProtocolError("RX identity must be a full 32-byte public key")
    if not data:
        raise ProtocolError("Empty event")
    if data[0] == 1:
        if len(data) != 77:
            raise ProtocolError(f"Invalid snapshot length {len(data)}")
        event_id = struct.unpack_from("<I", data, 1)[0]
        owner = data[5:37].hex()
        fid, tx = struct.unpack_from("<II", data, 37)
        stage, mode, body, scales, eyes, tint, appearance = struct.unpack_from("<BBBBBHB", data, 45)
        if stage > 3 or mode not in (ord("C"), ord("M")) or max(body, scales, eyes) > 6 or appearance > 1:
            raise ProtocolError("Invalid fish appearance")
        name = data[53:77].split(b"\0", 1)[0].decode("utf-8", errors="replace")
        name = "".join(c for c in name if c.isprintable())[:24]
        return Snapshot(rx, event_id, owner, fid, tx, stage, chr(mode), body, scales, eyes, tint, bool(appearance), name)
    if data[0] == 2 and len(data) == 11:
        event_id, snapshot_id, status, attempts = struct.unpack_from("<IIBB", data, 1)
        if status not in (1, 2) or attempts > 4:
            raise ProtocolError("Invalid return status")
        return ReturnStatus(rx, event_id, snapshot_id, "delivery-confirmed" if status == 1 else "unresolved", attempts)
    raise ProtocolError("Unknown event kind or version")


def encode_event(event):
    if isinstance(event, Snapshot):
        name = event.name.encode("utf-8")[:23].decode("utf-8", errors="ignore").encode("utf-8").ljust(24, b"\0")
        return (b"\x01" + struct.pack("<I", event.event_id) + bytes.fromhex(event.owner)
                + struct.pack("<IIBBBBBHB", event.fish_id, event.tx_id, event.stage, ord(event.mode),
                              event.body, event.scales, event.eyes, event.tint, int(event.appearance)) + name)
    return b"\x02" + struct.pack("<IIBB", event.event_id, event.snapshot_id, 1 if event.status == "delivery-confirmed" else 2, event.attempts)


def mesh_message(payload):
    """Decode actual companion messages; fish events are never fabricated DMs."""
    if not payload:
        return None
    code = payload[0]
    start = 4 if code in (16, 17) else 1
    if code in (7, 16) and len(payload) >= start+12:
        key = payload[start:start+6].hex()  # a prefix, deliberately not called a full identity
        text_type = payload[start+7]
        text_start = start+12+(4 if text_type == 2 else 0)
        if len(payload) < text_start: return None
        return {"kind": "mesh", "route": "direct", "sender_prefix": key,
                "timestamp": struct.unpack_from('<I', payload, start+8)[0],
                "text_type": text_type, "path_length": payload[start+6],
                "snr": struct.unpack_from('<b',payload,1)[0]/4 if start==4 else None,
                "text": payload[text_start:].decode("utf-8", errors="replace")[:160]}
    if code in (8, 17) and len(payload) >= start+7:
        text_type = payload[start+2]
        return {"kind": "mesh", "route": f"channel {payload[start]}",
                "channel_index": payload[start], "text_type": text_type,
                "timestamp": struct.unpack_from("<I", payload, start+3)[0],
                "text": payload[start+7:].decode("utf-8", errors="replace")[:160]}
    return None


def channel_info(payload):
    """Read the name only; do not retain/log the secret included by MeshCore."""
    if len(payload) != 50 or payload[0] != 18:
        raise ProtocolError("Invalid channel-info response")
    return payload[1], payload[2:34].split(b"\0", 1)[0].decode("utf-8", errors="replace")


def bridge_command_allowed(payload, radio_control=False):
    """RX plus bounded stock-client commands; writes require bridge opt-in."""
    from .meshcore_protocol import allowed_command, BRIDGE_CAPS
    if payload == BRIDGE_CAPS: return True
    if payload.startswith(MAGIC):
        return len(payload) in (9,10,13,15) and len(payload)>=9 and len(payload)=={0:9,1:10,2:9,3:15,4:13,5:9}.get(payload[4])
    return allowed_command(payload, write=radio_control)
