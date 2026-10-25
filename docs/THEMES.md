# Themes and fish styles

Six built-ins: **Classic**, **Tropical shallows**, **Deep sea**, **Freshwater**,
**Moonlit**, **Minimal**. Classic retains the original appearance. Theme changes
never alter received fish colours, RGB565 tint, stage, identity or saved visits.
Three global mesh styles: **classic**, **rounded**, **faceted**. Faceted uses flat
face normals, not just a lower quality preset. All variants fit the existing
conservative contact/projected envelope; animated fins remain flexible.

## Standalone

Open **Aquarium → Appearance & advanced graphics → Themes & fish**.
Choose a theme and **Load theme**. Change **Fish style → Apply fish style** to
use a different mesh without changing the water. Native edits apply immediately.

To make a custom theme: load a built-in, edit colours/light in Appearance and
**Apply & save**, then return to Themes, enter a unique lowercase **Custom ID**
and a name, and **Save current look as theme**. This captures the applied look
and chosen fish style. **Load theme** applies the saved result. Save again with
the same selected custom ID to update it. Built-ins cannot be overwritten.

Import/export uses the explicit file path field. Export refuses an existing file;
use a new filename. Import stores a new ID and does not silently replace a theme.
The UI reports malformed files/conflicts. Custom files live in `themes/` beside
the user's settings file, outside the installation. The applied appearance is
saved as a snapshot: editing a library file requires Load theme to reapply it.
Ordinary Appearance edits keep working and don't require a custom theme.

## Home Assistant

Normal selection remains authoritative in **Aquarium → Configuration**:

```yaml
theme_id: tropical
fish_style: rounded
theme_overrides:
  background_top: "#176c80"
  brightness: 0.85
```

**Save + Restart** applies both selections and edited theme content.
`theme_id: current` (default/migration) uses the existing Appearance settings
unchanged. A named theme replaces only its aesthetic fields; old Appearance
values for those same fields do not override it. Use `theme_overrides` for
explicit per-install adjustments. `fish_style: theme` (default) uses the theme's
style; classic/rounded/faceted explicitly overrides it. Missing or broken themes
fall back to Classic with a log message, without resetting other settings.

Open the app's Web UI URL ending in **`setup.html`**, then **Theme library**.
The aquarium root stays unobstructed/display-only. The library offers duplicate,
field editing, JSON import/export and save. Imported JSON opens for review before
save. Built-ins are immutable; choose a unique ID. Saving edits content only,
not the active selection; stale saves are rejected until reloaded.

HA custom files persist at `/data/config/loragotchi-tank/themes/` and survive
image updates/restarts. The page and API use the existing ingress/access guard.
The loopback library process has no HA API token and cannot change fish data,
selection, radio configuration, renderer input or arbitrary files.

## What a theme owns

Palette/background, fog colour/density, sand tint, day/night colour/brightness,
light strength/direction, caustic/shaft strength and decorative motion speeds.
It does **not** own clock mode/timezone/times, fog/shaft enable switches, quality,
FPS, resolution, mesh detail, plant/bubble counts, lighting/caustic enable flags,
decoration selections, window layout, expiry or connection settings. Explicit
effect-off choices stay off. Minimal reduces visual effects, not geometry counts.
Change quality separately when reducing resource use.

## Portable data-only format

```json
{
  "schema_version": 1,
  "id": "my-lagoon",
  "name": "My lagoon",
  "extends": "tropical",
  "appearance": {"sand_tint": "#f1dfb9", "fog_density": 0.01},
  "fish_style": "rounded"
}
```

One built-in parent only; no arbitrary inheritance chains. IDs are 1–48 lowercase
letters/numbers/hyphens, starting with a letter. `current` and built-in IDs are
reserved. Maximum128 custom themes,16KiB each. Types, finite ranges, colours and
field names are validated; symlinks are not loaded. Files contain only these
manifest fields—never collection/history, credentials or connection settings.
Images, scripts, custom model packs, per-fish styles and outlined shaders are
not supported. Original Tidal Garden reef artwork has shipped; see
[Scenery](https://github.com/DrToxic/LoRagotchi-Aquarium/blob/main/docs/SCENERY.md). These exclusions are not outstanding owner decisions.

## Verification

`python tools/run_native.py tools.themes_smoke` exercises native theme pixels,
Classic restoration,56 stage/colour variant envelopes, pose/simulation continuity,
mid-exit old/new sequencing, controls/export and256-fish restyling. In the HA
source use `--managed` for its single display-only window. Unit tests cover
migration/authority, corrupt manifests, safe persistence and API write boundaries.
Native software-render evidence is not Windows/GPU/HAOS performance qualification.
