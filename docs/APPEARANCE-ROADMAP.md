# Aquarium appearance settings — inventory and proposed design

Date: 2026-10-21. Requester: DrToxic.

Status: design proposal, not an implemented feature set or publication request.
Inspected desktop `af0fa37` and HA `a005eb3` (preview.5). The HA product has
evolved since the desktop release; changes must preserve its managed,
single-window rendering and HA-owned configuration.

## 1. Current settings

| Area | Available now | Desktop exposure | HA exposure |
| --- | --- | --- | --- |
| Quality | compatibility, low, balanced, high, ultra | Native selector | Configuration selector |
| Internal resolution | Render scale 0.25–2 | Native slider 0.25–1.5; CLI/file up to 2 | Optional override 0.25–2 |
| Mesh detail | 8–48 | Preset, CLI or settings file | Optional override |
| Plants / air bubbles | 0–100 each | Preset, CLI or settings file | Optional overrides |
| Scene lighting / caustics | On/off | Preset, CLI or settings file | Optional overrides |
| Frame rate / VSync | FPS cap; VSync on/off | Preset, CLI/file; FPS 10–240 | FPS 10–60, default 20; VSync default off |
| Fish names / channel chat | On/off | Native controls; names currently runtime-only | Configuration; channel bubbles apply to legacy RX mode, not HA MeshCore chat |
| Decorations | Anchor, pots, wreck, arch, chest | Native toggles and Refresh library | Configuration toggles for bundled items |
| Fish lifecycle | Arrivals/departures on/off; shark/net/bag/bowl/cage selections | Native Animations page | Configuration |

Desktop additionally has output/fullscreen/panorama/deadzone controls. Those are
not appearance themes and must not be reintroduced into HA's managed view.

The existing quality presets mix performance and aesthetics: changing a preset
changes plant/bubble counts and lighting/caustics as well as mesh detail, frame
rate and render scale. A new visual theme should not silently reset those
performance decisions.

## 2. Existing renderer values which can become settings

These already exist in code, but are not configurable:

| Component | Current implementation | Proposed controls |
| --- | --- | --- |
| Ambient light | Fixed blue-water light | Ambient brightness and colour |
| Main surface light | Fixed directional light, heading −35°, pitch −65° | Strength, colour, heading and elevation |
| Fill light | Fixed weaker directional light | Strength and colour; direction under Advanced |
| Water fog | Fixed RGB colour, exponential density 0.012 | Fog enabled, colour, density |
| Background | One fixed two-colour world-space gradient | Solid/gradient style and colours |
| Sand | Generated textured floor | Colour/tint and texture selection |
| Rocks / coral / plants | Fixed geometry/layout and generated palettes | Palette/tint; visibility options where collision geometry can be updated consistently |
| Caustics | Moving translucent textured floor; fixed opacity and UV speeds | Strength and movement speed |
| Light shafts | Three translucent shafts, currently coupled to caustics | Separate enabled/strength controls |
| Plant sway | Fixed speed/amplitude | Optional motion strength/speed |
| Fish rendering | One procedural body shape and fin layout | Selectable rendering style, requiring new style implementations |

Turning lighting off does not disable the unlit background, caustics or light
shafts. A real night mode must adjust these too; merely dimming the main light
would leave an implausibly bright background and glowing sand.

## 3. Proposed user-facing groups

### Appearance

- Theme: **Classic** (unchanged default), **Tropical shallows**, **Deep sea**,
  **Freshwater**, **Moonlit**, **Minimal**.
- Background: solid colour, vertical gradient, or an optional local image.
- Water colours, fog strength, sand colour and scenery palette.
- Decoration selection stays separate, with an explicit option to apply a
  theme's suggested decoration defaults.
- All outputs share one world-space appearance. Do not tile backgrounds per
  desktop window or produce seams across a panorama.

The names above are proposed presets, not existing or already-produced art.
An image is a backdrop, not a replacement for the 3D aquarium.

### Lighting

- Mode: **Static**, **Clock schedule**, **Home Assistant sun**.
- Overall, ambient and main-light brightness; colour/warmth; advanced direction.
- Separate day and night brightness/colour targets, with a minimum fish
  visibility floor unless the user deliberately chooses blackout.
- Dawn/dusk transition duration, manual preview time and reset to current time.
- Caustics and shafts fade with the cycle; labels retain independent legibility.

