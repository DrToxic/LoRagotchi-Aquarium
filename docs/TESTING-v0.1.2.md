# v0.1.2: wider roaming, collisions and fullscreen

## What changed

- Fish choose longer journeys into underused **visible-water sectors**, with
  independent pacing and glides. They no longer abandon most journeys after a
  short timer and repeatedly drift back through the centre. Goals account for the
  combined window frustum, including gaps/offsets; resizing replans movement
  without teleporting fish. The physical water volume is wider, deeper and taller.
- Panda3D's bundled **Bullet** handles broadphase, body contacts, continuous
  collision detection and non-bouncy resolution. Each fish stage has a scaled
  body capsule; rocks and coral use convex shapes generated from the same layout
  as the artwork. Floor/tank planes are solid. The existing spatial hash provides
  early steering, including a consistent passing side for head-on approaches.
- Arrival placement checks clearance, including contact margins. Existing
  identities and motion states survive names, quality changes and roster order;
  growth updates the collision body and removal releases it. No visitor is culled
  to satisfy crowd density.
- `F` and `--fullscreen` now mean **borderless fullscreen**. On Windows,
  `MonitorFromWindow` / `GetMonitorInfoW` supplies the containing monitor bounds,
  including negative origins. No exclusive display mode is requested. The
  previous window size, origin and decoration state are restored per window.
  This addresses the reported attempt to switch into a nonexistent 1920×1009
  monitor mode: that was a window client size, not a supported display resolution.

No new package dependency, radio/firmware change, database change or population
limit is introduced. Bullet is already part of the pinned Panda3D package.

## Collision scope

Colliders approximate the **opaque fish body**, not every animated fin or tail.
Plants and tiny decorative pebbles are not solid obstacles; the floor is a
conservative plane above the slight sand ripples. Contact shells tolerate small
solver penetration. There is no elastic bouncing or damage/gameplay simulation.
Fish separated in depth can legitimately overlap in the 2D image. Extremely
crowded custom/live populations may still crowd or require separation; a no-overlap
guarantee for unlimited bodies in a fixed tank is not claimed.

## Verification

- Full local suite: **37 tests** (including the optional sibling firmware tests).
  A standalone aquarium archive skips those two firmware-only tests.
- Collision cases: fry/adult/mixed-size head-on paths, crossing paths, valid
  depth-separated passes, floor/walls/reef occupancy, stage growth, name refresh,
  removal, and non-intersecting initial placement for all 256 demo fish.
- Motion tests: deterministic identity ordering, bounded displacement/turns at
  256 fish, retained motion state, wider edge/upper-water occupation after warmup,
  view-aware goals on unequal/offset views, and no teleport on view changes.
- Fullscreen property tests reproduce the 1920×1009 client-size case against a
  1920×1080 monitor, plus negative origins and independent window restoration.
- Native Xvfb/Mesa checks at 256 fish: cached names and rename, preset continuity,
  fullscreen sizing/restore without a hardware mode switch, two distinct windows,
  frozen-world pixel reconstruction, unequal-size/offset resize, close/reopen
  cleanup, and roster clearing. Both window screenshots inspected.
- Xvfb has no window manager: its test proves size/position restoration and
  requested properties, **not Windows title-bar style or monitor API execution**.
  The real Windows fullscreen fix, mixed-DPI placement and GPU frame pacing need
  owner retesting. Linux/macOS multi-monitor fullscreen selection is not promised
  by the single-display fallback.

## Reproduce

```sh
uv sync --extra test
uv run pytest -q
uv run python tools/run_render_smoke.py
uv run python tools/measure_swimming.py --fish 256 --seconds 120
```

The coverage probe samples the second half of a two-minute **simulated** run. It
reports edge occupation (`abs(x) > 10`), upper water (`z > 9`) and sampled contact
shell penetration. Wall-clock execution time is not rendering FPS or a hardware
soak. The v0.1.1 baseline occupied the outer areas in 8.2% of samples and upper
water in 0.3%. The final v0.1.2 run measured **38.6% outer / 29.5% upper**
across 15,360 sampled fish positions, retaining all 256 fish. This is coverage
evidence, not GPU performance. Approximate contact shells showed a maximum sampled
residual depth of 0.074 world units; rigid contact is not exact mesh separation.

## Owner retest

```sh
uv sync
uv run loragotchi-tank --demo 256 --preset high --wall-columns 2
```

Move the second window to the other monitor; press `F` in each window. Each should
fill its own monitor without the unsupported-resolution error. Press `F` again to
restore it. Let the tank run for a minute after resizing, then check edge/upper
water use, body contacts near rocks and other fish, and names-on smoothness.
