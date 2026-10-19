# v0.1.4: visible swimming areas, more windows and Deadzones

## Implementation

Reuses Panda3D native outputs, DirectGUI and the existing Bullet simulation; no
new library, second renderer, radio operation or firmware change.

- Up to eight independently movable views, each owning its output, off-axis lens,
  overlay, input prefix and cleanup. Arbitrary secondary views can close, not just
  the last one. One shared simulation and identity set remain.
- Default visible-area enforcement uses the union of non-minimized client
  rectangles, not their bounding rectangle. Exact interval coverage preserves
  adjoining/overlapping seams and excludes gaps/missing corners.
- A conservative stage-scaled sphere encloses the entire animated fish, including
  fins/tail. Its exact perspective footprint is checked at all depths. Swept
  footprint boxes prevent physics steps tunnelling across even narrow gaps.
- Goal selection/obstacle preview prefer visible routes. The hard constraint is a
  final movement guard, not just steering or a mask drawn over hidden fish.
  Fish cannot traverse disconnected display regions during ordinary swimming.
- Layout changes preserve still-visible fish and relocate newly hidden ones into
  available water. If no usable placement exists, fish wait hidden with their
  identity/body retained and collision mask disabled; footer reports the count.
  Later layout/roster changes retry placement. Heavy crowding remains possible.
- Third compact tab contains window management, preview, 16 editable rectangular,
  rounded-rectangular or elliptical exclusions, percent coordinates, enabled
  state, click-to-place draft, Apply/Delete and optional per-window outlines.
- `display-layout.json` version 1 stores zones/edge protection and explicitly saved
  window geometry. Missing/invalid settings fall back safely. Saved window
  geometry restores on normal launch; `--wall-columns N` overrides its geometry.
  Text focus protects aquarium shortcuts in all three tabs.

## Local evidence

```sh
uv sync --extra test
uv run pytest -q
uv run python tools/run_render_smoke.py
uv run python tools/options_smoke.py
uv run python tools/deadzones_smoke.py
```

Unit/integration suite: 60 passed with sibling RX sources available. Two optional
firmware-source tests skip in the standalone archive (58 pass, 2 skip).

New geometry/simulation tests cover union seams/overlap/missing corners, tiny
gaps, every shape, disabled zones, perspective-sphere containment at varied depths,
swept traversal, bad/NaN/infinite settings, negative desktop geometry persistence,
offscreen repair, disconnected regions, and all-water-excluded recovery without
identity loss. Existing collision/motion/storage/transport tests are retained.

A separate 256-fish diagnostic ran 60 simulated seconds in disjoint vertically
offset windows plus an ellipse exclusion. All 153,600 sampled fish positions
retained their whole-outline visibility and none were parked. The software host
needed about 65 seconds; this is a simulation diagnostic, **not GPU FPS**.

Native Xvfb/Mesa tests verify:

- Compact third tab at 720p/1440p/4K and fit-down at 800×450; screenshot inspected.
- Three differently sized/offset native windows with changing aquarium pixels in
  every output, visible zone outlines, and retained fish identities.
- Real editor callbacks: create all shapes, reject invalid coordinates, enable/
  disable, draft click placement, typing/shortcut guards and persistence.
- Close a non-last window through the window-event path; close only the input's
  originating window using its Escape event; three multi-view reopen cycles with
  stable output/camera/input-node counts; open eight outputs and reject a ninth.
- Fresh-process restoration of saved three-window geometry/zones, plus explicit
  single-window override. No network/radio access in these tests.
- Existing 256-fish rendering, cached name/rename handling, two-window frozen
  reconstruction (mean sampled RGB difference about 0.00005), independent resize,
  fullscreen/restore, move/focus buffer reuse, removal/session clear and RX UI.

Xvfb has no window manager: programmatic close plus explicit native-event handler
is a cleanup test, not a real title-bar click. Linux software GL is not evidence of
Windows/NVIDIA/mixed-refresh frame pacing. OS placement and per-monitor DPI on
Windows still require the owner's setup; no physical RX operation was performed.

## Owner retest

Extract the archive into a fresh folder, then:

```sh
uv sync
uv run loragotchi-tank --demo 256 --preset high --wall-columns 2
```

1. Arrange two windows like the reported offset layout. Keep **Edges: on** and
   watch the missing upper-left area: fish should turn inside displayed water,
   including fins/tails. Disconnected windows should not exchange fish invisibly.
2. Tab → Deadzones → Add; move the new window to a third area/monitor. Make views
   touch if fish should swim continuously between them. Resize/move/fullscreen
   and close a middle view. Newly hidden fish can relocate when geometry changes.
3. New zone → choose Rectangle/Rounded rectangle/Ellipse. Enter layout-relative
   percentages (Left/Top start at the combined layout's top-left), then Apply.
   Use `<`/`>` to revisit zones. Test corners, edges, depth, disable and Delete.
   Use different width/height percentages to make a physical square/circle on a
   non-square layout. Outlines helps align zones; it does not black out scenery.
4. Save layout, exit and relaunch without `--wall-columns`; confirm positions,
   sizes, count and zones restore. `--wall-columns 1` is the recovery override
   for a changed monitor setup. It does not delete zones; disable/delete in Tab.
5. Check names, all tab controls, input focus and frame pacing with your usual
   fish population. Increase water area or reduce demo count if overcrowded.

This is a manual exclusion system, not OS window-occlusion tracking. Explorer,
taskbars or other apps covering an aquarium need a configured zone. Client areas
outside actual monitor hardware aren't automatically clipped; keep windows
onscreen. Percentages follow the combined layout, so check zones after rearranging
monitors. No multi-host wall synchronization or bezel calibration is claimed.
