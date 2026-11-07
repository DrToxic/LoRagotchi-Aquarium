# Water RX–Aquarium contract (local implementation; not deployed)

LRX/1 signature and commands 0–6 are unchanged. Kind 1 is exactly 77 bytes;
kind 2 is exactly 11 bytes. No padding is repurposed. Default export is legacy.
A new client requests command 7, exact request length 10, normal token at 5,
byte 9 = 1 (Water event schema). Success returns one byte 1. Old RX returns
status 1; the new client falls back to legacy. Other errors are fatal. Negotiation
belongs to the active 15-second lease, resets on release/expiry/takeover, and is
locked once summary/read begins. No negotiated format survives reconnect.

Opted-in leases export snapshot kind 3, exactly 84 bytes. Bytes 1–76 are the
unchanged kind-1 payload. Offset 77 is presence bits: 1 species (S1), 2 fine genes
(H1), 4 panel (P1); other bits must be zero. Species LE16 at 78; body/scales/eyes
genes at 80/81/82; panel at 83. Absent fields are zero, and are not evidence of
received fish species/genes/panel. Present species retains all uint16 values;
present genes accept 0..6 or 8..247; panel is 0..2. Legacy palette remains 0..6.
Unknown species render as fish 0 but remain stored exactly. Name never determines
species. Terminal return remains kind 2. Event IDs, ACKs and ledger are shared
across both formats: no second event or deletion on RETURN. A legacy consumer gets
a valid kind 1 and may acknowledge that intentionally lossy projection. Consumers
must fully decode and durably save before ACK; unknown/malformed events are never
ACKed. Replay dedup accepts the same event's legacy projection without erasing
known metadata; contradictory supplied metadata is rejected.

RX accepts strict short COMMIT (four fields), strict nine-field legacy appearance,
and ordered optional H1 (three genes), P1 (panel), S1 (species), each at most once.
Malformed/overflow/empty/trailing/unknown fields reject without consuming the
reservation. S1 ACK is advertised only with durable retention implemented. Every
first accepted capture is immutable, including absence provenance, full 32-byte
owner/transaction/fish binding; short/full retries cannot replace it. Actual DX
caches its complete negotiated COMMIT, so losing the first COMMIT retains metadata.

Journal version 2 extends each slot with seven metadata bytes. Valid exact-size
version-1 banks migrate in memory preserving event IDs, jobs, upload flags, keys
and generations, then write only the inactive bank with verified readback. No
format/reset/store deletion. Unsupported future banks block startup/writes even
beside an older valid bank; corrupt banks use a valid peer bank, both invalid fail
closed. Physical flash/power-cut safety is not established by host tests.

Radio custody/RETURN is independent of PC availability, rendering or SQLite
success. AQUARIUM1 follows durable RX capture, not a PC attestation. Existing four
slots, retry budget and terminal return jobs remain. Legacy RX cannot recover
metadata it never captured: re-share through capable RX is required.

## Python data API

Snapshot adds species_id=0, body_gene/scales_gene/eyes_gene=None, panel=None,
species_present=False, genes_present=False, panel_present=False. Presence describes
received metadata, not guesses. SQLite JSON rows need no destructive schema reset;
missing keys use dataclass defaults. Partial/legacy re-shares preserve prior known
metadata only for the same owner and fish ID; never transfer it to a new fish identity. Event rows remain
durable replay records. Registry is tank.species; fine-colour rendering is a separate consumer concern.
LEG1 eggs stay fish-only: no species suffix or name-based inference, and no changes
to local Mystery/adopted identity semantics.
