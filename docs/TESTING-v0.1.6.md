# v0.1.6 — Unicode display fallback

## Change

- Bundle unmodified Noto Emoji outline font and OFL license; keep Liberation Sans
  for ordinary text. Use Panda3D's native embedded font properties.
- Apply glyph fallback only at display boundaries: fish labels, selected fish,
  HUD/status, inbox, discovered device names and connection errors.
- Ignore presentation selectors and nonprinting controls. Unsupported glyphs
  render as `?`; complex joined emoji render as separate supported components.
- Do not change transport, stored names, keys, simulation, geometry ownership,
  or per-frame label placement. Bounded text/coverage caches supplement the
  existing immutable name geometry cache.
- No dependency change or installed OS fonts required.

## Regression coverage

`tests/test_text.py` uses the actual bundled fonts and Panda text generation:

- Fish, tropical fish, blowfish, shark, biohazard and smiling face glyph coverage.
- Presentation selectors, combining accents, Greek/Cyrillic, unsupported
  characters and externally supplied Panda control characters.
- Protocol encode/decode and SQLite reopen preserve the original Unicode name.
- Duplicate-name identities retain distinct transforms, reuse glyph geometry,
  refresh on rename and clean up on removal.

`tools/text_smoke.py` runs the actual native app under temporary Xvfb:

- Emoji in moving labels, selected-fish panel, HUD and inbox.
- Second native window and cached name geometry.
- Synthetic Bluetooth discovery and selection preserve the exact address.
- Pixel difference proves visible emoji geometry, not merely font coverage.
- Fails on missing-glyph/unknown-text-properties warnings or GL errors.

Development checks: 68 unit tests passed with the sibling firmware source
available; native Unicode smoke passed with 1,631 changed emoji pixels.
Screenshots in `.local/v016-unicode-*.png` were visually inspected.

## Fresh-package checks

Run from an extracted source ZIP:

```sh
uv sync --frozen --extra test
uv run --frozen pytest -q
uv run --frozen python tools/text_smoke.py
uv run --frozen python tools/run_render_smoke.py
uv run --frozen python tools/options_smoke.py
```

The two firmware-source tests skip when the optional sibling `LoRagotchi-RX`
checkout is absent. The wheel must contain both TTF files and both font licenses.
The handoff records the archive SHA256 and actual fresh-package check outcomes
in `.local/v016-package-verification.json`.

Environment: Linux, Python 3.12, Panda3D 1.10.16, Xvfb/Mesa llvmpipe. Missing
`/dev/input` and XFree86-DGA notices are expected in this environment, not
missing-glyph errors. This does not prove Windows/GPU performance or physical
radio behavior. No live database, radio, firmware or settings are modified.
