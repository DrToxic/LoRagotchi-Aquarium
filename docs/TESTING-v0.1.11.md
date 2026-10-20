# v0.1.11 — Fish arrivals, exits and refresh choreography

## Contract

- Renderer-only state machine separates the authoritative desired roster from
  the currently shown snapshots. Exactly one model per full owner identity.
- Initial/new fish descend from above the current combined panorama. A clear
  vertical route is checked against solid scenery, including stacked shelves;
  alternative open landing columns are preferred over clipping through solids.
  If no open column fits, the arrival waits without losing its identity.
- The landing point is temporarily reserved by a held Bullet body; normal
  steering resumes at the end. Geometry/layout revisions invalidate route checks.
- Old snapshots keep their original model, stage, colour and name until exit
  completion. Newest desired version enters afterward. Updates during entry
  wait; updates during exit coalesce. Remove/re-share and duplicate refreshes
  cannot leave duplicate models, collisions or labels.
- Five local original BAM actors: toothless cartoon shark, net, water bag,
  glass bowl and open cage. Source generator uses existing Panda geometry;
  no downloaded art, new runtime library or external asset service.
- Four simultaneous exits, with remaining fish swimming in a queue. Turning
  animations off releases all actors/holds and applies the desired roster.
  Disabling all exit styles instead selects a simple upward swim.
- Refreshes are recognized by a changed Snapshot, including a new share/event
  with identical colours. ReturnStatus never exits a copy. Demo/replay→live
  switches discard synthetic visual sequences before showing the live roster.
- The existing service, store, protocol and transport code are unchanged.
  Commit-before-ACK and full-owner identity behavior remain intact.

## Reproduce

```sh
uv sync --frozen --extra test
uv run --frozen pytest -q
uv run --frozen python -m tools.run_native tools.transitions_smoke --demo 8 --preset low --settings .local/animation-check/settings.json
uv run --frozen python tools/run_render_smoke.py
uv run --frozen python -m tools.run_native tools.operator_smoke --demo 24 --preset low --settings .local/operator-check/settings.json
uv run --frozen python tools/text_smoke.py
uv run --frozen python tools/projection_smoke.py
```

`tests/test_transitions.py` uses real Panda scene models/Bullet without a display.
The native sequence smoke captures all five actors and compares with actor-hidden
frames, tests the real roster event path, old/new appearance ordering, portrait
resize during lift, shared-actor panorama reconstruction, full blackout, output
close/reopen, graphics rebuild and final actor/model/body cleanup.
It also completes 256 animated arrivals, queues a 256-fish refresh, rebuilds
graphics with both active and queued exits, and checks immediate opt-out cleanup.
The 256-fish steady-state renderer, deadzone and Unicode suites explicitly disable
animations to isolate their existing cached-label/window checks.

Source archive and wheel asset equality, isolated frozen installs, checks and
captures are recorded under `.local/v0111-*`. Two optional sibling RX-source
tests skip in a standalone aquarium archive.

## Owner acceptance

1. Start the demo and watch fish descend from above. Open **Animations**.
2. Enable one pickup at a time and use **Aquarium → Remove copy**.
3. On the existing live RX connection, re-share an updated fish: old appearance
   must leave first and the refreshed appearance must enter from above.
4. Re-share again while that exit is underway; only the latest version enters.
5. Try adjacent/stacked windows, round masks and a resize during pickup.

Linux Xvfb/Mesa is the native test environment, not Windows/NVIDIA or physical
projector proof. Pickups are temporary visual choreography rather than rigid
physics objects; they do not shove the other swimming fish. Desktop gaps and
projector masks can intentionally conceal portions of a shared-world sequence.
No radio, firmware operation, push or release is part of this local build.
