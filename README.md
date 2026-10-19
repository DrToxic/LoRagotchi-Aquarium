# LoRagotchi-Aquarium · v0.1.2

A native **Python + Panda3D** aquarium for shared LoRagotchi fish. Real 3D fish,
independent cruise/glide swimming, animated tails/turns, original procedural scenery, adjustable graphics, durable
snapshot storage, and USB/BLE/LAN adapters to the companion **LoRagotchi-RX**
firmware prototype. No web server or Electron renderer.

RX receives a normal DX visit, captures a snapshot, then proactively returns the
original after about four seconds. Returning the original **does not remove the
copy**. No local pet, care or breeding runs on RX. Copies do not age themselves;
sharing again refreshes their appearance.

## Quick start — no radio required

Clone the repository (or download and extract its ZIP), then open a terminal in
that directory. Python **3.10 or newer** is required; Python 3.12 is the tested
version. With [uv](https://docs.astral.sh/uv/) installed:

```sh
git clone https://github.com/DrToxic/LoRagotchi-Aquarium.git
cd LoRagotchi-Aquarium
```

```sh
uv sync --extra test
uv run loragotchi-tank --demo 16 --preset high
```

Alternatively, use Python directly — no uv or shell activation required:

**Linux:**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m tank --demo 16 --preset high
```

**Windows (PowerShell):**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m tank --demo 16 --preset high
```

The Windows example assumes Python 3.12 is installed. The owner tested the initial
prototype on Windows with 256 fish (i7-11700F / RTX 3060); this update still needs
Windows acceptance. This is a source prototype, not a standalone installer.

```sh
# Low-cost rendering on a high-resolution display; no automatic population loss.
uv run loragotchi-tank --demo 24 --preset low --width 1920 --height 1080 --render-scale .5

# Two separate OS windows showing one continuous aquarium.
uv run loragotchi-tank --demo 256 --wall-columns 2 --preset high

# Unequal monitors/windows, with the second display lower and to the right.
# Replace the example Y=180 with your desktop offset, or just drag the windows.
uv run loragotchi-tank --demo 256 --wall-columns 2 --preset high --width 2560 --height 1440 --second-width 1920 --second-height 1080 --second-origin 2560 180

# Borderless fullscreen; uses monitor bounds, independent of scene scale.
uv run loragotchi-tank --demo 16 --fullscreen --width 3840 --height 2160 --preset high

# Manual overrides: implemented features only.
uv run loragotchi-tank --demo --detail 12 --plants 10 --bubbles 4 --fps 30 --no-caustics
```

`Tab`: operator controls · `F`: borderless fullscreen · `1…5`: quality presets · `N`: names ·
`V`: open/close second window · click/right arrow: select fish · `Delete`: remove selected copy ·
`Esc`: close panel, then exit. End display session asks for a second click; this
hides display copies and never sends a radio RETURN. New shares can reappear.

The second view is now a **real, independently movable/resizable window**, not a
split screen. Both windows share the same fish and simulation. Their OS-reported
positions and sizes determine continuous camera crops, including vertical offsets
and monitors to the left of the primary display. The gap between windows remains
a gap in the virtual aquarium. Move/resize the windows to match your desktop;
changing the combined window bounds reframes the shared scene.

In the second window, `N` toggles names, `F` toggles its fullscreen mode,
click/right arrow selects a fish, and `V`, `Esc`, or its close button closes only
that window. Operator controls stay in the main window. To reopen, press `V` in
the main window. On Windows, fullscreen uses the containing monitor’s bounds without changing its
display mode; toggling back restores the previous window size and position. This
also avoids requesting unsupported client sizes such as 1920×1009 as monitor
modes. The Windows API path, mixed-DPI coordinates and mixed-refresh frame pacing
still need owner hardware validation. The Linux fallback uses Panda’s display
bounds; per-monitor Linux/macOS fullscreen placement is not established.
No multi-host sync or bezel calibration.

Fish choose longer journeys into underused visible-water sectors, with independent
cruising speeds, gradual turns and slow glides. Destinations adapt to the combined
window view; resizing does not teleport fish. Graphics changes or re-sharing do
not reset their swimming state. Names retain the cached text geometry introduced
in v0.1.1.

Collision detection uses Bullet, already included with Panda3D: stage-sized fish
body capsules, solid reef rock/coral shapes, and tank/floor boundaries. Predictive
steering and gentle contact response avoid billiard-ball bouncing. Flexible fins,
tails and plants are not rigid colliders; fish at different depths can still
overlap on screen. These are approximate solid shapes, not per-triangle soft-body
physics. Arrivals are placed with clearance when space is available; no fish are
removed to satisfy crowd density. Extreme overcapacity can still cause crowding.

Demo supports 0–256 synthetic fish as a bounded test generator; this is **not a
hard-coded live population cap**. Graphics quality never culls real visitors.
Names and operator UI are optional. Synthetic mode is clearly labelled.

## RX connections

Use only with RX firmware described in [the RX protocol](docs/RX-PROTOCOL.md).
Stock/DX firmware does not implement this extension. No direct-message replies
are sent by this PC client: RX is the sole LFG1 authority.

```sh
uv run loragotchi-tank --connect serial:/dev/ttyUSB0 --operator
# Windows serial equivalent: --connect serial:COM4
uv run loragotchi-tank --connect ble:AA:BB:CC:DD:EE:FF --operator
```

BLE uses the existing Nordic UART companion characteristics. Pair the device in
your operating system with the PIN shown on its RX display. Each LRX fragment is
at most 20 bytes, including headers, so no assumed large MTU or guessed stream
reassembly is needed. Real BLE pairing/notification behavior is **untested**.
Ordinary MeshCore inbox polling is disabled when Bleak cannot confirm an ATT MTU
of at least 179; fish sharing still uses the small-fragment route.

### WLAN / LAN via an explicit bridge

The first iteration supplies a **real PC/SBC bridge**, not an onboard-Wi-Fi
endpoint. A machine attached to RX by USB or BLE runs:

```sh
uv run loragotchi-rx-bridge --token-file .local/rx.token --init-token
uv run loragotchi-rx-bridge --radio serial:/dev/ttyUSB0 --token-file .local/rx.token
uv run loragotchi-tank --connect tcp:127.0.0.1:8765 --token-file .local/rx.token
```

For a trusted LAN, explicitly bind the bridge to its private LAN address and
privately copy the token file to the aquarium machine. Do not expose this port
to the Internet. Challenge/HMAC authenticates the client but **does not encrypt**
traffic; use an SSH tunnel when confidentiality is needed. No Wi-Fi credentials
or firewall rules are changed. One connected consumer at a time. The bridge
allows only the RX extension and read-only MeshCore inbox polling, not arbitrary
radio configuration/private-key commands. No onboard WLAN RX build is supplied.

The live SQLite database defaults to `~/.local/share/loragotchi-tank/live.sqlite`
(or `XDG_DATA_HOME`). Settings use `~/.config/loragotchi-tank/settings.json` (or
`XDG_CONFIG_HOME`). `--database`, `--settings`, and `--session` override these.
Demo/replay default to an **in-memory** database, never the live roster. A copy is
keyed by full owner public key within a session; matching names/IDs can coexist.

## Replay

JSONL, one `{ "rx": "64 hex characters", "payload": "binary event as hex" }` per
line. Replayed events go through the production event parser and SQLite service:

```sh
uv run loragotchi-tank --replay docs/example-replay.jsonl --preset balanced
```

## Hardware and visual scope

| Path | v0.1 evidence |
|---|---|
| Linux x86_64 | Native rendering and operator callbacks tested under Xvfb/Mesa llvmpipe |
| Modern Raspberry Pi | Design target; ARM64 engine wheels exist, no physical Pi validation |
| Original Pi / Zero / 32-bit ARM | **Not established**: packaging, driver and performance gate remains open |
| Windows | Owner tested initial prototype at 256 fish on i7-11700F / RTX 3060; v0.1.2 multi-window/performance retest pending, no installer |
| macOS | Opportunistic; untested |
| 1080p/4K | Arbitrary output dimensions and independent render scale; 1080p tested, 4K not benchmarked |
| Video wall | Two real OS windows, unequal-size/offset frusta and shared-world reconstruction tested on Linux Xvfb; Windows/mixed-DPI placement unverified, no multi-host sync/bezel calibration |
| USB | Actual serial I/O tested via pseudoterminal, physical RX untested |
| BLE | Concrete adapter + BLE firmware build; packet contract tested, physical link untested |
| WLAN/TCP | Authenticated bridge over actual loopback sockets tested; physical LAN/radio untested |

Compatibility/Low/Balanced/High/Ultra change resolution scale, mesh detail,
lighting, vegetation, bubbles and caustics. They are **visual profiles, not board
certification**. Shadows, reflections, texture-quality menus, antialiasing and
postprocessing are not advertised as implemented. No second renderer is hidden
behind Compatibility. The smallest Pi must not dictate the installation ceiling,
but claiming support needs hardware/build evidence.

Python/Panda3D was selected for this runnable iteration: maintained native C++
render engine, quick protocol iteration, and useful Windows/modern Linux builds.
C++/raylib remains worth testing if the original-Pi packaging gate fails; no
unverified claim that this Python stack already supports every Pi.

## Tests and screenshots

```sh
uv run pytest -q
uv run python tools/run_render_smoke.py
uv run python tools/headless_capture.py --demo 16 --preset high \
  --screenshot .local/aquarium.png --run-seconds 6 --settings .local/settings.json
```

On an aquarium-only checkout, the two optional C++/RX integration tests skip
because they require the separate sibling RX source; the aquarium tests still
run. Install the test extra (`uv sync --extra test` or `python -m pip install -e
'.[test]'`) before running pytest.

The last two commands require Linux Xvfb. They launch only a temporary local X
server (`-nolisten tcp`); no xauth installation or system config change is needed.
Software-renderer timings are not GPU or Pi FPS evidence.

See [v0.1.2 testing notes](docs/TESTING-v0.1.2.md), [implementation report](docs/IMPLEMENTATION-REPORT.md),
[protocol](docs/RX-PROTOCOL.md), [asset attribution](assets/ATTRIBUTION.md), and
[firmware handoff notes](docs/FIRMWARE.md). No radio has been flashed or used over
the air by this implementation task.

# Credits
LoRagotchi Aquarium is by DrToxic, and is made for the LoRagotchi-DX firmware by
Robert Rayner / M0YNW.

Big thanks go out to Robert for letting me muck in on the project!

Further thanks go to the MeshCore team for creating MeshCore in such a format that
we can do these fun things!

## Related projects

### Looking for the Aquarium firmware?
https://github.com/DrToxic/LoRagotchi-RX [Pending...]

### Looking for LoRagotchi-DX?
Original Author: https://github.com/DarkButterfly85/LoRagotchi-DX

Fork: https://github.com/DrToxic/LoRagotchi-DX

RX/DX firmware source and binaries are not included in this aquarium repository.
