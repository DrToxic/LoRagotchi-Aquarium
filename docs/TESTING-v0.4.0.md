# Desktop layout verification — 2026-10-21

Synthetic native tests only; no live radio or production fish database.

## Checks included

- Unit regressions for automatic relocation, unchanged neighbours, collision
  ownership, pins/no-fit recovery, cached-position restore/revalidation, exact
  edge/seam eligibility, edge shelf envelopes and profile-v1 migration/backup.
- Native layout suite: six flat-colour pixel checks across all three mask shapes
  in normal/inverted modes; protected scenery has no forbidden diagnostic pixels
  outside a declared two-pixel contour tolerance. Includes physical solids,
  pins, shelf emitters, native controls, eight outputs, non-last/all-window close
  and recovery, 256 fish and no idle-frame placement solves.
- Default static reef batching compared with the original scenery construction:
  zero changed pixels at 960×540. This excludes fish, plants and water effects
  from the comparison and is not a whole-scene deterministic benchmark.
- Existing appearance, operator, transitions, projection and framing suites are
  retained. Projection tests disable automatic scenery reflow to isolate the
  blackout compositor; the new layout suite tests mask-aware scenery separately.

Commands (Linux with Xvfb, isolated settings):

```sh
uv sync --frozen --extra test
uv run --frozen pytest -q
uv run --frozen python -m tools.run_native tools.layout_smoke
uv run --frozen python -m tools.run_native tools.layout_baseline
uv run --frozen python -m tools.run_native tools.appearance_smoke
uv run --frozen python -m tools.run_native tools.operator_smoke --demo 24 --preset low --settings .local/operator/settings.json
uv run --frozen python -m tools.run_native tools.transitions_smoke --demo 8 --preset low --settings .local/transitions/settings.json
uv run --frozen python -m tools.projection_smoke
uv run --frozen python -m tools.framing_smoke
```

No Windows/GPU performance claim follows from Mesa/llvmpipe. Layout changes can
do more work than steady-state frames; reflow is event-driven and drag-time
searches are deferred. `.local/layout/report.json` records the native fixture's
renderer, per-edit costs, diagnostic pixel counts and 256-fish frame sample.

## Owner Windows retest

1. Back up the settings directory. Open the ZIP in a fresh folder and use the
   usual install/launch commands; retain your settings path if desired.
2. Add/move/resize a deadzone over the wreck and reef. Confirm Auto objects move
   where supported, valid neighbours stay put and hidden objects return later.
3. Pin an object, cover it with a zone and remove the zone. Confirm its saved
   checkbox stays enabled and it returns to the pinned position.
4. Enable an edge shelf on a bottom/side-attached rectangular zone. Try rounded,
   elliptical, inverted and too-small variants; inspect the reason when omitted.
5. Enable shelf/mixed columns. Check anchors, motion, mask boundaries and counts.
6. Drag/resize several windows, test mixed DPI/fullscreen/minimize, close an
   arbitrary output, close all outputs, reopen, then save/restart the layout.
7. Scroll every Decorations category slowly at normal and scaled UI sizes.
   Check the last rows, pins, refresh and reset controls.

Fish transfers, expiry, new fish styles and new reef assets are not in this ZIP.