Clock schedule uses explicit morning/evening times and an IANA timezone. In HA,
use the configured HA timezone, not the container's implicit UTC or the agent
owner's timezone. Handle midnight crossings, DST and start/restart at any phase.
Use wall-clock time for phase and monotonic elapsed time for short blending.

HA sun mode should read the existing `sun.sun` state/attributes through the
already authenticated backend and pass a small visual state to the renderer.
This requires a new subscription/IPC message; it does not exist today. Keep API
tokens and network I/O out of the renderer. On unavailable/stale sun data, use a
documented fixed schedule fallback and report the fallback in diagnostics.

Desktop geographic sunrise/sunset can be a later optional Astral adapter if
requested. Fixed schedules need no location or external service. Reuse the
existing HA Sun integration rather than calculating astronomy twice.

### Fish style

- **Classic**: preserve the current geometry and appearance.
- **Rounded/cartoon**: fuller body and softer fins/eyes.
- **Low-poly**: deliberately faceted shapes, not merely a lower quality preset.
- **Flat/outlined**: a distinct rendering treatment; outlines need separate
  feasibility/performance qualification before becoming a promised preset.
- Advanced later: per-fish style overrides or stable mixed styles, keyed by the
  full owner identity rather than name or fish ID.

Body/scales/eye colours, RGB565 tint and stage remain the received fish's data.
Styles change local presentation, not saved snapshots, radio messages or the
source pet. No theme silently randomises or recolours the incoming collection.

Different silhouettes must supply compatible tail/fin attachment points and
correct physical dimensions. Keep collision clearance, selection, labels and
old-appearance exit/new-appearance entry working. This is more work than adding
a dropdown. Start with a global style; per-fish overrides can follow.

## 4. User-creatable themes

Use a versioned, data-only `theme.json` plus optional local assets. Reuse Panda3D
and the current asset-loader patterns; no Python plugins, remote asset fetches
or new rendering engine are needed for the first version.

Example of the proposed format (not loadable by the current app):

```json
{
  "schema_version": 1,
  "id": "my-lagoon",
  "name": "My lagoon",
  "extends": "classic",
  "background": {
    "style": "gradient",
    "top": "#246E80",
    "bottom": "#031723"
  },
  "water": {"fog_colour": "#124854", "fog_density": 0.01},
  "lighting": {
    "day": {"brightness": 1.0, "colour": "#FFF0D6"},
    "night": {"brightness": 0.2, "colour": "#709ACB"}
  },
  "scenery": {"sand_colour": "#ACA783"},
  "fish_style": "classic"
}
```

Suggested first-version rules:

- Built-in themes are immutable; Duplicate creates an editable user theme.
- User themes live in persistent user data outside the installation/container
  image, so upgrades do not erase them. Existing custom decoration folders inside
  the source tree are not an adequate HA persistence mechanism.
- A user theme may extend one built-in theme; avoid arbitrary inheritance chains.
- Validate types, finite numeric ranges, colour syntax, asset dimensions/size,
  relative paths and references. A bad optional pack falls back to Classic with
  a readable error, not a full reset of aquarium settings.
- Import/export includes a manifest and its own assets only: never fish data,
  histories, connection settings, tokens or unrelated files.
- Desktop: appearance controls with Duplicate/Save/Reset and pack import/export.
- HA: normal controls stay in HA Configuration. A later theme-library page under
  the existing setup UI can provide upload/export/duplicate for web-only users;
  the aquarium view stays unobstructed and no native config window returns.
- In HA, the selected theme ID and overrides remain HA configuration authority;
  the library page edits theme content, not a competing hidden selection state.

## 5. Implementation shape and constraints

One renderer-side settings model and appearance implementation should serve both
products, with separate desktop and HA adapters. The repositories are currently
separate and are **not** automatically synchronised: shared changes need explicit
porting/testing, and the HA generated package must be refreshed from its source.
Do not edit generated `loragotchi_aquarium/tank/` copies independently.

Separate three layers:

1. Performance settings: resolution, FPS, geometry detail, effect budgets.
2. Theme: colours, palettes, materials, background and available style choices.
3. User overrides and schedule: selected theme adjustments, clock and visibility.

Selecting a theme must not change quality, radio configuration, stored fish or
window layouts. Explicit graphics overrides continue to win over quality
presets. Turning an effect off for performance wins over a theme asking for it.

