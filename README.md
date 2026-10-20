# LoRagotchi-Aquarium · v0.1.8

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
prototype on Windows with 256 fish (i7-11700F / RTX 3060), and accepted the
v0.1.2 swimming/collision update. The new v0.1.3 radio controls need hardware testing. This is a source prototype, not a standalone installer.

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
`V`: add another window (up to eight) · click/right arrow: select fish · `Delete`: remove selected copy ·
`Esc`: close panel, then exit. While editing a text field, aquarium shortcuts are
suspended and `Tab` advances to the next field. End display session asks for a second click; this
hides display copies and never sends a radio RETURN. New shares can reappear.

Names and incoming text use bundled Liberation Sans plus **Noto Emoji**
monochrome glyphs, including 🐟 and ☣. No extra system font installation is
needed. Emoji presentation selectors are ignored; joined emoji may appear as
individual symbols. Characters outside both fonts display as `?`. This affects
display only: original Unicode names remain unchanged in radio data and the
saved collection. The same fallback applies to labels, the selected-fish panel,
messages, connection status and discovered device names.

v0.1.7 fixes a Windows-only crash in the v0.1.6 emoji coverage check. Existing
collections/settings remain compatible; no database reset or firmware update is
needed. See [Windows Unicode regression checks](docs/TESTING-v0.1.7.md).

### Floating channel chat (v0.1.8)

Plain messages received by RX on **`#loragotchi-DX`** emerge from behind the sand
in rounded chat bubbles, drift upward, and leave the top of the aquarium.
Sender names and Unicode/emoji use the existing bundled fonts. Bubbles live in
the shared 3D world: sand/reef can occlude them, windows crop the same bubble,
and projector blackouts cover them.

**Tab → Aquarium → Channel chat: on/off** controls the effect and remembers your
choice. It is on by default. Disabling it clears visible/queued chat; it does not
disconnect RX or alter the fish collection.

- RX must already have that hashtag channel configured. The aquarium reads its
  channel name; it does not join channels or change keys/settings on the radio.
  Name matching is case-insensitive and never assumes a fixed channel slot.
- Direct messages, other channels, non-plain messages and `LFG1` fish-transfer
  traffic never become bubbles. Ordinary inbox behavior remains available.
- Chat is ephemeral: up to four visible bubbles, 24 waiting messages, five
  seconds between launches; queued messages older than two minutes expire.
  Duplicate receiver/channel/timestamp/text combinations are suppressed.
  Chat is not saved as fish or written into the collection database.
- USB and the authenticated bridge support the read-only channel lookup.
  **Update the bridge host to v0.1.8 too** if using TCP. BLE retains the existing
  requirement for a confirmed MTU of at least 179 for ordinary chat messages;
  small-MTU fish transfers are unaffected.

No new dependency or RX firmware update is required for the existing
channel-message protocol. Synthetic protocol, serial/TCP and rendered pixel
checks are documented in [v0.1.8 testing notes](docs/TESTING-v0.1.8.md).
Physical radio/Windows validation of this new feature remains pending.

Each view is a **real, independently movable/resizable OS window**, not a split
screen. All windows share the same fish and simulation. Their OS-reported client
positions and sizes determine continuous camera crops, including vertical offsets
and negative desktop coordinates. Move/resize windows to match your setup;
changing the combined window bounds reframes the shared scene.

In an additional window, `N` toggles names, `F` toggles that window's fullscreen,
click/right arrow selects fish, `V` adds a view, and `Esc`/the close button closes
only that view. `Tab` toggles controls in the **main** window. Windows can also be
selected, added, closed and made fullscreen in **Tab → Deadzones**.

On Windows, fullscreen uses the containing monitor’s bounds without changing its
display mode; toggling back restores the previous window size and position. This
also avoids requesting unsupported client sizes such as 1920×1009 as monitor
modes. The Windows API path, mixed-DPI coordinates and mixed-refresh frame pacing
still need owner hardware validation. The Linux fallback uses Panda’s display
bounds; per-monitor Linux/macOS fullscreen placement is not established.
No multi-host sync or bezel calibration.

