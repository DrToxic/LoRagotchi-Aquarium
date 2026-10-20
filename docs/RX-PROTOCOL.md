# LRX/1 companion extension

Experimental local allocation at command/response **0x70**. Audited against
LoRagotchi-DX `6a7b41a`, whose regular command list ends at 66 and whose existing
responses/push codes do not use this signature. This is not an upstream MeshCore
registered opcode. Require the full `70 52 58 01` signature and version; stock
firmware rejection is not an RX capability. Debug Serial text is never an event.

## Carrier and consumer

- USB/TCP: existing MeshCore `< uint16-le-length payload` client framing and
  `> uint16-le-length payload` radio framing. Maximum normal frame: 176 bytes.
  Partial/coalesced stream reads are supported.
- BLE: Nordic UART service `6e400001-b5a3-f393-e0a9-e50e24dcca9e`; write-with-response
  RX characteristic `...0002...`, notify TX `...0003...`. **One GATT value is one
  companion frame.** No `<`/`>` wrapper. No arbitrary byte-chunk concatenation.
- Every extension request/response is at most 20 bytes. Larger logical events
  are fetched by offset; a 77-byte snapshot takes eight ten-byte reads.
- Firmware ships mutually exclusive USB and BLE builds. A nonzero random 32-bit
  consumer token reserves a 15-second lease, refreshed on valid requests. A
  second token gets BUSY; disconnect recovery may wait for lease expiry. Token
  is arbitration, not a security credential; BLE pairing and physical USB trust
  protect the link. TCP bridge additionally authenticates by HMAC challenge.

All integer fields are little-endian. Request prefix is `[0x70,'R','X',1,op,
consumer_token:uint32]`, followed by args. Response prefix is
`[0x70,'R','X',1,op,status]`, followed by data. Status: 0 OK, 1 bad request/lease,
2 another active consumer, 3 storage not ready. Only `HELLO` can take a new lease.

| op | Request args | OK response data |
|---|---|---|
| 0 HELLO | none | capacity u8, link flags u8 (1 USB/2 BLE), chunk size u8 (=10), storage-ready u8 |
| 1 IDENTITY | offset u8 | offset u8, total u8 (=32), up to 12 public-key bytes |
| 2 PEEK | none | event ID u32 (0 if empty), length u16 |
| 3 READ | event ID u32, offset u16 | offset u16, total u16, up to 10 data bytes |
| 4 ACK | event ID u32 | empty; success only after firmware's durable ACK-state save |
| 5 RELEASE | none | empty |
| 6 RETRY RETURN | snapshot event ID u32 | empty; explicit reset of exhausted return attempts; no new copy |

Op 6 is implemented at the protocol layer but is not yet exposed in the aquarium
UI. Retry generates a **new terminal status event ID**, leaving snapshot ID
unchanged. Unresolved jobs are never silently evicted. No recovery erasure/reset
command is offered. One copy/device/session is the PC default, not a radio opcode.

## Snapshot event (77 bytes)

| Offset | Field |
|---|---|
| 0 | kind u8 = 1 |
| 1 | event ID u32 |
| 5 | full owner public key, 32 bytes |
| 37 | fish ID u32 |
| 41 | transaction ID u32 |
| 45 | stage u8: 0 fry, 1 young, 2 adult, 3 elder |
| 46 | mode byte ASCII C or M |
| 47,48,49 | body, scales, eyes indices 0..6 |
| 50 | mono RGB565 u16 |
| 52 | appearance-present u8 0/1 |
| 53 | UTF-8 name, 24-byte NUL-padded field |

Palette 0 Coral, 1 Tangerine, 2 Gold, 3 Mint, 4 Lagoon, 5 Orchid, 6 Mono.
RX identity is the public key from IDENTITY, not a display name. Event ID is a
persisted nonzero counter scoped to RX identity. It conveys capture ordering,
**not UTC**. No age, happiness, generation or species is fabricated. Short first
COMMIT uses absent-appearance/mono fallback; duplicate short COMMIT preserves
captured genes. PC preserves earlier known genes on an incomplete re-share but
retains `appearance=false` so freshness is not fabricated.

## Terminal return-status event (11 bytes)

`kind=2:u8, event_ID:u32, snapshot_ID:u32, status:u8, attempts:u8`