Colour/light/fog updates should mutate existing nodes. Do not call the current
full `rebuild_scene()` on each clock tick: it recreates scenery and fish nodes.
Only geometry/asset changes should rebuild, preserving animation state. Keep
day/night processing lightweight for HA's observed software renderer.

Current `Settings.load()` constructs the dataclass directly from JSON and falls
back to all defaults on invalid/unknown fields. Add explicit migration and
field-level validation before introducing a larger versioned settings surface;
preserve existing values and original files on migration failures.

Current HA options apply through Save + Restart. New manual settings should use
that honest contract initially; the selected clock/sun cycle must then run
automatically without restarts. Live HA sliders/entities are a separate feature,
not something a configuration schema alone provides.

## 6. Recommended delivery order

1. **Expose and separate:** document current fields, add missing desktop controls,
   preserve HA overrides, establish versioned appearance settings and Classic.
2. **Lighting and backgrounds:** brightness/colour/fog, solid/gradient backgrounds,
   clock-based dawn/day/dusk/night, then HA sun input. Preserve today's appearance
   exactly when Classic/static defaults are selected.
3. **Theme library:** several deliberate presets, persistent custom manifests,
   duplicate/import/export; optional image backgrounds after asset validation.
4. **Fish styles:** rounded and faceted variants first; outlined/custom models
   only after native pixel and performance qualification.

For a first implementation, phases 1–2 form a useful bounded release. Theme and
fish-style frameworks should not delay exposing settings that already exist.

### Follow-on: configurable bubble columns

Requested by DrToxic on 2026-10-21, after reviewing the appearance design.
Schedule after the lighting/background foundation; this adds to the plan and
does not resume the currently paused implementation.

The current `AirBubbles` implementation distributes individual bubbles across
the tank and recycles them from below the main sand floor. Its `bubbles` count is
not a number of emitters, and generated shelves are not spawning surfaces yet.
Extend this existing implementation rather than introducing a particle engine.

- **Column count**, with zero disabling columns independently of ambient bubbles.
- **Placement mode:** main floor, generated shelves, or a mixture. Manual
  positions can follow automatic placement rather than delaying the first pass.
- **Stable random placement:** retain a seed and offer an explicit Shuffle action;
  columns should not jump to new spots every launch, graphics change or frame.
  For HA's configuration-only first version, a seed field can provide the same
  reroll without pretending a Save + Restart option is a live action.
- **Appearance:** emission density/rate, column width/spread, bubble size range,
  rise speed and gentle lateral drift. These are proposed controls, not current
  capabilities; final limits depend on native performance checks.
- **Surface-aware emitters:** use generated shelf top coordinates and main-floor
  geometry, with edge clearance and spacing between columns. Avoid solid
  decorations and blocked upward paths; do not spawn inside rocks or beneath a
  shelf when a clear rising column is intended.
- **Layout changes:** preserve valid emitter anchors; deterministically relocate
  only invalid ones when shelves are regenerated. If insufficient valid sites
  exist, report the actual placement count rather than stacking emitters.
- **Continuous panorama:** one world-space column across all relevant outputs,
  not a separate emitter for each window or duplicate copies on overlapping views.
- **Performance:** pool/recycle particles, bound the total active bubble budget
  across ambient bubbles and all columns, and avoid allocation per frame. Raising
  the column count must not silently multiply an unlimited particle workload.
- **Lighting:** use the new appearance/day-night treatment. Keep the option open
  for themes to suggest column appearance later, without overriding the user's
  count or graphics budget.

Verify zero/one/multiple columns, floor/shelf/mixed placement, deterministic
reload/shuffle, resized/rebuilt shelves, occlusion and shared-window continuity.
No radio, fish snapshot or collision-body behaviour needs to change for these
decorative particles. Exact column limits and performance remain unmeasured.

## 7. Acceptance evidence required for implementation

- Existing settings migrate without losing performance, decoration or animation
  preferences; changing appearance does not alter saved fish or radio behavior.
- Native screenshot checks at day/night/twilight and with lights/caustics/shafts
  disabled; text remains legible and the default Classic appearance is retained.
- Clock tests include midnight, DST, restart, missing timezone and unavailable
  HA sun state; no dependency on a live radio or the host's actual current time.
- Changes keep current fish motion and transition sequencing intact, with no
  per-tick scene/model reconstruction.
- Desktop panorama views remain continuous. HA still has one display-only view,
  working read-only ingress and persistent custom themes across package updates.