Fish choose longer journeys into underused visible-water sectors, with independent
cruising speeds, gradual turns and slow glides. Destinations adapt to the combined
window view. Ordinary swimming and graphics changes preserve individual state;
newly hidden fish are relocated when a window/deadzone layout changes. Names retain the cached text geometry introduced
in v0.1.1.

### Deadzones and display layouts (v0.1.4)

Open **Tab → Deadzones**. **Edges: on** is the default: the complete fish silhouette
(body, fins and tail) stays within the union of non-minimized aquarium window
areas. Fish can cross adjoining/overlapping edges, but cannot swim through a gap
or missing corner between windows. Disconnected areas keep their fish until the
layout changes; they do not secretly cross the desktop. Manual zones work at all
fish depths. **Edges: off** restores unrestricted gap-crossing; zones still apply.

- **Add / Close:** up to eight native windows. Select a view in the dropdown;
  the main view cannot be closed here. New views cascade so you can place them.
- **Save layout:** remembers current window positions, sizes and count for next
  launch. `--wall-columns 1` ignores saved window geometry; `--wall-columns N`
  explicitly starts 1–8 windows. Each window is still freely movable/resizable.
- **New zone → shape → Apply:** rectangle (independent width/height, including squares),
  rounded rectangle (quarter-short-side corner radius) or ellipse (equal physical
  dimensions give a circle). Up to 16 zones; cycle with `<`/`>`, edit, disable or
  delete individually. Apply automatically saves zones and edge protection.
- **Left / Top / Width / Height:** percentages of the *whole combined layout*,
  measured from its top-left corner. Click the preview to set the draft centre,
  then Apply. Percentages follow layout resizing; check them after rearranging
  monitors. They are not percentages of the selected window.
- **Outlines:** toggles visible coral-coloured borders across the aquarium views;
  preview outlines are always available. Scenery remains visible unless that zone has **Blackout: on**.

#### Projectors and round displays (v0.1.5)

Each deadzone has independent switches in **Tab → Deadzones**:

| Settings | Fish restriction | Projector output |
|---|---|---|
| Invert off, Blackout off | Avoid inside | Scenery still visible |
| Invert off, Blackout on | Avoid inside | Inside painted black |
| Invert on, Blackout off | Stay inside | Scenery still visible outside |
| Invert on, Blackout on | Stay inside | Everything outside painted black |

Blackout masks scenery, fish, names and HUD text at output resolution, independent
of render scale. Disabled zones do neither. Switches save immediately on an
existing zone; new zones remain drafts until **Apply**. Old layouts default to
both switches off. Multiple zones combine their excluded areas; multiple inverted
zones therefore retain only their **shared interior**, not a union of circles.

For a round display, choose **Ellipse**, set **Invert: on** and **Blackout: on**,
then Apply. On a single 16:9 output, `Left 21.875 / Top 0 / Width 56.25 / Height 100`
produces a centred physical circle; on a square output use `0 / 0 / 100 / 100`.
These percentages describe the entire combined window layout, not the selected
view. Use other dimensions for oval surfaces or a smaller circular projection.

Controls remain visible above the mask while open so a full blackout cannot lock
you out. Close them with **Tab** for clean projection, and turn **Outlines off**.
Use **F** for borderless output (OS title bars/desktop outside the client aren't
part of the aquarium mask). Blackout emits RGB zero; physical projector black
levels depend on the projector. No edge blending/keystone correction is included.

The preview shows window rectangles in teal, gaps in dark, and exclusions in
coral. Geometry is stored beside settings in `display-layout.json`, separate from
radio preferences and the fish database. It does not auto-detect Explorer or
other applications covering an aquarium: reserve those spaces with manual zones.
Keep windows on your actual monitors; off-desktop client areas are not separately
clipped to monitor hardware boundaries. Mixed-DPI Windows placement still needs
hardware testing. If no valid water can fit a fish, it waits off-view with its
identity retained; the footer reports the count. Removing the obstruction or
changing the layout returns it. Dense crowds still need sufficient swim space.

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

Press **Tab → RX Radio**. The panel stays a compact 432×594 output pixels even on
1440p/4K displays, with separate **Aquarium** and **RX Radio** tabs; it scales down
when a smaller window cannot fit it. Existing graphics/fish controls remain in
the Aquarium tab.

