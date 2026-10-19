# v0.1.5: projector blackout and inverted display areas

## Changes

- Independent **Blackout** and **Invert** switches per deadzone, beside Outlines
  in the existing compact third tab. New zones keep switches in their draft until
  Apply; existing-zone switches save immediately. Disabled zones do neither.
- Invert changes the excluded area to the shape's exterior. Whole-fish footprint
  containment, not centre-point containment, enforces curved edges. Ordinary
  exclusions can cut holes inside an inverted area. Multiple inverted zones keep
  their intersection; non-overlapping interiors park fish without deleting them.
- Blackout paints the excluded area opaque RGB zero over scenery, fish, names and
  HUD. It is built from Panda3D's native polygon-with-hole triangulator, with no
  new package, shader, texture mask or CPU-generated raster image dependency.
- Curves are tessellated at output-resolution precision (about half a pixel or
  better), independently of the 3D scene render scale. One shared geometry is
  cropped into each native view, including unequal sizes and desktop offsets.
- Explicit render bins place masks after the ordinary 2D overlay, controls above
  masks, and dropdowns above controls. Tab closes the controls for clean output.
  This avoids a full blackout making its own controls inaccessible.
- Existing version-1 display profiles load with new flags defaulting off. Settings
  remain separate from RX connection details and the live fish database.
- Multi-window cleanup now retires buffers after drawing the closing window's
  native graphics context. The previous direct close of a middle window after
  captures/rescaling could delete a context-local FBO while a sibling context was
  current on the tested GLX driver, leaving stale scene pixels/framebuffer errors.
  Retired buffers are deactivated and display regions removed before removal.

## Verification

```sh
uv sync --extra test
uv run pytest -q
uv run python tools/run_render_smoke.py
uv run python tools/options_smoke.py
uv run python tools/deadzones_smoke.py
uv run python tools/projection_smoke.py
```

Full local suite: 65 passed. Standalone archive: 63 passed, two optional sibling
firmware-source tests skipped. Geometry tests include old-profile migration,
flag validation, exact convex whole-box containment, inverted curved boundaries,
combined interior exclusion, disjoint inverted zones and recovery of parked fish.

The projection smoke uses native Xvfb/Mesa rendering with GL debugging enabled:

- For all three shapes in normal/inverted modes, 62,164 sampled pixels are checked:
  31,082 masked pixels are exactly RGB zero and 31,082 unmasked pixels match the
  frozen reference. A two-output-pixel boundary band is excluded from pixel
  comparison to allow rasterization/tessellation edge coverage.
- Disabled masks, invert without blackout, multiple combined masks and a full
  screen rectangle are checked. Blackout applies to labels/HUD, not just fish.
- Full blackout still permits visible controls and dropdowns. Actual toggle
  callbacks and on-disk flags are exercised. A 16:9 circular preview/output is
  captured after the simulation places whole fish inside it.
- Three native offset/unequal windows, render scales 0.35 and 1.2, move/resize,
  middle-window close and repeated clear/rebuild retain correct per-view masks.
  Surviving windows must render a controlled 3D scene colour change after close,
  not merely display their last good texture (even a floor-only crop is checked). The harness fails on GL errors, bad matches or incomplete
  framebuffer warnings, not just nonzero exit codes.
- A 3840×2160 circular output is pixel-checked with the scene at 0.35 scale.
- Existing 256-fish renderer, native lifecycle, compact 720p/1440p/4K controls,
  simulated RX UI and fresh-process saved-layout restore checks are retained.

No actual Windows projector, round panel, mixed-DPI monitor arrangement or radio
hardware was used. RGB-zero screenshots prove output masking, not a projector's
optical black level. Xvfb programmatic close tests are native lifecycle tests, not
physical title-bar interaction. Physical Windows placement/frame pacing remains
an owner hardware check. No edge blending, geometric warping or multi-host sync.

## Quick setup

1. Tab → Deadzones → New zone → choose shape and dimensions → Apply.
2. **Blackout on** hides the excluded area. **Invert on** makes the shape's inside
   usable water and its outside excluded. Use both for a shaped projector output.
3. For a centred circle on one 16:9 output, use Ellipse with Left **21.875**, Top
   **0**, Width **56.25**, Height **100**. For a square output, use **0 / 0 / 100 /
   100**. Percentages span the entire combined layout, not the selected window.
4. Turn Outlines off, close controls with Tab, and use F for borderless output.
5. Reopen Tab to adjust/disable/delete zones. Saved preferences restore normally.
   Do not enable several separate inverted zones expecting a union: their common
   interior is the usable area.
