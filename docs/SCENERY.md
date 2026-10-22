# Scenery

Tidal Garden is the default. Existing settings without a scene choice adopt it;
explicit Classic choices, fish/history, themes, quality and library selections
are preserved. No firmware change is required.

## Standalone controls

- Appearance → Quality → Scenery style: Tidal Garden or Classic, then Apply & save.
- Decorations → Reef / Plants: check each object to show it, uncheck to hide it.
- Selections persist through restart, refresh, quality changes and scene switches.
  Each scene has its own object identities. A lower plant count can temporarily
  omit a saved selection; increasing it restores that selection.
- Hiding a solid removes its fish-collision proxy too. Auto/Pinned placement stays
  independent: checked objects can still wait for space behind a mask.
- Plant count remains 0–100; sway is under Appearance → Light.
- Colour themes, including the Classic theme, do not select the scenery style.

## Home Assistant

Configuration → Scenery style (`scene`): `tidal-garden` or `classic`.
Save and restart. The managed aquarium remains display-only; use HA configuration
for plant count, sway, library decoration switches and other graphics settings.
The source's optional standalone operator also has Reef/Plants checkboxes.

Classic can cost less on software rendering. Local llvmpipe measurements are
not Windows/GPU or HA hardware performance guarantees.
