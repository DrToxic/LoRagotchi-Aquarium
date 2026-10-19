# Community Tank development

- This is a native Python/Panda3D application; do not replace it with a web page.
- Main thread owns rendering. The service worker owns radio and SQLite I/O.
- Never acknowledge an RX event before committing SQLite. Preserve full device
  identity; names and fish IDs are not unique. RETURN status never removes a copy.
- Synthetic demo and replay must stay isolated from the live database by default.
- RX firmware prototype is in sibling `LoRagotchi-RX`, local branch
  `feature/community-tank-rx`, based on accepted DX `6a7b41a`. Do not edit or
  change the branch of sibling `LoRagotchi-DX` as part of aquarium work.
- Use `uv sync --extra test`, `uv run pytest -q`. Native renderer integration:
  `uv run python tools/run_render_smoke.py` (Linux with Xvfb). Do not use software
  Xvfb timings as Pi/GPU performance measurements.
- No live-radio operations, flashes, pushes, releases or public listeners are
  implied by a local code task. The LAN bridge defaults to loopback.
- Keep transport/graphics/platform support claims evidence-based. Compatibility
  preset is a visual profile, not proof of original Pi/Zero support.
