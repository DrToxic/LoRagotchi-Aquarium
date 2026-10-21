# v0.6.0 — configurable copy lifespan

Built on desktop v0.5.0; transfers and layout-aware scenery are retained.
HA has its own preview7 package based on preview6; desktop-only layout/travel
features are not silently ported into its single-window build.

## Automated verification

- `pytest -q`: storage lifecycle, renewal/deduplication, persistence, migration,
  rollback, manual hiding and disconnected worker checks plus existing suites.
- `python tools/run_native.py tools.expiry_smoke`: real worker expiry, old model
  departure/body cleanup, re-share re-entry, manual hide, arrival interruption,
  opt-out and native control pixels.
- Existing `tools.travel_smoke` and `tools.transitions_smoke --demo 8` retain
  coverage of transfers and 256-fish animation scheduling.
- Exact archived source installed into isolation for final verification.

## Owner retest

1. Aquarium → Fish lifespan → After last share → `0.02` Hours → Apply.
2. Watch a newly shared/demo copy leave after approximately72 seconds.
3. Re-share: one copy returns, including identical appearance.
4. Restart: saved live copies keep their original deadline.
5. Turn expiry Off: expired copies return; manually removed copies do not.
6. Enable transfers and exercise closing/moving windows near expiry.

Windows/mixed-DPI/native hardware retest remains outstanding. Linux native proof
uses Xvfb/software GL and is not a GPU or Pi performance claim. No firmware or
radio changes and no source publication are implied by this package.