- **USB serial:** refresh the detected ports, choose your RX (or enter `COM4`,
  `/dev/ttyUSB0`, etc.), then **Connect**. Baud rate is 115200.
- **Bluetooth LE:** pair through your operating system first using the RX display
  PIN. Scan, select a device (or enter its address/identifier), then **Connect**.
  Discovery lists nearby BLE devices; finding one does not prove RX compatibility.
- **Network bridge:** enter the bridge host/IP, port and the local path to its
  32-byte token file. This connects to the PC/SBC bridge described below, not to
  an assumed onboard Wi-Fi endpoint.

The panel shows connecting/connected/retrying states and errors. A dropped link
retries every three seconds until **Disconnect**. Disconnect also cancels a
pending attempt; an in-flight radio request may finish first. Discovery and
connection work run on the worker thread, not the renderer. Disconnect before
scanning for another device. The app does not send chat replies or change radio
settings from this panel.

Connection details are remembered beside graphics settings in `rx-connection.json`;
only the token **file path** is saved, never its contents. There is **no automatic
connection at startup** unless you explicitly use `--connect`.

Connecting while running a demo/replay switches to the separate default live
collection; synthetic fish are not copied across. Even an explicit demo/replay
`--database` remains separate. A live `--connect --database PATH` launch still
uses your chosen database. Disconnect leaves the saved live fish swimming.

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

See [v0.1.3 testing notes](docs/TESTING-v0.1.3.md) for UI, cancellation and
connection-lifecycle checks. Physical USB/BLE/RX interoperability remains unverified.

## Hardware and visual scope

| Path | v0.1 evidence |
|---|---|
| Linux x86_64 | Native rendering and operator callbacks tested under Xvfb/Mesa llvmpipe |
| Modern Raspberry Pi | Design target; ARM64 engine wheels exist, no physical Pi validation |
| Original Pi / Zero / 32-bit ARM | **Not established**: packaging, driver and performance gate remains open |
| Windows | Owner tested initial prototype at 256 fish on i7-11700F / RTX 3060; v0.1.2 functionally accepted; v0.1.5 projector/multi-window hardware retest pending, physical RX link unverified, no installer |
| macOS | Opportunistic; untested |
| 1080p/4K | Arbitrary output dimensions and independent render scale; 1080p tested, 4K not benchmarked |
| Video wall | Up to eight native OS windows; three-window offset animation, lifecycle, saved-layout restore and two-window reconstruction tested on Linux Xvfb; Windows/mixed-DPI placement unverified, no multi-host sync/bezel calibration |
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
uv run python tools/deadzones_smoke.py
uv run python tools/projection_smoke.py
uv run python tools/headless_capture.py --demo 16 --preset high \
  --screenshot .local/aquarium.png --run-seconds 6 --settings .local/settings.json
```

On an aquarium-only checkout, the two optional C++/RX integration tests skip
because they require the separate sibling RX source; the aquarium tests still
run. Install the test extra (`uv sync --extra test` or `python -m pip install -e
'.[test]'`) before running pytest.

The rendering commands require Linux Xvfb. They launch only a temporary local X
server (`-nolisten tcp`); no xauth installation or system config change is needed.
Software-renderer timings are not GPU or Pi FPS evidence.

See [v0.1.5 projector testing notes](docs/TESTING-v0.1.5.md), [v0.1.4 testing notes](docs/TESTING-v0.1.4.md), [v0.1.3 radio testing notes](docs/TESTING-v0.1.3.md), [v0.1.2 testing notes](docs/TESTING-v0.1.2.md), [implementation report](docs/IMPLEMENTATION-REPORT.md),
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

### Looking for LoRagotchi-RX - the Aquarium firmware?
https://github.com/DrToxic/LoRagotchi-RX

### Looking for LoRagotchi-DX - the Companion firmware?
Original Author: https://github.com/DarkButterfly85/LoRagotchi-DX

Fork: https://github.com/DrToxic/LoRagotchi-DX

RX/DX firmware source and binaries are not included in this aquarium repository.
