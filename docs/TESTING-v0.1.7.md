# v0.1.7 — Windows supplementary-character crash

## Cause and fix

The v0.1.6 coverage check passed each Python character to
`TextNode.hasCharacter()`. Panda3D 1.10.16 binds that argument as `wchar_t`.
Windows uses a 16-bit value, so a supplementary character such as U+1F41F
(fish) raises `TypeError`; Linux's 32-bit value hid the problem.

Keep that API for BMP characters (including Panda's synthesized accents).
For supplementary characters, query the font with `getGlyph(int_code_point)`.
Missing glyphs can return non-null replacement objects; compare against the
known-unmapped U+10FFFF glyph in the two bundled fonts. Do not compare character
fields: Panda caches glyphs by glyph index, so aliases can share an object
tagged with the first requested code point.

Only the display coverage helper changes. Stored/wire names, fonts,
dependencies, settings, radio operations and swimming remain unchanged.

## Checks

- `tests/test_text.py`: real font coverage and generated geometry; supplementary
  fish/emoji, biohazard/selectors, unsupported noncharacters; Windows-like
  narrow-binding rejection; existing raw-name protocol/SQLite roundtrip,
  duplicate identity, cache, rename and removal checks.
- `python tools/text_binding_smoke.py`: headless, real installed Python/Panda
  bindings. On Windows it first reproduces the old TypeError, then proves five
  corrected Unicode cases generate geometry and preserve expected plain text.
  No window, radio, settings or live database is opened.
- `python tools/text_smoke.py`: native Linux/Xvfb text in moving names, selected
  fish, messages/status, device picker and second window; pixel comparison
  requires visible emoji and fails on missing glyph warnings.

The binding check was run with official Windows CPython 3.12.10 and
Panda3D 1.10.16 amd64 binaries under Wine 10. It reproduced the original error
(`wchar_t=16`) and passed the fixed cases. The same check passed on Linux
(`wchar_t=32`). **Wine is not a native Windows/NVIDIA hardware test.**

Fresh source archive verification:

```sh
uv sync --frozen --extra test
uv run --frozen pytest -q
uv run --frozen python tools/text_binding_smoke.py
uv run --frozen python tools/text_smoke.py
uv run --frozen python tools/run_render_smoke.py
```

The two optional firmware-source tests skip without the sibling RX checkout.
Archive/wheel byte checks and completed package results are recorded in
`.local/v017-package-verification.json`; Windows binary output is retained in
`.local/v017-windows-binding.log`. Physical Windows/GPU retest remains pending.

## Existing Windows install

Close the aquarium and copy the new source over the existing installation,
keeping `.venv` and any custom data/settings. No dependencies changed:

```powershell
.\.venv\Scripts\python.exe -m tank --preset high
```

Alternatively extract fresh and follow the normal installation instructions.
The default collection/settings live outside the source directory; preserve
any custom `--database` or `--settings` paths.
