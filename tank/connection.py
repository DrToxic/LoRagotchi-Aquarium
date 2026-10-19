"""Radio preferences and discovery; no credentials or automatic connections."""
import asyncio
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path


def live_database():
    return Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local'/'share'))/'loragotchi-tank'/'live.sqlite'


@dataclass
class ConnectionProfile:
    transport: str = 'serial'
    serial_port: str = ''
    ble_address: str = ''
    host: str = '127.0.0.1'
    port: str = '8765'
    token_file: str = ''

    def uri(self):
        if self.transport == 'serial':
            target = self.serial_port.strip()
            if not target: raise ValueError('Choose or enter a USB serial port.')
            return 'serial:'+target
        if self.transport == 'ble':
            target = self.ble_address.strip()
            if not target: raise ValueError('Choose or enter a Bluetooth device address.')
            return 'ble:'+target
        if self.transport == 'tcp':
            host = self.host.strip().strip('[]')
            if not host or any(c.isspace() for c in host) or '/' in host:
                raise ValueError('Enter a bridge hostname or IP address, without a URL prefix.')
            try: port = int(self.port)
            except (ValueError, TypeError): raise ValueError('Bridge port must be 1–65535.') from None
            if not 1 <= port <= 65535: raise ValueError('Bridge port must be 1–65535.')
            if not self.token_file.strip(): raise ValueError('Enter the path to the bridge token file.')
            return f'tcp:{host}:{port}'
        raise ValueError('Choose USB serial, Bluetooth LE or Network bridge.')

    def token(self):
        if self.transport != 'tcp': return None
        with Path(self.token_file.strip()).expanduser().open('rb') as source: token = source.read(33)
        if len(token) != 32: raise ValueError('Bridge token file must contain exactly 32 bytes.')
        return token

    def save(self, path):
        # Only the token's path is stored. Its bytes never enter UI/settings/logs.
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(asdict(self), indent=2), encoding='utf-8')
        temporary.replace(path)

    @classmethod
    def load(cls, path):
        try:
            raw = json.loads(Path(path).read_text(encoding='utf-8'))
            result = cls(**raw)
            if not all(isinstance(v, str) for v in asdict(result).values()): raise ValueError()
            if result.transport not in ('serial', 'ble', 'tcp'): raise ValueError()
            return result
        except (OSError, ValueError, TypeError): return cls()

    @classmethod
    def from_uri(cls, uri, token_file=None):
        kind, target = uri.split(':', 1)
        result = cls(transport=kind, token_file=str(token_file or ''))
        if kind == 'serial': result.serial_port = target
        elif kind == 'ble': result.ble_address = target
        elif kind == 'tcp': result.host, result.port = target.rsplit(':', 1)
        result.uri()
        return result


def discover(kind):
    """Called by the service worker, never Panda's rendering thread."""
    if kind == 'serial':
        from serial.tools import list_ports
        return [(p.device, f'{p.device} · {p.description}') for p in sorted(list_ports.comports())]
    if kind == 'ble':
        from bleak import BleakScanner
        devices = asyncio.run(BleakScanner.discover(timeout=5))
        return [(d.address, f'{d.name or "Unnamed device"} · {d.address}') for d in devices]
    return []
