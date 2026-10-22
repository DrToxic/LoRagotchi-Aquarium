# Living aquarium — 0.9.0 candidate

Native Panda3D in both applications. No new runtime dependency, firmware change,
radio ownership change, or modification to a visiting pet's identity/health/age.

## Bubbles and water

Standalone: **Appearance → Bubbles / Water**. HA: **Configuration → Appearance**,
then Save + Restart.

- `column_placement`: existing floor / shelves / mixed, plus **objects** and
  **all** (objects plus normal surfaces). Named rock crevices, sponge openings and
  the nursery roof follow their object's actual position and visibility. Classic
  rocks and Tidal Garden are both supported. Object outlets use the existing total
  column pool, not a separate unbounded allocation.
- `column_count` 0–16; `column_particles` 1–300. Ambient `bubbles` remains 0–100.
  A column count of zero disables columns, including object outlets.
- `bubble_dynamics`: independent size, rise-speed modulation, drift and emission
  delays. `bubble_collisions`: swept static-only Bullet deflection. No fish/bubble
  or bubble/bubble physics. Trapped particles have bounded lifetimes.
- `background_motion`: off / rays / ripple; `background_speed` 0–3 and
  `background_strength` 0–1. Zero speed freezes the pattern; off removes it.
  These controls are independent of caustics, plant motion and day/night lighting.
- `fish_activity`: off / gentle / lively. Seeded glides, short bursts, small play
  loops, object investigation, bubble following and short wake-following chases.
  Activity is local to the aquarium, preserves identity, and survives roster/name
  refreshes and graphics changes. Collision anticipation samples the approach and
  evaluates turning clearance; Bullet still enforces physical contact.

Defaults: gentle fish activity, dynamic/colliding ambient bubbles, water pattern
**off**, columns **off**. No particle-count increase on upgrade. Turn collision
checks off on slower hosts if desired. Software-renderer timings are not physical
HAOS/Windows/GPU performance guarantees.

## Breeding cave and local nursery

**Off by default.** Standalone: Aquarium → Breeding nursery. HA: Configuration →
Nursery. Enable the cave, optionally enable automatic pairing, choose 1–12 eggs
and a 1–1440 minute rest per parent (default 6 eggs / 30 minutes).

Two different full owner identities, adult or elder, visit the cave. Parents must
remain unchanged and present throughout the visit. Arrival, departure, transfer,
blocked/hidden cave, timeout or unavailable swim space cannot produce a phantom
egg. Desktop also allows explicit parent selection. HA's managed viewer remains
read-only; automatic pairing is opt-in through Configuration.

Eggs are stored transactionally on a dedicated storage worker. Capacity, immutable
parents and both parent cooldowns commit together. Lowering capacity or disabling
the nursery never deletes eggs. Demo/replay and live stores are separate; default
in-memory demos remain ephemeral. Persistent stores are `nursery-live.sqlite3`,
`nursery-demo.sqlite3` and `nursery-replay.sqlite3` beside settings, partitioned by
the display session. Back up these files with the existing aquarium data.

The nursery displays coloured eggs and two frozen **2D appearance portraits** per
egg. Portraits are generated from the stored breeding-time appearance, not the
parent's later live state. Colour previews use one stored random interpolation
fraction between the parents' body colours in linear-light sRGB.

**These are local eggs, not transferable DX genomes.** The rule is explicitly
versioned `local-linear-srgb-v1`; `firmware_genome` remains null. No egg is removed,
claimed, ACKed or transmitted. DX discovery, genome/palette mapping and a durable
reservation/commit/recovery handshake must be agreed with the firmware session
before enabling transfer. See [DX egg contract](DX-EGG-CONTRACT.md).

## Games using mesh messages

Standalone: Aquarium → Mesh message games. HA: Web UI → `setup.html` → Mesh
message games (separate `games.html`, never controls over the aquarium stream).

Games: **noughts and crosses**, **guess the number**, and **open-deck blackjack**.

1. Player 1 starts a game and copies the outgoing LAG1 invitation.
2. Send it to the other aquarium's operator in **MeshCore direct chat**.
3. Player 2 pastes it and selects Join. Play when prompted, copy the outgoing
   turn back into that same direct chat, and import the reply with Receive turn.
4. Resend the latest outgoing turn after loss. Duplicates and older messages do
   nothing; conflicting histories, illegal moves and forged local turns fail.

This is **manual copy/paste transport**, not automatic mesh integration. No radio
commands are emitted by the game panel. Both peers need this aquarium version or
another implementation of the documented protocol. Check the sender in the chat;
the game payload does not authenticate peers. No channel broadcasts or wagering.

Messages include the complete bounded game history and fit 160 UTF-8 bytes. The
host commits its guessing-game secret in the invitation; the final reveal checks
both that commitment and all prior clues. Blackjack uses a shared open deck, not
hidden cards or gambling-grade randomness. On desktop, the current game (including
the host's private number) is saved as `aquarium-game.json` beside settings. HA
keeps the current game in this browser's local storage. Only copy the **outgoing
turn**, never private saved-game JSON. Browser storage clearing loses that local
recovery state. No automatic retries or background game transmissions.

Wire: `LAG1|kind|id|commit|moves|reveal|1`, kind t/g/b, 16 lowercase hexadecimal
ID, dot-separated moves or `-`. T: squares 1–9, X first. G: guest guesses 1–20,
host replies h/l/c, SHA256(`number:nonce`) first 24 hex in commit; final reveal
`number,nonce` with 12-hex nonce. B: h/s; 52 cards sorted by SHA256(`id:card`),
card 0–51, rank card%13+1, face cards 10 and ace 1/11; first two cards to player 1,
next two to player 2. Alternate turns, skip stood/busted hands. No turn after end.

## Validation tools

`uv run pytest -q`

`uv run python tools/run_native.py tools.living_smoke --output .local/living-proof`

HA source additionally accepts `--managed`; use `--quality low` or
`--quality compatibility` for lower-tier checks. The native probe exercises the
300+100 bubble budget, hidden emitters, water pixels/freeze, a real parent visit,
committed eggs/portraits, 256 fish and repeated Classic/Tidal Garden rebuilds.
