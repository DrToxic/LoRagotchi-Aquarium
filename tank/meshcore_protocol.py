"""Stock companion wire formats, shared with LRX on the *same* transport.

Checked against MeshCore companion MyMesh.cpp and meshcore_py 2.3.17.
No private-key commands. Names/text are UTF-8 byte-limited, never truncated.
"""
import hashlib
import math
import struct
from .protocol import ProtocolError, MAX_FRAME

BRIDGE_CAPS = b'\x70RC\x01'
ERRORS = {1: 'unsupported command', 2: 'not found', 3: 'storage full',
          4: 'invalid state', 5: 'file I/O error', 6: 'invalid argument'}


class RadioRejected(ValueError):
    """Explicit error response: unlike a timeout, the stream remains usable."""


def text_bytes(value, limit, label='Text', empty=False):
    if not isinstance(value, str) or '\0' in value:
        raise ValueError(f'{label} cannot contain NUL.')
    if any(ord(c)<32 and not (label=='Message' and c in '\n\t') for c in value):
        raise ValueError(f'{label} contains unsupported control characters.')
    raw = value.encode('utf-8')
    if (not value.strip() and not empty) or len(raw) > limit:
        raise ValueError(f'{label} must be {0 if empty else 1}–{limit} UTF-8 bytes.')
    return raw


def public_key(value):
    try: raw = bytes.fromhex(value)
    except (ValueError, TypeError): raise ValueError('Use the full 64-hex-character public key.') from None
    if len(raw) != 32: raise ValueError('Use the full 64-hex-character public key.')
    return raw


def string(raw):
    return raw.split(b'\0', 1)[0].decode('utf-8', 'replace')


def contact(packet):
    if len(packet) not in (144, 148) or packet[0] not in (3, 0x8a):
        raise ProtocolError('Invalid contact record')
    plen = packet[35]
    hops, width = (0, 1) if plen == 255 else (plen & 63, (plen >> 6)+1)
    if width > 3 or hops*width > 64: raise ProtocolError('Invalid contact path')
    last, lat, lon = struct.unpack_from('<Iii', packet, 132)
    return dict(key=packet[1:33].hex(), type=packet[33], flags=packet[34],
                name=string(packet[100:132]), path_length=plen,
                path=packet[36:36+hops*width].hex(), last_advert=last,
                lat=lat/1e6, lon=lon/1e6, raw=packet[1:].hex())


def contact_update(item, *, name=None, flags=None, path=None, path_width=1):
    raw = bytearray.fromhex(item['raw'])
    if len(raw) not in (143, 147): raise ValueError('Refresh this contact before editing.')
    if name is not None: raw[99:131] = text_bytes(name, 31, 'Name').ljust(32, b'\0')
    if flags is not None: raw[33] = int(flags)
    if path is not None:
        path_width = int(path_width)
        try: data = bytes.fromhex(path.replace(' ', ''))
        except ValueError: raise ValueError('Route must be hexadecimal hop hashes.') from None
        if path_width not in (1, 2, 3) or len(data) > 64 or len(data) % path_width or len(data)//path_width > 63:
            raise ValueError('Invalid route size for the selected hop width.')
        raw[34] = len(data)//path_width | (path_width-1) << 6
        raw[35:99] = data.ljust(64, b'\0')
    return b'\x09'+raw


def self_info(packet):
    if len(packet) < 58 or packet[0] != 5: raise ProtocolError('Invalid radio identity response')
    lat, lon = struct.unpack_from('<ii', packet, 36)
    freq, bw = struct.unpack_from('<II', packet, 48)
    return dict(key=packet[4:36].hex(), name=string(packet[58:]),
                power=struct.unpack_from('<b', packet, 2)[0], max_power=packet[3],
                lat=lat/1e6, lon=lon/1e6, multi_acks=packet[44],
                location_policy=packet[45], telemetry=packet[46], manual_add=packet[47],
                frequency=freq/1000, bandwidth=bw/1000, sf=packet[56], cr=packet[57])


def device_info(packet):
    if len(packet) < 80 or packet[0] != 13: raise ProtocolError('Unsupported device information')
    # Bytes 4:8 contain the BLE PIN. Do not retain or publish it.
    return dict(protocol=packet[1], max_contacts=packet[2]*2, max_channels=packet[3],
                build=string(packet[8:20]), model=string(packet[20:60]), version=string(packet[60:80]),
                repeat=bool(packet[80]) if len(packet)>80 else False,
                path_mode=packet[81] if len(packet)>81 else 0)


def channel(packet):
    if len(packet) != 50 or packet[0] != 18: raise ProtocolError('Invalid channel information')
    name = string(packet[2:34])
    # Identity fingerprint prevents slot reuse from mixing unrelated histories.
    # Raw channel keys never enter UI events, history, or logs.
    identity = hashlib.sha256(packet[2:]).hexdigest()[:24]
    return dict(index=packet[1], name=name, identity=identity, occupied=bool(name or any(packet[34:])))


