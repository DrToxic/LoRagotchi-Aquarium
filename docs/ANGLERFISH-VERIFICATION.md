# Anglerfish verification — 2026-11-07

> Historical pre-integration local evidence. For the subsequently merged,
> versioned source and changed test assumptions, see
> [publication verification](PUBLICATION-2026-11-07.md).

Local-only standalone and HA integration. No commits, pushes, merges, releases,
firmware changes/flashes, real-radio use or owner-data access were performed.
Existing nursery/hatch edits were captured before work and preserved.

## Source gates

- Standalone: **394 passed**, 53.96 seconds, no skips.
- HA sibling: **460 passed**, 70.47 seconds, no skips.
- New Anglerfish suite: **37 passed**, including host-compiled production DX/RX,
  real negotiated companion fragments/ACKs, SQLite, render dispatch and all
  240 production H1 hue conversions. No physical radio is involved.
- Strict presence/invalid genes/unknown IDs, same-owner/different-pet changes,
  pre-metadata JSON, expiry/hiding/session replay, storage failure ordering and
  unsupported/error negotiation are covered. Existing nursery/local hatch,
  lifespan, transport, labels, layouts, motion and other tests remain green.
- Twelve pre-edit mesh signatures guard every age/style. Runtime metadata for
  0..13, 15, 256, 65535 and unflagged 14 must leave those meshes unchanged.

## Native proof

Panda3D 1.10.16, Linux Xvfb, Mesa llvmpipe LLVM 19.1.7, 256 bits.

- 90 exact framebuffer comparisons: old Water IDs 0..13 plus unknown 65535,
  all three styles, both headings, all four stages and six palettes per frame.
  Six further absent-species framebuffer pairs are identical. This compares
  against the saved pre-edit renderer, not candidate-generated expected pixels.
- Six moving Anglerfish frame pairs (styles/headings) and twelve labelled native
  plates show four ages, coloured/white/black/H1 palettes and lure poses.
- Blackout includes the unlit lure; zero scene scale produces exactly the hidden
  scene framebuffer against a black background, not a permanently glowing bulb.
- Standalone and HA managed actual-app lifecycle probes each pass **20 cases x
  510 updates** (four stages x five exit styles), with old/new mesh hashes,
  immutable colours, intact joints and moving lure throughout replacement.
- Actual restyle/rebuild, day/night/blackout, resize, removal/reentry and native
  screenshots pass in each variant. Desktop additionally closes a non-last
  output and performs three secondary-window reopen cycles with the same fish.
- The broader native renderer probe passes with **256 fish** (including 64
  Anglerfish), cached names/rename, fullscreen restore, independent windows,
  resize/move/focus reuse, close/reopen cleanup and remove/end-session cleanup.
  Shared-world reconstruction mean RGB error: 0.0000649.
- Inspected the native age/style plates, full demo scenes, night scene and
  surviving output screenshots. No GL BadMatch/incomplete-framebuffer failures
  occurred in the successful Anglerfish lifecycle probes.

The first broader smoke attempt reused its old .local/smoke-settings.json and
failed a name-toggle assumption. It was rerun with a new temporary settings
location and passed; no application/source change was needed to hide this.

## Resource bounds and measurements

Geometry detail is capped at 20 (faceted 10). Static parts flatten; tail/fins
retain their ordinary joints. Lure animation changes only joint transforms and
bulb colour scale; no vertex rebuild, extra task, per-fish light, bloom, texture
or particle pool. All age/style bounds stay within existing fish envelopes.

A frozen 24-fish plate, identical camera/body poses/detail/resolution, alternated
lure updates off/on/off/on, 20 warmup + 60 measured frames per block:

- Enabled update medians: 0.263 / 0.273 ms; p95: 0.322 / 0.314 ms for all 24.
- Enabled full-frame medians: 8.15 / 8.61 ms; p95: 8.86 / 9.94 ms.
- Off full-frame medians: 8.04 / 7.86 ms; p95: 10.22 / 8.59 ms.

These are this software-rendered host's observations, not Pi/Zero/physical GPU
or HAOS guarantees. The implementation deliberately keeps the Pi-oriented
baseline bounded, but hardware power/FPS acceptance is still required.

## Preservation and generated HA context

Both original dirty trees were backed up under /tmp/anglerfish-baseline before
editing, including untracked nursery files and binary diffs. Nursery, hatch,
controls, cave, migration and HA-specific source/config edits were not reset.
Only inherited art.py, aquarium.py, demo.py and LIVING-AQUARIUM.md gained scoped
Anglerfish integration; all other inherited root-source bytes are unchanged.

New/modified files for this integration in both roots:

- tank/anglerfish.py, art.py, aquarium.py, demo.py
- tank/protocol.py, client.py, store.py (consume existing negotiated RX format)
- tests/test_anglerfish.py, fixtures/angler_receiver.cpp,
  fixtures/non_angler_geometry.json
- tools/anglerfish_smoke.py, tools/anglerfish_lifecycle_smoke.py
- docs/ANGLERFISH.md, ANGLERFISH-VERIFICATION.md, LIVING-AQUARIUM.md
- HA only: tools/package_ha.py includes the linked feature documentation;
  corresponding generated loragotchi_aquarium runtime/docs copies synchronize
  using the existing backup-preserving generator.

Evidence directory: /root/.openclaw/workspace/reports/aquarium-anglerfish/.
It retains baselines/hashes, logs, native PNG/JSON and the final local HA archive
and integrity/isolated-install results. Test work uses synthetic identities and
temporary settings/databases only. Generated source is not a deployment.

## Limits

Legacy 77-byte events do not carry species: those visitors must keep fallback
fish art. Species-aware live art requires a capable existing RX that actually
captured S1|14 and returns negotiated kind 3. The physical receiver/firmware was
not inspected or upgraded. Unknown species remain opaque and unchanged.

No new species-aware nursery portraits, egg-colour rules, inherited local-fry
species or DX adoption flow was added. Existing nursery semantics are preserved.
Physical Pi/HAOS/Supervisor/browser ingress, real radios, Windows/mixed-DPI/GPU
and power/current measurements remain outside this host-only proof.
