# Appearance release verification — 2026-10-21

## Verified locally

- Desktop unit suite: **177 passed**, including individual-field migration,
  original malformed-file backups, validation, midnight/DST schedules, stale HA
  sun fallback, stable emitter placement and quality/appearance separation.
- Original desktop v0.2.1 versus new Classic/static: **zero changed pixels** in a
  deterministic 960×540 scenery comparison (no fish/ambient bubbles; frozen
  plant/caustic phases). This isolates renderer defaults from fish motion.
- Native appearance suite: day/night/restored pixels, no fish model/swimmer
  reconstruction on appearance changes, native input validation, bounded moving
  bubble pool, fixed emitter/node identities, floor/shelf rising-path clearance,
  generated shelf removal and honest zero-column fallback.
- Native transitions suite includes original-old exit/new entrance, all pickup
  actor styles, resize/quality changes, panorama continuity, projector blackout,
  256 animated arrivals, queued updates and opt-out cleanup.
- Native operator/render suites: drag/resize, separate windows, stacked shelves,
  close/reopen cleanup, retained swimming state and shared-world reconstruction.
- Native Radio workflow: one shared port, channel/DM delivery, contact/channel
  management, device/tools and fish ACKs remain functional. The v0.2.1 transcript
  clipping implementation is unchanged.
- Native projection suite: all mask shapes, 3 offset windows, output scales,
  4K masks and continued rendering after an output closes.

Linux/Xvfb/Mesa timings are not target GPU/Windows/HA-host performance evidence.
One uncapped low-profile sample with 12 frozen fish at 960×540 (624×351 internal)
measured median render/update 17.0 ms without columns and 21.3 ms with 3 columns /
90 bubbles; P95 24.3/29.0 ms, 30 frames each. This is a small shared-host software
rendering sample, not a promised FPS or a clean hardware benchmark. Columns are
capped at 300 pooled particles total, plus separately capped ambient bubbles.

## Run relevant native checks

Use isolated settings paths and synthetic inputs; never point tests at a live
collection. The standalone appearance and projection suites isolate themselves.

```sh
uv sync --frozen --extra test
uv run --frozen pytest -q
uv run --frozen python -m tools.run_native tools.appearance_smoke
uv run --frozen python -m tools.run_native tools.transitions_smoke --demo 8 --preset low --settings .local/test-transitions/settings.json
uv run --frozen python -m tools.run_native tools.operator_smoke --demo 24 --preset low --settings .local/test-operator/settings.json
uv run --frozen python -m tools.run_native tools.render_smoke --demo 12 --preset low --settings .local/test-render/settings.json
uv run --frozen python -m tools.run_native tools.radio_smoke
uv run --frozen python -m tools.projection_smoke
```

## Home Assistant preview 6

The separate HA tree adds read-only sun/timezone observation and HA-owned options.
Its unit suite additionally covers backend event routing, connection reuse,
optional snapshot-write failures, observer disconnects, and receiver/display
process isolation. Native managed-display checks retain one window, no operator
controls/hotkeys/masks, moving fish and unchanged legacy layout files.

The exact generated 85-file app context was extracted from its ZIP and built as
an amd64 container. Chromium verified clean animated root/view/control routes
at both root and simulated nested Supervisor ingress paths. Live synthetic HA
sun events visibly dimmed/restored pixels with unchanged renderer/observer PIDs;
unavailable sun selected clock fallback. Demo observer made no MeshCore service
calls. Renderer environment contained no Supervisor token. Direct ingress access
was denied, internal health passed, and raw pointer input was rejected on both
WebSocket routes even with client-side viewOnly disabled.

This is a local synthetic Supervisor/HA fixture, **not** a physical HAOS upgrade
or physical-radio proof. HA option changes still require Save + Restart.

## Owner retest

1. Extract desktop into a new directory; use the existing install/start commands.
   In Aquarium → Appearance, change light/water settings and Apply. Preview
   night/day, return to Current time, restart and check persistence.
2. Enable 2–3 columns with a total budget of 60. Change the seed. On desktop,
   test floor/mixed/shelves with your actual window layout, then resize/close an
   output. Verify no unexpected disappearance or columns through solid scenery.
3. Try your local clock zone across the schedule boundaries. HA: choose `ha_sun`,
   confirm HA's timezone, and check Logs if the clock fallback appears.
4. Check Windows mixed-DPI/fullscreen, frame pacing, real fish collection and
   target-device resource use. No reset of fish data is required.

No firmware change, live-radio operation, GitHub publication or installed HA
configuration change is part of this local handoff. Theme packs, new reef/fish
art and desktop deadzone shelves/transfers/decor placement remain follow-ons.
