# v0.1.10 — Operator window, continuous panorama and decorations

## Implementation

- The first native window is the decorated 456×704 operator window. Its four
  tabs are Aquarium, RX Radio, Deadzones and Decorations. All aquarium views,
  including the first, own separate outputs, offscreen buffers, overlays,
  off-axis lenses and input prefixes. No controls/HUD are rendered into them.
- Outputs request undecorated windows; a client-area gesture moves the window,
  or resizes from a 9-pixel edge/corner. Four pixels distinguish a drag from a
  fish-selection click. Native global pointer sampling uses Win32 or X11 so a
  gesture can finish outside the client. Fullscreen disables gestures and
  preserves/restores the pre-fullscreen borderless rectangle.
- Any output can close, including the first and last. The operator remains and
  the shared fish/store are retained. Reopening restores rendering. Closing the
  operator quits; minimizing it must not throttle visible aquarium outputs.
- Actual desktop X **and Y** rectangles once again define the single shared
  camera, constraints, masks and picking. v0.1.9's per-view vertical sand
  alignment is removed. Global sand anchors the combined frustum; individual
  sand depths vary. Vertically stacked upper outputs get shared-world sand
  shelves, with an open centre and foreground route between levels.
- The file-based decoration library loads static native EGG/BAM models and
  JSON metadata, using the existing Panda loader. It adds no runtime dependency
  or executable plugin mechanism. Bundled original low-poly art: pirate ship,
  stone arch, treasure chest, anchor and clay pots. The ship and chest default
  on; user overrides persist across presets, restarts and library refresh.
- Collision proxies describe solid pieces only. Ship/arch openings remain
  navigable. Visibility and collisions toggle together; newly obstructed fish
  are relocated to clear water (or parked if no placement fits), never deleted.
  Library refresh removes old nodes/bodies. Invalid optional assets are reported
  in the tab without taking down valid entries.

Native asset format reference:
[Panda3D model files](https://docs.panda3d.org/1.10/python/programming/scene-graph/model-files).
The editable asset generator is `tools/build_decorations.py`; user instructions
and manifest example are in `tank/assets/decorations/README.md`.

## Reproduce

Use isolated settings/demo data, not a live radio or collection:

```sh
uv sync --frozen --extra test
uv run --frozen pytest -q
uv run --frozen python -m tools.run_native tools.operator_smoke --demo 24 --preset low --settings .local/operator-check/settings.json
uv run --frozen python tools/run_render_smoke.py
uv run --frozen python tools/options_smoke.py
uv run --frozen python tools/deadzones_smoke.py
uv run --frozen python tools/text_smoke.py
uv run --frozen python tools/chat_smoke.py
uv run --frozen python tools/framing_smoke.py
uv run --frozen python tools/projection_smoke.py
```

`run_native` launches Xvfb directly with `-displayfd`; it needs no `xauth`.
Operator native input tests additionally use the system X11/XTest libraries.
These are Linux testing tools, not application dependencies.

## Evidence

- Native XTest mouse input verifies client-area movement, bottom/right and
  top/left corner resize, button release outside the original client, persistent
  render targets and fullscreen restore. Geometry tests cover all edges, minimum
  size and negative desktop coordinates.
- A fully black aquarium has sampled RGB exactly zero while the separate
  controls pixels remain unchanged. Settings are not in the panorama bounds.
- Frozen unequal/vertically offset views reconstruct the corresponding part of
  a single reference render (observed mean RGB error 0.0000069). Side-by-side
  256-fish reconstruction also passes. Physical clipping at a genuine outer
  border or gap is distinct from the old mismatched vertical crops.
- Two stacked views receive two shared-world shelf ledges. Clearances leave
  centre/foreground passages for all fish stages. Native captures prove upper
  and lower scenes draw fresh pixels, including after arbitrary closes.
- Adult/elder-sized Bullet bodies physically traverse both ship and arch
  openings, with no residual penetration. Probe checks cover every fish stage;
  solid beams/pillars remain blocking. Library reload/toggle tests check
  persistence, model loading, node/body cleanup and malformed metadata.
- Existing native checks cover 256 identities, labels/cache/renames, RX controls
  with a simulated local peer, Unicode pixels, saved geometry/zone restoration,
  eight outputs, bubble birth/rise/top exit and channel filtering.
- Projector tests sample 62,164 pixels across all three shape/inversion pairs:
  31,082 exactly black and 31,082 matching unmasked output. Additional cases
  cover three offset views, render scales 0.35/1.2, target reuse, surviving fresh
  3D frames, repeated masks and 4K circular blackout at 0.35 scene scale.
- Native checks use GL debugging where relevant and reject GL/FBO, missing
  glyph and text-property errors. Headless Xvfb lacks `/dev/input` and XFree86-DGA;
  those startup notices are not failures of XTest/client input.

Exact ZIP versus committed-source verification, wheel asset inclusion,
fresh frozen install checks, logs and screenshots are retained under
`.local/v0110-*`. The two sibling-firmware-source tests are optional and skip in
the standalone source archive.

## Limits

Linux/Xvfb/Mesa software GL is the tested host. No window manager is running in
these checks: they prove native X11 inputs and Panda window requests/lifecycle,
not a title-bar click or every desktop's policy. Windows/NVIDIA, KDE/GNOME/LXDE/
Xfce, XWayland compositor placement restrictions, mixed-DPI screens, per-monitor
Linux fullscreen and physical round projectors need hardware acceptance.
No GPU/Pi performance claim, physical RX link, radio operation, firmware change,
public push or release is part of this local update.
