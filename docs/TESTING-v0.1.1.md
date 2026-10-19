# v0.1.1: swimming, labels and native windows

## Changes

- Independent seeded destinations, cruise/glide pacing, gradual heading changes,
  banking, depth changes and velocity-based local avoidance replace shared oval
  paths. Roster refreshes and quality changes preserve existing swimming state.
- Names are immutable text geometry with independent transforms for every owner
  (including owners with identical names). Labels regenerate on name/roster
  changes, not every frame, and removed owners release their label nodes.
- `V` / `--wall-columns 2` opens a genuine second OS window. One simulation and
  two native render targets show a continuous scene. Each window may be moved,
  resized and fullscreened separately; the second may be closed/reopened without
  closing the aquarium or dropping fish.
- Frusta use OS-reported desktop rectangles, including negative coordinates and
  unequal heights/vertical offsets. Names and picking use the corresponding
  window's lens. Each window owns a native graphics context; render targets resize
  in place instead of being repeatedly destroyed on focus/position/size events.

## Verification

- `uv run pytest -q`: 25 passed with sibling RX source available. Aquarium-only
  downloads skip the same two optional firmware integration tests as v0.1.
- Simulation tests cover deterministic identity ordering, name refresh continuity,
  256 fish over 600 steps, bounded position/turn changes, both turn directions,
  independent destination changes and slow/fast swimmers.
- Additional local five-minute simulated stress run: all 256 fish stayed in
  bounds; no population culling. This is simulated time, not a hardware soak.
- Native Linux Xvfb/Mesa test (`uv run python tools/run_render_smoke.py`): 256 fish,
  all 256 independent name nodes, unchanged text-build count during animation,
  name refresh, retained swimming states across presets, two distinct OS windows,
  pixel reconstruction of a frozen full-width world, independent resize/offset,
  unchanged targets on move/focus, close-event handling, three reopen cycles with
  stable output/camera/input counts, and remove/end-session cleanup. The close
  property is changed programmatically then the normal window-event handler is
  invoked; Xvfb has no window manager for a title-bar click test.
- Frustum projection tests cover 2560×1440 plus 1920×1080 with a vertical offset,
  a negative-origin secondary monitor, and vertically stacked windows.
- Both window screenshots inspected. Software rendering is not physical Windows,
  NVIDIA or Raspberry Pi performance evidence.

## Repeatable labels probe

From a desktop with the environment installed:

```sh
uv run python tools/benchmark_labels.py --demo 256 --preset high --no-vsync
```

The probe freezes the same fish geometry/positions, alternates labels off/on/off/on,
warms up each mode and prints update median plus frame median/p95 for 60 frames per
pass. It excludes animation differences and the frame cap; values describe only
that machine's renderer. Window startup and radio I/O are not benchmark targets.

### Local controlled result (not GPU/Pi FPS)

At 640×360 output / 416×234 internal, low preset, VSync disabled, on Linux
llvmpipe with the same frozen 256-fish scene and two passes per mode:

| Median frame time | Original v0.1 | v0.1.1 |
|---|---|---|
| Names off | 38.9–39.4 ms | 39.7–39.8 ms |
| Names on | 63.1–63.3 ms | 41.6–42.1 ms |

The scene retains 256 independently positioned labels, including repeated names.
This supports a reduced label-rendering cost on this software-rendering host,
not a promised Windows framerate. Hardware retesting is still required.

## Owner retest

```sh
uv sync
uv run loragotchi-tank --demo 256 --preset high --wall-columns 2
```

- Watch for varied headings, routes and pacing instead of a common circular orbit.
- Press `N` in either window and compare smoothness with names on/off.
- Move the second window to the other display, resize/maximize it, and confirm
  its crop, labels and click selection agree with the visible fish.
- Close/reopen the second window with `V` or its close button. The first should
  keep running with all fish retained.
- For the reported 2560×1440 / 1920×1080 setup, `--second-width 1920
  --second-height 1080 --second-origin X Y` can specify initial placement; use
  the actual desktop offset, not a guessed one.

The owner already reported the original prototype runs with 256 fish on Windows
(i7-11700F / RTX 3060 12 GB), smoother with names disabled. This revision's Windows
frame pacing, native fullscreen placement and mixed-DPI/refresh behaviour remain
unverified. No changes to radio protocol, firmware, saved fish, live database or
retention semantics are included.
