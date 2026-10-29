# Changes

This history preserves the versioned and feature notes previously in the README. Current usage and setup remain in the [README](README.md).

## v0.10.0 · Native controls redesign

The optional desktop operator now opens at 1100×800 with a persistent sidebar,
readable pixel-sized controls and scrollable smaller-window layouts. See
[Controls and save scopes](docs/CONTROLS.md) for appearance drafts, previews,
separate save actions and the feature map. Home Assistant managed mode remains
display-only and continues to use HA Configuration, not this operator.

The sidebar has eight sections, selected-fish and status cards, grouped appearance drafts, an applied-scene preview, explicit save scopes, reset/cancel and discard confirmation. See [controls](docs/CONTROLS.md).

## v0.9.1 · Juvenile colours

Fry and young use age-based genetic colours with neutral eyes; adult appearance and monochrome genetics remain unchanged. No radio protocol or persistence changes.

## v0.9.0 · Living aquarium

0.9.0 adds dynamic/object bubbles, fish activities, animated water, an opt-in local nursery and manual mesh-message games. See [controls and boundaries](docs/LIVING-AQUARIUM.md). DX egg transfer is not connected.

## v0.8.0 · Tidal Garden

Tidal Garden is now the default native reef, with upgraded animated seagrass.
Reef and Plants have persistent per-object checkboxes in Decorations.
Classic remains selectable under Appearance → Quality → Scenery style.
[Scenery controls and HA configuration](docs/SCENERY.md).

The separate `tools.reef_study` launcher remains available for historical
comparison probes; it is no longer needed to run the new graphics.

## v0.7.0 · Themes and fish styles

Six built-in themes, persistent editable custom themes, JSON import/export, and
Classic/Rounded/Faceted fish styles. See [Themes](docs/THEMES.md) for controls,
HA configuration authority and the portable data-only format.

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

## v0.1.7 · Windows Unicode fix

v0.1.7 fixes a Windows-only crash in the v0.1.6 emoji coverage check. Existing
collections/settings remain compatible; no database reset or firmware update is
needed. See [Windows Unicode regression checks](docs/TESTING-v0.1.7.md).

## Earlier feature and usage notes

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


## Tidal Garden graphics

Tidal Garden is now the default scenery, including shaded animated seagrass. Classic remains available as the simpler alternative. Scenery style is separate from colour themes and quality presets. See [Scenery controls](docs/SCENERY.md).