Status 1 = MeshCore delivery ACK observed, 2 = unresolved after bounded attempts.
A delivery ACK is **not an application-level HOME receipt**. The original legacy
owner provides no such receipt. A return event never removes the PC snapshot.

## Durability and replay

RX commits snapshot plus pending return before ARRIVED, holds four seconds,
then tries RETURN C at most four times at ten-second spacing. Early RECALL makes
return due immediately. A duplicate/late transaction never restarts the hold.
On reboot, captured return jobs become due immediately; attempt budget persists.
A missing contact consumes bounded attempts and stays unresolved, not rerouted.

Four slots combine intake, upload backlog and return recovery. Slot reclamation
requires delivered status **and** durable PC ACKs of both snapshot/status. An
8-entry completed-transaction tombstone ring rejects recent stale COMMITs after
reuse. This is bounded replay protection, not permanent unique transactions.
Full/unhealthy storage responds BUSY to new REQ. A save failure after reservation
prevents ARRIVED and upload, but still prioritises RETURN. An abrupt loss while
storage is physically failing cannot magically preserve an unsaved snapshot.

ESP32 journal uses alternating checksum-protected SPIFFS files. Writes target
only the inactive bank, then flush, close, reread, compare and validate before
promoting it. Torn/latest-corrupt bank falls back to the last valid generation.
If existing banks are both invalid, fail closed instead of resetting event IDs.
RX does not auto-format SPIFFS on mount failure. Physical power-cut/flash-wear
validation remains required; this is not a filesystem-level atomicity guarantee.

PC commits SQLite (WAL, FULL synchronous) before ACK. Crash after save/before ACK
replays the same event and does not clone a fish. A conflicting payload reusing
an existing RX/event ID is refused. Removal/end-session hides copies locally;
a re-share refreshes them, while duplicate replay cannot undo removal. Demo and
replay stores are isolated from live by default.

Ordinary MeshCore direct/channel messages use the original offline message queue
and sync command 10, decoded separately. They are not disguised fish events.
v0.1.8 adds an ephemeral public-screen overlay only for plain messages whose
channel name resolves to `#loragotchi-DX` (case-insensitive). Command 31 reads the
channel index's metadata; response 18 contains index, 32-byte name and 16-byte
secret. Only the name is retained, cached for 30 seconds per connection. The
secret is neither retained nor logged. The original bridge permitted this exact two-byte read command. v0.2.0 adds
the separately described [stock-client workspace](RADIO.md), with explicit user
sends/settings and bridge write opt-in. No automatic replies are generated.
BLE normal inbox is skipped when its large-message MTU cannot be established.


## Stock-client multiplexing (v0.2.0)

The service worker owns one Client/transport and serializes stock companion
requests with LRX requests. Contact sync has an 8-second deadline; other stock
commands have a 4-second deadline. Multi-channel refreshes issue one lookup per
worker turn with LRX polling between turns, rather than blocking the 10-second
lease for a complete channel scan. Ordinary message bursts drain faster while
preserving LRX polling. An interrupted command is not retried automatically.

DM identities on wire are six-byte prefixes. Contacts retain full public keys;
sending fails closed if more than one saved contact matches the prefix. A
received unresolved/ambiguous prefix is not presented as a verified full key.
Chat history is separate from fish records and bounded to 5,000 messages per
SQLite database. Channel conversations include a non-secret metadata/key
fingerprint, preventing a changed channel slot from reusing the old history.

The optional LAN bridge capability request is `70 52 43 01` (`\x70RC\x01`),
handled by the bridge without radio I/O. Its response is the same four bytes
plus a write-enabled byte. Default false; `--radio-control` opts in. Supported
stock read commands are always allowed, while writes pass a strict length/code
allowlist. Rejected requests return companion error 6 without dropping LRX.
Response 18 retains its 50-byte shape but replaces nonzero channel-secret bytes
with the first 16 bytes of SHA256(secret); empty keys remain zero. The desktop
never treats these bytes as a usable secret. Device-info BLE PIN bytes are zeroed.
This avoids publishing channel keys/PINs in metadata. The existing HMAC transport
still lacks server authentication/encryption; use a trusted LAN or SSH tunnel.
