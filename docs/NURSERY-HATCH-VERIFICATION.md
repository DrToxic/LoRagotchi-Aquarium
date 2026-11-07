# Nursery local-hatch verification

Verified 2026-11-07. Local source only; no push, release, deployment, firmware flash,
real-radio connection or owner data/settings mutation was performed.

## Implemented

- Adult/elder demo breeding and native parent-menu crash fix (DirectOptionMenu
  selectedIndex is an attribute). Invalid, empty, duplicate, juvenile and stale
  selections fail safely. No age/stage/generation is invented for received fish.
- Dedicated persistent local egg/fry database beside settings, shared visually
  across Demo/Live and application restarts, partitioned by display session name.
  Visitor/receiver/companion databases remain separate; replay remains isolated.
- Additive legacy imports preserve original files, immutable parents, preview
  JSON, egg IDs and parental cooldowns. Transactions roll back together on failure.
- Explicit, atomic, exactly-once local hatch into a saved unique Gen 1 fry,
  lifetime 0 (forever), with no ageing, visitor expiry or breeding. Exact egg RGB
  preview feeds normal pale fry expression without quantisation.
- Local-fry cap/removal and durable retry receipts; deleted fry do not resurrect.
- Desktop hatch controls and optional explicit startup argument. HA keeps the
  managed viewer read-only and adds nursery_hatch_egg in Configuration; full
  available IDs are logged, and restart retries return the same saved fry.
- Cave approach now holds a bounded above-front detour and supplies turning
  clearance/separate holding targets for two elder bodies. Previous native
  timeout trials exposed heading-dependent wall contact; final-v2 probes pass.

## Tests and graphics evidence

Both source trees: uv run pytest -q; git diff --check.

- Standalone: **357 passed** (54.95 s), .local/local-hatch-final-v2-tests.log.
- HA: **423 passed** (69.46 s), .local/local-hatch-final-v2-tests.log.
- Extracted final HA artifact: **70 passed** (1.39 s), targeted nursery, living
  model, migration, local-hatch and HA-configuration tests. No optional skips.
- Fault-injected legacy imports at cooldown, lineage and completion-receipt
  boundaries roll back all imported rows; source bytes remain unchanged and
  retry imports exactly once. Hatch deletion failure also retains the exact egg.
- Concurrent hatch, capacity failure, duplicate create/hatch, removed-fry retry,
  stale source commands, session/replay separation and live/demo switch/restart
  tests pass. Tests verify local removal never enters the service command queue.
- Real Panda3D/DirectGUI windows and XTest pointer input reproduce the old menu
  KeyError, then safely select parents, invite a pair and click local hatch.
  Native cave visits use accelerated simulated elapsed time, ordinary Bullet
  collision/visible-water steering, and **no clear-approach/teleport fixture**.
- Full native process restarts restore the exact saved fry. HA configuration
  startup hatch and repeated configured restart preserve the same identity.
- A live-shaped test snapshot is injected into the actual app event handler to
  prove visitor/local-fry coexistence and local permanence; this is **not a
  physical live-radio test**. The nursery probe forbids opening a radio.
- Broader living graphics probes pass on standalone and managed HA: 300 column
  plus 100 legacy bubbles, hidden emitters, changing water pixels, zero-speed
  pixel identity, egg/portrait rendering, 256 fish, seven activities and repeated
  Classic/Tidal Garden scene rebuilds. Final egg/fry/UI screenshots were inspected.
- Eight-heading physical clearance assertions protect the elder holding targets.

Authoritative evidence directory:
/root/.openclaw/workspace/reports/aquarium-local-hatch/

Use final-v2-standalone (report, restart, hatch/UI screenshots),
final-v2-ha-managed (stored egg, configured hatch/repeat and restart),
final-v2-living-standalone and final-v2-living-ha (graphics reports), and
isolated-final-v2-ha-native (extracted-package hatch/coexistence/restart).
Older reports/logs are retained recovery/failed-trial evidence, not final results.

## HA source/package integrity

Shared nursery/art/UI/tests/docs bytes match between the standalone and HA root
sources. HA-specific fixed scenery, managed input, backend/radio and streaming
architecture were retained, not replaced by the desktop renderer.

Generated add-on context: tools/sync_ha_repository.py --check verifies 115 files.
The prior generated directory was retained by its atomic synchronizer.

Final local artifact: ha-local-hatch-final-v2.zip in the evidence directory.
SHA256: 9eee509c8fef91e1c5a44649581b93a62243e52f290298c2928004a9ebfe87da
All 115 archive member paths/bytes match the generated context. It was extracted
into a new isolated directory, installed in its own Python 3.12 environment, and
its targeted tests and managed native hatch/coexistence/full restart probes pass.
Python 3.10 syntax parsing passes for runtime source; no Python 3.10 runtime test.

## Limits

Linux Xvfb/Mesa llvmpipe only; not Windows/GPU/Pi performance or actual HAOS
Supervisor/browser ingress installation proof. Docker is unavailable on this host,
so no container rebuild was possible. No hardware radio, donor pet, companion or
DX adoption handshake was used. Blocked/hidden/custom-layout cave approaches still
fail closed on timeout rather than creating an egg. Keep the same settings
location and session name for a given local collection. DX adoption remains
unsupported and retains the egg; aquarium-only hatch does not imply transfer.

User operation and migration details: LIVING-AQUARIUM.md.
