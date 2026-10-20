# v0.1.9 — Per-window sand framing and complete bubble exits

## Rendering changes

- Keep one shared world, simulation and camera orientation. Align the nominal
  rear sand edge (world Y=13, Z=0) to screen Y=-1/3 in each native view. Preserve
  horizontal spans/gaps and pixel scale; each window's vertical crop is centred
  around its own lower-third sand line, regardless of its desktop Y position.
- Separate water rectangles from actual desktop rectangles. Window placement,
  saved layouts, mask geometry, UI previews and zone percentages stay in desktop
  coordinates. Fish footprint constraints map each visible water piece back to
  the same desktop coordinates as the projector mask. Inverted masks cannot be
  escaped by turning edge protection off and swimming outside every view.
- Portrait layouts limit vertical FOV to the familiar 16:9 tank's water height.
  Equal-height horizontal crops still reconstruct the full shared scene.
  Vertical stacks intentionally show overlapping water rather than a single
  vertically continuous panorama: each window has its own sand line.
- Decorative bubbles no longer wrap at world Z=12. Each depth plane derives
  its exit from the current frustum and adds a full geometry margin; recycling
  starts beneath the sand. Layout changes update limits without rescaling
  bubble positions.
- Chat uses upward displacement, not a fixed expiry timer/interpolation to an
  obsolete endpoint. Resizing updates the exit and billboard orientation while
  preserving position, speed, node identity and cached text. Existing routing,
  deduplication, queue limits, settings and fish storage remain unchanged.

Panda3D's existing perspective lenses and mesh/node transforms are sufficient;
no new graphics library, service or dependency is introduced.
Lens behavior reference: [Panda3D lenses and field of view](https://docs.panda3d.org/1.10/python/programming/camera-control/perspective-lenses).

## Verification

```sh
uv sync --frozen --extra test
uv run --frozen pytest -q
uv run --frozen python tools/framing_smoke.py
uv run --frozen python tools/chat_smoke.py
uv run --frozen python tools/run_render_smoke.py
uv run --frozen python tools/projection_smoke.py
```

- Unit checks project the rear sand point through actual Panda lenses for
  landscape, portrait, narrow/tall, unequal, offset, negative-origin and stacked
  layouts. Mask/steering checks independently project world points through each
  lens and compare with all three zone shapes in normal and inverted modes.
  Existing whole-footprint, swept-motion and simulation checks remain in place.
- `framing_smoke.py` uses actual sand geometry and the water backdrop with
  diagnostic colours to measure the visible edge, independent of lighting and
  fish. Each sample must be within 1.5% of output height of the nominal 2/3-down
  line (allowing the natural sand ripples and rasterization). Cases include a
  single landscape/portrait view, three unequal/vertically offset windows,
  resize/move, half-scale rendering, fullscreen/restore and surviving windows.
- Native pixel differences prove an air bubble renders above the old cutoff,
  reaches the top 20 pixels, disappears fully before recycling and is hidden
  on birth. A chat bubble survives its old deadline after a wider-to-taller view
  change, visibly crosses the top border, then removes only once offscreen.
  Layout changes do not rebuild chat text.
- Existing native smoke covers synthetic channel input, real sand occlusion,
  256 fish, cached labels, horizontal window reconstruction, target reuse and
  lifecycle. Projector checks cover exact-black/unchanged output pixels for
  all shapes and inversion modes, offsets, scales and 4K circular output.

Run with isolated demo data/settings; no live radio or collection is touched.
Logs, screenshots, exact-archive/wheel byte verification and fresh-install
results are retained under `.local/v019-*`.

Environment: Linux/Xvfb/Mesa software GL, with GL debugging enabled for the new
framing check. Optional sibling-firmware checks skip in a standalone aquarium
archive. Windows/NVIDIA, mixed-DPI monitors and physical projectors still need
the owner's hardware retest; these results are not GPU performance claims.
