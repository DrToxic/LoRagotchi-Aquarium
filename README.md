# LoRagotchi-Aquarium · v0.9.0

**Playing the mesh games?** [Two-player setup, rules and troubleshooting](docs/LIVING-AQUARIUM.md#games-using-mesh-messages).

## Native controls

The optional desktop operator now opens at 1100×800 with a persistent sidebar,
readable pixel-sized controls and scrollable smaller-window layouts. See
[Controls and save scopes](docs/CONTROLS.md) for appearance drafts, previews,
separate save actions and the feature map. Home Assistant managed mode remains
display-only and continues to use HA Configuration, not this operator.

## Tidal Garden default scenery

Tidal Garden is now the default native reef, with upgraded animated seagrass.
Reef and Plants have persistent per-object checkboxes in Decorations.
Classic remains selectable under Appearance → Quality → Scenery style.
[Scenery controls and HA configuration](docs/SCENERY.md).

The separate `tools.reef_study` launcher remains available for historical
comparison probes; it is no longer needed to run the new graphics.

## Themes and fish styles

Six built-in themes, persistent editable custom themes, JSON import/export, and
Classic/Rounded/Faceted fish styles. See [Themes](docs/THEMES.md) for controls,
HA configuration authority and the portable data-only format.


A native **Python + Panda3D** aquarium for shared LoRagotchi fish. Real 3D fish,
independent cruise/glide swimming, animated tails/turns, original procedural scenery, adjustable graphics, durable
snapshot storage, and USB/BLE/LAN adapters to the companion **LoRagotchi-RX**
firmware prototype. No web server or Electron renderer.

RX receives a normal DX visit, captures a snapshot, then proactively returns the
original after about four seconds. Returning the original **does not remove the
copy**. No local pet, care or breeding runs on RX. Copies do not age themselves;
sharing again refreshes their appearance.

## v0.6.0 · Configurable fish lifespan

**Aquarium → Fish lifespan** adds optional expiry in hours or days (off by
default). A new share renews the copy; duplicate packets, restarts and window
transfers do not. Expired fish leave through the existing departure animation.
Saved history remains, and manually removed copies stay hidden when changing
this rule. Original pets and radio returns are unaffected.

[Controls, migration and acceptance checks](docs/FISH-LIFESPAN.md).

## v0.5.0 · Fish travel between disconnected areas

**Animations → Travel between disconnected areas** offers Off (the default),
Occasional and Frequent. A fish swims fully out of one water area before entering
another, keeping its identity, model and saved visit. One journey runs at a time;
full-outline routes and landing space are reserved before it leaves.

Adjacent/overlapping windows remain one panoramic tank, not separate aquariums.
Window gaps and splitting deadzones can create separate areas. Transfers use
clear output edges or rectangular opaque blackouts; narrow/crowded layouts may
have no safe route. Existing pickup actors remain for ordinary updates/removals;
this first travel pass uses simple swim-out/swim-in choreography.

[Controls and limitations](docs/DESKTOP-LAYOUT.md) ·
[Verification and Windows retest](docs/TESTING-v0.5.0.md).

Standalone only. No HA, firmware, radio, stored-visit or expiry changes.

## v0.4.0 · Layout-aware scenery and edge shelves

Decorations now automatically seek supported positions outside deadzones.
Valid neighbours stay put; objects that cannot fit wait without leaving invisible
collision bodies. **Decorations → Auto / Pinned** controls each library object,
rock/coral cluster or plant. Automatic placement respects the full projected
shape, preserves hollow ship/arch passages and remembers valid placements.

**Deadzones → Edge shelf: auto** adds a ledge where a rectangular or rounded
screen-edge zone has a suitable flat upper edge and clear water above it. Existing
bubble columns can use these surfaces without increasing their particle budget.

[Controls and limitations](docs/DESKTOP-LAYOUT.md) ·
[Verification and Windows retest](docs/TESTING-v0.4.0.md).

That standalone release added scenery placement and shelves; it did not include
fish transfers, visitor expiry or new reef artwork.

## v0.3.0 · Appearance and bubble columns

Native **Aquarium → Appearance** controls now expose lighting, clock-based
smooth day/night, solid/gradient water, fog, sand tint, effect motion and quality.
Stable seeded bubble columns can rise from the floor or generated shelves using
a bounded shared particle pool. Classic/static remains the default.

[Controls, limits and HA behavior](docs/APPEARANCE.md) ·
[Verification and hardware retest](docs/TESTING-v0.3.0.md).

## v0.2.1 · Radio scrolling fix

Chat history and the Tools activity log no longer disappear abruptly when
scrolled. Scroll ranges now follow the actual rendered text, including wrapping
and emoji, and reset when switching to an empty conversation. No database,
firmware or radio protocol changes. See [verification](docs/TESTING-v0.2.1.md).

## Radio workspace (v0.2.0)

One connection now serves the aquarium **and** the everyday MeshCore client:

- **Connection:** existing USB, Bluetooth and network settings/layout.
- **Chat:** channels and direct messages, UTF-8 composer, local history, unread
  counts, pagination, and honest sent / delivered / unconfirmed status.
- **Contacts:** search/paginate, discovered nodes, add/rename/favorite/remove,
  reset/share routes and import/export MeshCore contact URLs.
- **Channels:** configure slots, standard hashtag keys or supplied private keys;
  replacing/clearing a configured slot requires a second click.
- **Device:** identity/battery/storage, name, RF settings, TX power, coordinates,
  contact/location preferences, clock sync and local/flood advertisements.
- **Tools:** remote login/logout, commands, status, decoded telemetry, route
  discovery/manual paths and local radio statistics.

There is still only **one serial-port owner**. RX events keep their original
commit-before-ACK path. No automatic radio sends, automatic message retries, or
firmware changes are introduced. This is not full stock-app parity: maps, QR
scanning, firmware flashing, signing/identity-key management and raw-packet tools
are not included. [Usage and limitations](docs/RADIO.md).

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
v0.1.2 swimming/collision update. The v0.2.0 Radio workspace needs physical-radio/Windows retesting. This is a source prototype, not a standalone installer.

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

The **first window is the operator/settings window**; the aquarium opens in a
second, undecorated window. Close the settings window to quit the application;
its minimize button leaves the aquarium running.

In an aquarium: **drag anywhere** to move, **drag a 9-pixel edge/corner** to resize,
`Tab` brings settings forward, `F` toggles borderless fullscreen, `N` toggles names,
`V` adds a view, click/right arrow selects fish, and `Esc` closes just that view.
All aquarium views can be closed and reopened without deleting the collection.
In settings, `1…5` changes quality, `Delete` removes the selected copy, and `Tab`
advances between focused fields (otherwise minimizes/restores settings).
End display session requires a second click and only clears local display copies;
it never sends a radio RETURN. New shares can reappear.

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

### Fish arrivals and departures (v0.1.11)

Fish enter from above, settle into open water and begin their normal swimming.
Removing a copy chooses a random, family-friendly exit: a toothless cartoon shark,
a net, a water bag, an open cage or a lift-out glass bowl. Containers descend;
the passenger swims in, then the carrier lifts it beyond the top border.

**A refreshed fish exits with its old appearance, then re-enters with its latest
snapshot.** Repeated updates during an exit coalesce; updates during arrival wait
for that arrival to finish. Identical roster refreshes do not replay animations.
A removal during an update cancels its pending re-entry. Radio RETURN messages
still retain the aquarium copy and do not trigger an exit.

The settings window's **Animations** tab enables/disables animations and chooses
the random pickup styles. With every style unchecked, departing fish simply swim
up and out. Choices survive restarts and graphics presets. At most four pickups
run together; additional departures keep swimming while queued. End display
session hides copies in storage immediately, but their visible departures drain
through this queue. Switching animation off finishes all visual transitions
immediately. Closing the app never waits for an animation.

All actors share the panoramic world and projector masks. The temporary models
live in `tank/assets/transitions/`; editable original geometry is in
`tank/transition_art.py`. No runtime dependencies, database migration or firmware
update are needed. See [v0.1.11 testing notes](docs/TESTING-v0.1.11.md).

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

### Continuous panoramic water (v0.1.10)

Every aquarium window is a crop of **one shared 3D world**, using its actual
**desktop X and Y position**, including negative origins and unequal sizes.
Adjacent windows align fish, scenery and chat in both axes. There are no fade
handoffs or per-window fish assignments. The settings window is excluded from
water bounds, saved output geometry and projector masks.

The sand's far edge sits one-third up the **combined panorama**; its depth varies
between individual views. This replaces v0.1.9's per-window sand anchoring, which
broke continuity at vertical offsets. Upper windows in vertically stacked layouts
receive sand-covered rock shelves. They leave a broad centre opening and an open
foreground swim route between levels. Moving/resizing a view reframes the combined
world and updates the shelves; side-by-side offsets do not create shelves.

Air and channel-chat bubbles travel beyond the **current top of the combined
water** before recycling/removal. Chat keeps its position and cached text through
layout changes. Portrait panoramas crop sides instead of exposing excessive sky.

Aquarium outputs request no OS decorations. Move and resize use the client area,
without depending on a particular desktop's title bar. Native pointer behavior
is tested on Linux X11/Xvfb; Windows, KDE/GNOME/LXDE/Xfce window-manager policies,
XWayland compositor restrictions and mixed-DPI behavior still need device testing.
Select, add, close or fullscreen any aquarium in **Controls → Deadzones**.
The controls remain in their own rectangular window, including with circular masks.

### Decoration library

**Controls → Decorations** lists checkbox toggles for the pirate ship wreck,
ancient stone arch, treasure chest, old anchor and clay pots. The ship and chest
start enabled. The ship's broken middle and the arch's opening are real swim-through
routes: only solid parts have collision boxes. Toggling an object changes both its
art and collisions; fish copies are never removed. Graphics presets preserve choices.

Add static `.egg`/`.bam` models and `decoration.json` in
[`tank/assets/decorations/`](tank/assets/decorations/README.md), then press
**Refresh library**. No application-code edits or new dependencies are required.
The library guide documents placement, collision boxes and an example manifest.

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
(body, fins and tail) stays within the union of non-minimized aquarium client
rectangles. Fish can cross adjoining/overlapping spans, but cannot swim through
a horizontal or vertical desktop gap or missing corner. Adjacent vertical views
are connected; shelves leave open passages.
Disconnected water areas keep their fish until the layout changes. Manual zones work at all
fish depths. **Edges: off** restores unrestricted gap-crossing; zones still apply.

- **Add / Close:** up to eight native windows. Select a view in the dropdown;
  any aquarium may be closed, including the last. New views cascade for placement.
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
  preview outlines are always available. In v0.4.0, protected scenery relocates
  independently of Blackout. Water/sand remain visible unless Blackout is on.

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

Controls stay in their separate, unmasked window, so even full blackout cannot
lock you out. Turn **Outlines off** for clean projection. Outputs are already
borderless; **F** fills the monitor. Desktop outside the client isn't part of
the aquarium mask. Blackout emits RGB zero; physical projector black
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

Press **Tab → Radio → Connection**. The original connection form is retained
inside the new Radio workspace. The controls are 432×724 pixels (scaling down
for smaller windows); Aquarium, Deadzones, Decorations and Animations remain
separate top-level tabs. See [Radio workspace](docs/RADIO.md) for chat and tools.

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
scanning for another device. Connection/discovery does not transmit messages or
change radio settings. Other Radio sub-tabs do so only through explicit actions.

Connection details are remembered beside graphics settings in `rx-connection.json`;
only the token **file path** is saved, never its contents. There is **no automatic
connection at startup** unless you explicitly use `--connect`.

Connecting while running a demo/replay switches to the separate default live
collection; synthetic fish are not copied across. Even an explicit demo/replay
`--database` remains separate. A live `--connect --database PATH` launch still
uses your chosen database. Disconnect leaves the saved live fish swimming.

Use only with RX firmware described in [the RX protocol](docs/RX-PROTOCOL.md).
Stock/DX firmware does not implement this extension. The PC can now send
ordinary messages, but never generates automatic LFG1 replies: RX remains the
sole fish-transfer authority.

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
defaults to the RX extension plus read-only stock-client queries. Add
`--radio-control` on the bridge to permit supported chat/contact/channel/device
actions. Private-key, signing, raw-packet, factory-reset and unrestricted local
CLI commands are not forwarded. Both bridge and desktop need v0.2.0 for the
new Radio workspace. Channel secrets and BLE PINs are filtered from bridge
responses. No onboard WLAN RX build is supplied.

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
| Video wall | Up to eight borderless output windows plus controls; physical panoramic crops, shelves, drag/resize and lifecycle tested on Linux Xvfb; Windows/desktop-environment/mixed-DPI behavior unverified, no multi-host sync/bezel calibration |
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

## Tidal Garden graphics

Tidal Garden is now the default scenery, including shaded animated seagrass. Classic remains available as the simpler alternative. Scenery style is separate from colour themes and quality presets. See [Scenery controls](docs/SCENERY.md).

## Living aquarium candidate

0.9.0 adds dynamic/object bubbles, fish activities, animated water, an opt-in local nursery and manual mesh-message games. See [controls and boundaries](docs/LIVING-AQUARIUM.md). DX egg transfer is not connected.
