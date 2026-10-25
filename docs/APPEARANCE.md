# Appearance and bubble columns

## Desktop

Open **Aquarium → Appearance** in the native controls window. The five pages
are Light, Cycle, Water, Bubbles and Quality. **Apply & save** validates and saves
all five pages. Invalid values leave the running scene and saved file unchanged.
VSync changes require a restart; the other controls apply immediately.

Preview day/night uses the currently applied settings, not unsaved entries.
**Current time** ends the preview. Preview is never saved. **Reset appearance**
restores Classic colours, static lighting and no columns while retaining quality,
fish, radio and window preferences. Graphics presets do not reset appearance.

## Light and time

- Static uses the day brightness/tint. Clock smoothly transitions between the
  chosen day/night targets. Fade begins at each HH:MM start time and is limited
  to fit the schedule, including schedules across midnight.
- Desktop defaults to `local`; an IANA zone such as `Europe/London` gives an
  explicit schedule. Timezone data is bundled for platforms without a system
  zone database. DST follows local wall time; clock corrections blend smoothly.
- Overall/day/night brightness and ambient/surface/fill strengths are 0–2.
  Zero deliberately allows blackout. Day/night tints use `#RRGGBB`.
- Light shafts can follow the caustics preset, remain on, or stay off. Caustic
  and shaft strength, caustic speed and plant sway/speed are independently
  adjustable. Night dims the world, background, fog and effects together;
  fish names and chat text retain independent legibility.
- Lighting-off is the unlit performance setting, not a substitute for night.
  No real-time shadows or extra rendering passes are introduced.

## Water

Classic retains the original gradient and fog colours. Solid uses the top
colour; Gradient uses both top/bottom colours. Backgrounds are world-space, so
multiple desktop outputs share one scene rather than tiled backdrops.
Water fog can be disabled, tinted or given density 0–0.1. `classic` preserves
its original colour exactly. Sand tint multiplies the existing textured sand,
including generated shelf caps; white leaves it unchanged.

## Bubble columns

- **Column count:** 0–16, independent of the scattered Ambient bubbles setting.
- **Placement:** floor, generated shelves, or mixed. Shelves-only with no usable
  shelves produces zero columns, not floating emitters.
- **Position seed:** stable seeded positions; change the integer to reshuffle.
  Layout changes retain valid anchors and relocate invalid ones. Solid scenery
  and blocked rising paths are rejected; logs show actual/requested counts.
- **Total column bubbles:** 1–300 across all columns, **not per column**. A budget
  smaller than the requested column count also limits placed columns. Ambient
  bubbles remain separately bounded at 100. Start with 2–3 columns and 60 total.
- Spread, size and rise speed are configurable. Bubble nodes are pooled/recycled;
  increasing count does not multiply the particle budget or create per-window
  copies. Particle count and transparency still have a rendering cost.

Generated shelves currently come from stacked desktop windows. Screen-edge
mask shelves, manual emitter placement and decoration deadzone exclusion are
not part of this version.

## Home Assistant

HA uses **Configuration → appearance**, then **Save + Restart** for manual edits.
There is no native controls window. The selected cycle runs continuously after
startup without further restarts. For example:

```yaml
appearance:
  mode: ha_sun
  timezone: ha
  day_start: '07:00'
  night_start: '19:00'
  transition_minutes: 60
  day_brightness: 1.0
  night_brightness: 0.2
  column_count: 3
  column_placement: floor
  column_particles: 60
  column_seed: 17
```

HA sun uses `sun.sun` elevation: night below −6°, day above +6°, smooth twilight
between. Timezone comes from HA configuration, not the container clock. Unavailable,
disconnected or more than 120-second-old sun data falls back to the clock schedule;
if no HA timezone is known yet it uses UTC and reports the fallback in Logs.

Home Assistant receiver mode shares its existing authenticated WebSocket. Demo
and dedicated-RX modes use a separate read-only state observer, with no MeshCore
service calls. The renderer receives only a small local sun/timezone snapshot,
never the HA token. Observer failure cannot stop fish intake. HA currently has
one window and no generated shelves: choose floor or mixed for visible columns.

## Compatibility

Settings schema 2 accepts older files, preserves unknown fields and validates
known fields individually. Loading a malformed file does not modify it. Before
an explicit save replaces a file with validation warnings, its original bytes
are retained beside it as `settings.json.pre-migration[.N].bak`.

Theme import/export and global fish styles are documented in [Themes](THEMES.md);
the shipped Tidal Garden reef is documented in [Scenery](SCENERY.md). Image
backgrounds are not supported. Fish identity, received colours/stages, databases,
radio protocol and firmware are unchanged. Appearance changes do not rebuild fish; geometry/detail changes still
use the existing state-preserving rebuild path.

## Age-based genetic colour expression

Fry and young express the genes already received; there is no new random choice,
setting, save migration or radio message. Classic, Rounded and Faceted use the
same rules. Adult and elder appearances are unchanged.

| Stage | Body | Tail and fins | Body markings |
| --- | --- | --- | --- |
| Fry | Ivory with 25% primary colour | Ivory with 62.5% primary colour | None |
| Young | Ivory with 62.5% primary colour | Ivory with 75% secondary colour | None |
| Adult/elder | Existing full genetic palette | Existing appearance | Existing detailed markings |

The percentages match DX's juvenile-colour implementation: primary is `body`,
secondary is `scales`, and ivory is RGB565 `0xFFBC`. Aquarium uses its existing
softer palette and float-precision 3D shading rather than firmware sprite pixels
or RGB565 channel rounding. Neutral eye rims, dark pupils and bright glints stay
readable; eye genes first express at adulthood. Colour belongs to each mesh, so
it follows the body, tail and pectoral joints through turns and animations.

Intentional monochrome alleles retain their received tint without an ivory cast.
The current Aquarium snapshot/receiver paths support the legacy palette, not H1;
this rendering change does not add or alter H1 decoding, persistence or adoption.
DX's H1 conversion remains on the firmware side where already supported.