def set_channel(index, name, secret='', clear=False):
    index = int(index)
    if not 0 <= index <= 255: raise ValueError('Invalid channel slot.')
    if clear: return bytes([32, index])+bytes(48)
    raw = text_bytes(name, 31, 'Channel name')
    if name.startswith('#'):
        key = hashlib.sha256(raw).digest()[:16]
    else:
        try: key = bytes.fromhex(secret)
        except ValueError: raise ValueError('Private channel key must be 32 hex characters.') from None
        if len(key) != 16: raise ValueError('Private channel key must be 32 hex characters.')
    return bytes([32, index])+raw.ljust(32, b'\0')+key


def radio_params(frequency, bandwidth, sf, cr, repeat=False):
    f, bw, sf, cr = float(frequency), float(bandwidth), int(sf), int(cr)
    if not math.isfinite(f+bw) or not (150 <= f <= 2500 and 7 <= bw <= 500 and 5 <= sf <= 12 and 5 <= cr <= 8):
        raise ValueError('RF values: 150–2500 MHz, 7–500 kHz, SF 5–12, CR 5–8.')
    return b'\x0b'+struct.pack('<IIBBB', round(f*1000), round(bw*1000), sf, cr, int(repeat))


def coordinates(lat, lon):
    lat, lon = float(lat), float(lon)
    if not (-90 <= lat <= 90 and -180 <= lon <= 180): raise ValueError('Invalid latitude/longitude.')
    return b'\x0e'+struct.pack('<ii', round(lat*1e6), round(lon*1e6))


def stats(packet):
    if len(packet)<2 or packet[0]!=24: raise ProtocolError('Invalid statistics response')
    formats = {0: ('<HIHB', ('battery_mv','uptime_s','errors','tx_queue')),
               1: ('<hbbII', ('noise_dbm','rssi_dbm','snr_quarters','tx_air_s','rx_air_s')),
               2: ('<IIIIII', ('received','sent','flood_tx','direct_tx','flood_rx','direct_rx'))}
    if packet[1] not in formats: raise ProtocolError('Unknown statistics type')
    fmt, keys = formats[packet[1]]
    if len(packet) < 2+struct.calcsize(fmt): raise ProtocolError('Truncated statistics')
    return dict(zip(keys, struct.unpack_from(fmt, packet, 2)))


def remote_status(packet):
    if len(packet)<60 or packet[0]!=0x87:raise ProtocolError('Truncated remote status')
    battery,queued,noise,rssi,received,sent,airtime,uptime=struct.unpack_from('<HHhhIIII',packet,8)
    snr=struct.unpack_from('<h',packet,50)[0]/4
    return f'{battery} mV · uptime {uptime}s · RX {received} / TX {sent} · queue {queued} · RSSI {rssi} dBm · SNR {snr:g} dB'


def telemetry(data):
    """Decode standard sensor fields using the maintained Cayenne LPP library."""
    from cayennelpp import LppData
    from cayennelpp.lpp_type import LppType
    fields=[];offset=0
    while offset<len(data):
        if not any(data[offset:]):break
        if len(data)-offset<2:raise ProtocolError('Truncated telemetry header')
        kind=LppType.get_lpp_type(data[offset+1])
        if kind is None:
            fields.append(f'Unknown sensor type {data[offset+1]} (remaining data not decoded)');break
        if len(data)-offset<kind.size+2:raise ProtocolError('Truncated telemetry value')
        item=LppData.from_bytes(data[offset:offset+kind.size+2]);values=list(item.value)
        if kind.type==116 and values[0]>327.67:values[0]=round(values[0]-655.36,2)
        if kind.type==117 and values[0]>32.767:values[0]=round(values[0]-65.536,3)
        fields.append(f'Ch {item.channel} {kind.name}: '+', '.join(str(v) for v in values))
        offset+=kind.size+2
    return ' · '.join(fields) or 'No telemetry fields'


def allowed_command(payload, write=False):
    """Strict bridge surface, not an arbitrary companion passthrough."""
    if not payload or len(payload)>MAX_FRAME: return False
    code, n = payload[0], len(payload)
    reads = {4: (1, 5), 5: (1,), 10: (1,), 17: (1,33), 20: (1,), 22: (2,),
             30: (33,), 31: (2,), 43: (1,), 56: (2,), 59: (1,)}
    if code == 1: return 8<=n<=40
    if code in reads: return n in reads[code] and (code!=56 or payload[1]<=2)
    if not write: return False
    exact = {6:(5,), 7:(2,), 9:(144,148), 11:(11,12), 12:(2,), 13:(33,),
             14:(9,), 15:(33,), 16:(33,), 27:(33,), 29:(33,), 32:(50,),
             38:(5,), 39:(36,), 52:(34,), 58:(2,), 61:(3,)}
    if code in exact: return n in exact[code]
    if code == 2: return 14<=n<=173 and payload[1] in (0,1,3)
    if code == 3: return 8<=n<=167 and payload[1]==0
    if code == 8: return 2<=n<=32
    if code == 18: return 99<=n<=176
    if code == 26: return 33<=n<=96
    # Deliberately omit private keys, signing, raw packets, reboot, factory reset
    # and unrestricted local CLI (which could bypass the command allowlist).
    return False
