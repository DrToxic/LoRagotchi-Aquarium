# Desktop fish-transfer verification — 2026-10-21

Synthetic native tests only; no live radio or production fish database.

## Coverage

- Conservative area connectivity: shared/overlapping seams, tiny gaps, corner
  contact, U-shaped connected windows, splitting masks, narrow real corridors,
  curved/inverted keep-ins and no outputs.
- Real Bullet corridor reservations and full-outline routes. No departure until
  both ends fit; opaque rectangular versus transparent deadzone boundaries.
- Same model/swimmer/body for an unchanged fish, unchanged roster/snapshot,
  idempotent zero-delta redraws, one journey at a time, cooldown and opt-outs.
- Removal during exit/hidden/entry, coalesced hidden updates, growing fish,
  deferred entry updates, destroy cleanup and closing/reopening all outputs.
- `tools.travel_smoke` checks actual native pixels across 24 departure/entry
  samples plus the fully hidden frame. No diagnostic fish pixels appear in the
  wrong output. It exercises quality rebuilds, native controls/profile saves,
  destination/all-window closure, opaque split, joined seams and a 256-fish idle
  check with no extra topology solves or route attempts. GL debugging is enabled.
- Existing lifecycle suite covers every pickup actor, old-out/new-in, coalescing,
  labels, panoramic crops, projector blackout, 256 arrivals and hold cleanup.
- Retained operator/layout suites cover native window controls, scenery
  relocation, masks, shelves, bubble columns, pins and eight-output lifecycle.

Commands (Linux with Xvfb, isolated settings):

```sh
uv sync --frozen --extra test
uv run --frozen pytest -q
uv run --frozen python -m tools.run_native tools.travel_smoke
uv run --frozen python -m tools.run_native tools.transitions_smoke --demo 8 --preset low --settings .local/lifecycle/settings.json
uv run --frozen python -m tools.run_native tools.operator_smoke --demo 24 --preset low --settings .local/operator/settings.json
uv run --frozen python -m tools.run_native tools.layout_smoke
```

In an isolated source ZIP, two optional sibling-firmware-source checks skip if
that separate firmware checkout is absent. They are not failed aquarium tests.
Mesa/llvmpipe evidence is not Windows/GPU performance proof. Route/corridor checks
are deliberately conservative: a skipped trip is preferable to a visible jump,
clipped teleport or collision. Carrier travel and curved blackout portals remain
future extensions, not advertised features of this build.

## Windows retest

1. Extract into a fresh folder and use the usual install/launch commands. Existing
   display profiles load with transfers Off; no saved fish migration is needed.
2. Arrange two output windows with a visible gap. Enable **Animations → Travel
   between disconnected areas → Frequent**. Allow 20–40 seconds per attempt;
   narrow/crowded layouts can legitimately skip attempts. A small fish in open
   upper water is the easiest first case.
3. Watch a fish leave fully before appearing elsewhere. Confirm appearance/name
   remain unchanged. No radio event or refreshed visit should result.
4. Join the windows edge-to-edge and overlap them: no new journey should start.
   Split one large window with a full-height rectangular blackout. Repeat with
   blackout off: the invisible keep-out must not become a visible swim-through.
5. During a trip, change graphics quality, move/resize/minimize outputs, close
   its destination, close every output, then open a usable view. Check recovery,
   no stuck holds and no missing identity. Include mixed-DPI/fullscreen layouts.
6. Change transfers to Off mid-trip (finishes), then turn all animations off
   mid-trip (stops safely). Restart and confirm the transfer preference persists.
7. If a genuine fish update/removal arrives during travel, confirm latest state
   eventually wins, with no duplicate fish or unwanted re-entry after removal.

Standalone only. HA, firmware, saved visits, expiry, new reef art and fish styles
are outside this release. No GitHub push is implied by producing this test ZIP.