- Scene-density/shape changes update collisions consistently. Fish-style tests
  cover all stages and the supported colour/tint combinations.
- Reuse existing native and packaging suites for affected areas. Software-render
  timings are not claims about Windows/GPU or physical HA host performance.

## Evidence and existing-solutions preflight

- Desktop: `tank/settings.py`, `tank/options.py`, `tank/aquarium.py`,
  `tank/art.py`, `tank/decorations.py`, `tank/habitat.py` at `af0fa37`.
- HA: the same renderer/art sources plus `tank/ha_settings.py`,
  `homeassistant/config.yaml.in`, `homeassistant/translations/en.yaml` and
  `tank/ha_api.py` at `a005eb3`. Desktop and HA `tank/art.py` are byte-identical.
- [Panda3D lighting](https://docs.panda3d.org/1.10/python/programming/render-attributes/lighting)
  and existing AmbientLight/DirectionalLight/Fog nodes cover the first pass.
- [Home Assistant Sun](https://www.home-assistant.io/integrations/sun/): upstream
  documentation confirms location-based sunrise/sunset and elevation/azimuth.
- [Astral](https://github.com/sffjunkie/astral): existing Python solar calculations;
  PyPI reports version 3.2. Optional future desktop capability, not an installed
  dependency or a maintenance guarantee.

No application source, installed HA configuration, firmware or GitHub content
was changed while preparing this inventory.


## Desktop layout follow-on (2026-10-21)

DrToxic requested these together with, or shortly after, bubble columns. Queue
this desktop-only pass immediately after the appearance/columns build:

- Optional shelves attached to water-facing edges of screen-edge deadzones.
  Expose their usable top faces through the same surface interface as generated
  stacked-window shelves so bubble emitters can use them. Work out rectangle,
  curved and inverted-mask semantics before promising every shape. HA keeps no
  deadzone/operator UI.
- Disconnected visible tank regions (for example windows surrounding another
  application) can exchange fish using renderer-only departure/re-entry
  transitions. Preserve identity, appearance, simulation continuity and stored
  copies; do not create arrivals/returns on the radio or delete/reinsert fish.
  Use occasional transfers with rate limits, a valid destination and a recovery
  path if that view closes. Distinguish these from old/new snapshot refreshes.
- Keep decorations out of deadzones using full projected footprint and matching
  collision proxies, not only object centres. Auto-placement should relocate or
  omit unplaceable objects rather than block swimming invisibly. Keep explicit
  manual placement stable and show conflicts. Account for all active outputs,
  overlaps and masks; retain the continuous world rather than per-window clones.

This is additional planned work, not implemented by the current appearance
modules. No extra firmware, HA receiver or live-radio changes are implied.


## Implementation resumed and art-direction reference (2026-10-21)

The owner subsequently said “Sweet. Let’s do it!”: phases 1–2 and bubble columns
are being implemented in isolated desktop/HA feature worktrees. Earlier pause
language above records the planning history, not the current authorization.
No publishing/deployment request is implied.

The owner supplied a SereneScreen Marine Aquarium reference image and wants a
similarly polished, calm reef experience without directly copying its artwork
or scene. Keep the current lightweight native renderer; improve original art,
feel and behavior beyond this settings release. Treat the reference as mood and
composition, not an asset source or a request for photorealism.

Visual follow-on priorities:
- An original reef composition with foreground/middle/background layers,
  asymmetric focal structures, contrasting silhouettes and open swimming water.
- Cohesive sand/rock/coral materials with texture detail and baked shading where
  useful; shared geometry, instancing/batching and limited transparent layers.
- Readable fish silhouettes, restrained fin/body animation, natural pauses and
  changes of direction; retain LoRagotchi identity, received colours and stages.
- Subtle local motion (plants, sparse bubbles, slow caustics) instead of making
  every object animate. No expensive real-time reef shadows by default.
- Quality tiers must reduce cost without destroying the intended composition.
  Compare frame time, draw calls, memory and geometry/effect budgets with the
  current scene; software-renderer results are not Windows/GPU/HA host proof.
- Produce a small original scene study and measured prototype before expanding
  the asset library. Theme packs/fish styles remain a separate documented phase.

Current release still covers controls, lighting/time cycles, solid/gradient water
and pooled bubble columns, not reef assets or the desktop layout follow-on above.
