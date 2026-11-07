# Anglerfish — scoped native Aquarium integration

## What is supported

Standalone and managed HA render **explicit Water registry ID 14** as an original
3D Anglerfish: broad head, toothed gape, fins, curved articulated lure and a small
pulsing bulb. Fry/young use existing pale age expression, neutral eyes and smaller
teeth; adults express the supplied body/scales/eye genes, elders keep that art at
the existing elder size. All three styles work. Age is the received **stage**,
not inferred elapsed age. No pet ages, happiness, generation or owner are invented.

The lure uses two small meshes and the existing identity-seeded swim clock. It
adds no per-fish light, shadow, bloom pass, texture, particle system or task. Its
unlit bulb still multiplies the scene day/night/tint/blackout scale. Tail and fin
joints, swimming/avoidance, transitions, visible-water layout and physical body
bounds are unchanged. The mesh fits the previous contact/projected-fin envelope.
Source panel P1 is retained as provenance, not used to erase Aquarium colour.

**No other species art or nursery rules were changed.** This living branch still
uses its original fish fallback for 0..13, unknown identities and absent species;
it does not silently import the separate Water-species renderer branch. Existing
local hatch remains a generic local fry; nursery portrait/egg preview semantics
remain unchanged, not a new species-aware breeding/adoption implementation.

## Authoritative source trace (read-only)

Inspected on 2026-11-07:

- DX Anglerfish source a290e48022a5bf47a994bbcf21ee640d9a0b1e4f:
  examples/companion_radio/LoRaFishSpecies.h assigns Anglerfish=14, permanent
  uint16 species identity, not fish ID/name/menu index. SPC1 is saved metadata,
  not an Aquarium snapshot. LoRaFishCommit.h freezes transaction-bound COMMIT
  retries; a peer's exact S1 ACK enables H1/P1/S1 extensions. Legacy ACKs produce
  the original nine-field COMMIT, so species is absent, never reconstructible.
- DX ui-new/UITask.cpp drawFishSpriteForStage and loRaFishJuvenileTint resolve
  existing palette/H1 genes, blend fry body 2/8 and fins 5/8 from body; young body
  5/8 and fins 6/8 from scales, against RGB565 ivory 0xFFBC. Mono 6 is not a hue.
  Eyes are neutral in juveniles. LoRaFishWaterSprite.h scales the same two semantic masks
  to 20x15 fry, 26x19 young and 32x24 adult/elder. Aquarium art is native geometry,
  not a copied framebuffer; old palette 0..5 retains its established Aquarium
  styling. H1 8..247 follows the production integer hue-to-RGB565 converter exactly.
- RX Water/current-ci source 32cff79822fe7a68ab2e62cf2c814d06e29f49c6,
  examples/companion_radio/LoRagotchiRX.h: ACK advertises S1; COMMIT captures
  optional H1 (three alleles), P1 (source panel 0..2), S1 (opaque uint16 species).
  Their independent presence bits survive its journal. The receiver's existing
  command **7, argument 1**, negotiated after IDENTITY and before PEEK/READ,
  selects its existing **84-byte kind 3** snapshot for that consumer lease.
  Missing/legacy firmware returns status 1 and remains on 77-byte kind 1.
- Existing Aquarium Water source 66695aa334290966663cdf92fac924ac56e6ab93
  already implements that decoder, negotiation and metadata storage. This work
  reuses that established contract; **no RX/DX firmware or wire format changed**.
  Replay enrichment additionally cannot renew expiry, unhide, repopulate a new
  session, or roll a newer copy back.

## Exact RX fields

Kind 3 keeps kind 1 offsets 1..76 unchanged: event ID, full 32-byte owner key,
fish ID, transaction ID, stage, mode, legacy body/scales/eye palette, tint,
appearance-present and name. It appends:

| Offset | Value |
| --- | --- |
| 77 | Presence bits: 1 species, 2 H1 genes, 4 panel; other bits invalid |
| 78..79 | uint16 LE species, zero when absent |
| 80..82 | body/scales/eyes H1 alleles, zero when absent |
| 83 | panel 0..2, zero when absent |

Alleles are 0..6 or 8..247; 7 and 255 are UI-only, not wire genes. If H1 is
absent, use the received legacy genes; if S1 is absent, keep ordinary fallback.
Name, fish_id, mode, tint and panel are **never** species heuristics. Unknown
species remain numerically intact but render with unchanged fallback. SQLite
still commits before ACK; full owner identity remains the roster key. Updating
same-owner but different fish_id cannot inherit the previous pet's metadata.

## Legacy blocker (not hidden by the demo)

A 77-byte legacy snapshot carries **no species at all**. Neither old snapshots nor
an old RX can identify an Anglerfish, and no appearance/name/ID inference can fix
that. Live Anglerfish rendering needs an already species-capable RX that received
S1|14 and supplies negotiated kind 3. No firmware flash/change was authorized or
performed here. This is an exact compatibility condition, not a promise that the
owner's physical receiver already runs that firmware.

## Synthetic demo and tests

Use an isolated settings location and --demo 16 to include four explicit synthetic
Anglerfish (fry, young, adult, elder); the first twelve and all existing demo names
remain unchanged. Demo storage remains separate from live data and no radio opens.

- tests/test_anglerfish.py checks strict fields/presence, replay/session/expiry,
  all age/style joints/bounds, neutral genes, unchanged other-species geometry,
  and host-compiled actual DX COMMIT -> actual RX fragments -> SQLite -> renderer.
- Production cross-firmware tests need the read-only sibling DX/RX source trees,
  or ANGLER_DX_SOURCE / ANGLER_RX_SOURCE; absence is an explicit NOT RUN skip.
  All 240 hue values are compared with the actual DX C++ converter.
- tools/anglerfish_smoke.py compares native framebuffer bytes against saved
  pre-edit art across all old Water IDs, unknown/absent species, styles/headings,
  and captures six palettes/four ages/two lure poses plus blackout.
- tools/anglerfish_lifecycle_smoke.py runs the real app, all 20 age/pickup pairs,
  restyle/rebuild, lighting, resize/removal/reentry and desktop multi-output close.
  --managed checks HA's native read-only path. Xvfb programmatic close is cleanup
  evidence, not a title-bar click or a Windows multi-monitor hardware test.

Evidence and measured outcomes: ANGLERFISH-VERIFICATION.md. No new runtime package.
Pi baseline is deliberately bounded geometry and transforms, **not measured Pi
performance**. Physical Pi/HAOS, GPU/Windows and radio acceptance remain unverified.
