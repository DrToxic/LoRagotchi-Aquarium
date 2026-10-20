# v0.1.8 — Floating hashtag-channel chat

## Routing and ownership

Reuse existing MeshCore inbox sync (command 10), legacy/V3 channel messages
(responses 8/17), and read-only channel metadata (command 31, response 18).
The layout was checked against `examples/companion_radio/MyMesh.cpp` in the
existing RX source. Channel headers now retain index, timestamp and text type.
Name lookup runs only on the service worker, after any pending LRX transaction;
it never nests a command inside a fish request. Cache names for 30 seconds per
connection, and discard the secret bytes carried by the metadata response.

The authenticated bridge adds only the exact two-byte channel-read command;
channel writes and arbitrary companion commands remain disallowed.
Missing/unresolved channels fail closed. No automatic channel join, radio
configuration, firmware change or on-air transmission.

`ChatQueue` accepts only plain messages on the resolved `#loragotchi-DX` channel
(case-insensitive), rejects DMs/other channels/LFG1 transfer payloads, bounds
pending messages to 24 and dedup keys to 512, and expires waiting messages after
120 seconds of animation time. The existing general inbox is not repurposed.
Chat does not enter the fish store. The new graphics setting defaults on when
loading an older settings file and survives preset changes.

## Rendering

Native Panda3D rounded meshes and cached Unicode text geometry, not a web view
or a per-frame text rebuild. Up to four independent bubble roots in one shared
world layer, spaced five seconds apart. They begin below the actual sand,
retain depth testing, drift gently while rising, leave the top, and release
their nodes. They are independent of scenery rebuilds and fish identities.
The usual window crop and output-resolution projector mask apply.

## Verification commands

```sh
uv sync --frozen --extra test
uv run --frozen pytest -q
uv run --frozen python tools/chat_smoke.py
uv run --frozen python tools/text_smoke.py
uv run --frozen python tools/run_render_smoke.py
uv run --frozen python tools/options_smoke.py
```

- Unit/integration checks cover legacy/V3 bytes, missing/nonplain channels,
  different channel slots, metadata-secret discard, interleaving with LRX
  transactions, cache, bounded dedup/expiry, disabled state, real serial
  pseudoterminal and authenticated TCP I/O, and bridge command restrictions.
- Native chat smoke feeds synthetic wire messages through `Client` and the
  real aquarium event handler. Pixel comparisons prove sand hides existing
  geometry, rising text is visible, and the bubble is completely offscreen
  before expiry. Also checks full projector blackout, two native windows,
  bounded bursts, cache stability, scene rebuild, on/off cleanup and persistence.
- Existing Unicode, 256-fish/window-lifecycle and RX-controls smoke checks
  retain coverage of the accepted v0.1.7 functionality.

Smoke data is explicitly synthetic; no real radio, live database or user
settings are touched. Screenshots/logs are under `.local/v018-*`; exact ZIP and
wheel byte verification plus fresh-package outcomes are recorded in
`.local/v018-package-verification.json`.

Environment: Linux/Xvfb/Mesa software GL. The two optional sibling-firmware
tests skip in an aquarium-only archive. Physical RX channel delivery,
Windows/NVIDIA and BLE MTU behavior need owner validation; these checks do not
claim those hardware results.
