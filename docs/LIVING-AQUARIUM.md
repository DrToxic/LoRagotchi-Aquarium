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

**Current release:** these are local eggs, not transferable DX genomes. The rule
is versioned `local-linear-srgb-v1`; `firmware_genome` remains null. No egg is
removed, claimed, acknowledged or transmitted by the aquarium.

### Egg adoption integration status

The DX-side [EGG-ADOPTION.md specification](https://github.com/DrToxic/LoRagotchi-DX/blob/feature/egg-adoption-colours/EGG-ADOPTION.md)
defines LEG1 capability negotiation and delivery, H1 hue genes, identity binding
and durable DX receipts. It supersedes the former aquarium boundary checklist.
RX forwarding and aquarium integration are still required; this is not a working
end-to-end adoption feature yet.

**Agreed gameplay (2026-10-24; not implemented by this documentation change):**

- Keep new-pet/reset adoption and select the egg in the aquarium app.
- Add **Options → Adopt an egg** when a saved designated 🥚 aquarium companion
  exists and the pet has no pending successor egg. The emoji is a discovery hint;
  a successful capability handshake must precede transfer.
- With a living pet, adoption fills the empty successor slot instead of breeding.
  It does not replace or reset the living pet or overwrite an existing egg.
- Generation follows the player's lineage: succession advances the local counter
  normally, not to the donor's generation. Donor parents remain provenance.

**Agreed existing-egg migration and preview policy (implementation pending):**
preserve egg IDs, parents, stored preview data and random choices; derive
DX-compatible H1 genes once, without rerolling the egg. Before adoption, offer
an optional reveal of the actual adoption colours, or let the player keep them
a surprise. Revealing or hiding the preview must not change genes or eligibility.
Do not force a colour reveal as part of confirmation or pass off the historical
RGB preview as an exact DX colour match. Both choices use the same durable
reservation and confirmation flow.

**Implementation requirements, not additional owner decisions:** persist an
exclusive reservation before delivery; bind it to full device identity and the
transaction; retry identical payloads; consume only after a durable DX receipt.
A link ACK or timeout is not proof of adoption. Ambiguous deliveries stay reserved
until reconciled, including after restart. Preserve transaction history and
existing egg identity/provenance. Capability absence, offline service and storage
failure must not silently consume eggs. No credentials belong in protocol logs.

The current DX specification describes fresh/reset adoption and has a finite
receipt-replay window. Successor adoption, player-generation handling and robust
reconciliation must be implemented and verified across DX/RX/app before enabling
this flow. These engineering gaps are not resolved merely by deleting a checklist.

## Games using mesh messages

Two people can play **noughts and crosses**, **guess the number**, or
**open-deck blackjack** by exchanging short messages in MeshCore direct chat.
Standalone 0.9.0 and HA 0.3.0-preview.10 use the same game format and can play
against each other. Each player needs their own game state and a way to send
and receive direct messages; no visiting fish or nursery egg is required.

**This is manual copy/paste, not automatic radio integration.** The game page
prepares a message; you send it through your existing chat client. Receiving a
chat message does not advance the game until you paste it into the game page.
Do not add a second radio connection just to play.

### Open the games

- **Standalone:** in the separate controls window, choose **Aquarium → Mesh
  message games**.
- **Home Assistant:** open the app Web UI's add-on-relative `setup.html` page,
  then select **Mesh message games**. The game page is `games.html`, alongside
  `setup.html`, not inside the aquarium display. When navigating by URL, retain
  the full existing ingress prefix and replace only the page suffix. If HA has
  wrapped the app in a frame, open the aquarium frame in its own tab first;
  appending `games.html` to HA's outer `/hassio/…` address will not work. Do not
  share or save temporary ingress-session URLs as dashboard links.

The HA aquarium stream remains read-only. Game moves happen on the separate
page, not by clicking fish or sending input to the stream.

### Start and exchange turns

Decide who will create the game (**player 1**) and who will join (**player 2**).
Use a direct chat with that same person for the whole game.

1. **Player 1:** choose a game in the dropdown and click **New game (player 1)**
   (HA: **New game · player 1**).
2. Copy the invitation using **Copy outgoing turn** on desktop or **Copy turn**
   on HA. Send that complete text in your direct chat. It starts with `LAG1|`.
3. **Player 2:** copy only the received `LAG1|…` text into the incoming-message
   field, then click **Join pasted invitation** (HA adds **· player 2**).
   The invitation selects the game; the joiner's dropdown need not match.
4. Check the status for whose turn it is. Make your move using the rules below.
   **Every successful move must be copied and sent to the other player.**
5. The other player pastes the message into their incoming field and clicks
   **Receive turn**. Use this button for subsequent messages, **not Join**:
   joining replaces your current local game and makes you player 2.
6. Repeat until the game reports a result. **Send and receive the final turn
   too**, so both players see the result. For a rematch, create a new game and
   exchange its invitation; swap who creates it if you want to swap roles.

Copy the entire single message, without chat timestamps, sender names, quotation
marks or Markdown fences. Do not edit the text. Messages fit 160 UTF-8 bytes and
include the game ID and turn history. Verify the sender in your chat client:
`LAG1` does not authenticate the person sending it.

### Noughts and crosses (tic-tac-toe)

**Player 1 is X and moves first; player 2 is O.** Get three of your marks in a
row, column or diagonal. A full board without a winning line is a draw.

Squares are numbered left-to-right, top-to-bottom:

```text
1 | 2 | 3
--+---+--
4 | 5 | 6
--+---+--
7 | 8 | 9
```

- **Desktop:** enter an empty square's number, `1`–`9`, and click
  **Play / give clue**.
- **HA:** click an available numbered square. Occupied squares and moves outside
  your turn are disabled.
- Copy/send the outgoing turn after each move; the other player imports it with
  **Receive turn** before playing.

**First-game walkthrough:** create and join an invitation as above. Player 1
plays `1` and sends; player 2 receives, plays `4` and sends. Player 1 receives,
plays `2` and sends; player 2 receives, plays `5` and sends. Player 1 receives,
plays `3` and sends. Player 2 receives the final message: X has the top row and
both sides show **Player 1 wins**.

### Guess the number

**Player 1 hosts; player 2 guesses first.** The app randomly chooses a secret
whole number from **1 to 20** for the host. The host does not type or choose it.
The invitation locks in that number without revealing it.

1. Player 2 enters a whole number in the displayed remaining range, clicks
   **Play / give clue**, then copies and sends the turn.
2. Player 1 imports it with **Receive turn**, then clicks **Play / give clue**
   to generate the truthful clue automatically. No number or clue text is needed
   from the host (desktop ignores the move field; HA hides it).
3. Player 1 copies/sends that clue; player 2 receives it. The displayed range
   narrows: a higher secret raises the lower bound; a lower secret lowers the
   upper bound. Guess again within that range.
4. A correct guess ends the game after the host sends the final clue. The game
   also ends after the host answers the tenth guess. The final message reveals
   the number and checks it against the invitation and every previous clue.
   Both sides display **Number verified: …** once they have that final state.

Example: if the secret is 14 and the guest guesses 10, the host's automatic clue
changes the guest's range to **11–20** after it is received. Guessing 14 next,
followed by the host's final clue, completes the game. For fewer guesses, try
near the middle of the remaining range.

The host must keep their private saved state to continue after closing the app.
The invitation alone cannot recover the unrevealed number. Share only outgoing
turn text, **never the saved-game JSON**.

### Open-deck blackjack

A casual two-player comparison, **not casino blackjack**: no dealer, betting,
splits, doubles, hidden cards or special natural-blackjack payout. Both sides
use the same reproducible open deck; it is not a secret or secure shuffle.

- Each player starts with two cards. The page displays both hand totals.
  **Player 1 acts first.**
- Enter **`hit`** to draw one card or **`stand`** to keep your total, then click
  **Play / give clue**. The short forms `h` and `s` also work.
- Copy/send each action and receive your opponent's reply. Turns alternate
  while both players are active; this is not “finish your whole hand first.”
- After a hit reaches **21 or more**, that hand automatically stops. Standing
  also stops your hand. If your opponent has stopped, you may take consecutive
  actions until you stand or reach 21 or more. Still send your latest turn.
- Number cards count at face value, J/Q/K count as 10, and aces count as 1 or 11
  to give the best total without busting. Above 21 is a bust.
- Once both hands have stopped, the highest total of 21 or less wins. A bust
  loses to any non-busted hand. Equal totals, or two busted hands, are a draw.

An initial two-card 21 still asks for an action: choose **stand** to keep it.
Follow the displayed turn prompt rather than assuming an automatic win.

### Saving, lost messages and troubleshooting

There is **one current saved game per desktop settings location or HA browser
storage context**, not a list of concurrent matches. Starting or joining another
game replaces it. Use separate browsers/profiles/devices for two players testing
against the same HA app; two tabs sharing storage are not independent save slots.

- **Nothing happened after sending in chat:** the recipient must paste the text
  into the game and click **Receive turn**. There are no automatic imports,
  retries or background game transmissions.
- **Lost message:** the sender copies and resends their latest outgoing turn.
  Matching duplicate/older messages leave the game unchanged. Do not start a
  new game to retry delivery.
- **Wait for the other player / disabled moves:** receive their latest turn
  first; the game may also already be over. In guessing, the guest starts and
  the host must send a clue after every guess.
- **Different game:** check that both sides are using the same invitation and
  that neither has started a rematch. Receive cannot switch games. Join a new
  invitation only when you intend to replace the current game as player 2.
- **Conflicting history / attempted local turn:** the message is rejected and
  the current game is unchanged. Confirm the peer and resend the last agreed
  turn. If you cannot recover a common state, agree to start a fresh game.
- **Incomplete/invalid message:** copy only the complete `LAG1|…` text again;
  do not reconstruct or hand-edit it. Illegal moves and occupied squares are
  rejected; choose a legal move instead.
- **Clipboard blocked:** desktop puts the outgoing message into its text field
  for manual selection/copy. HA selects **Your outgoing turn** for manual copy.
  Copy that message and send it yourself.
- **Desktop restart:** the game reloads from `aquarium-game.json` beside the
  settings file. Keep the same settings location and retain that file.
- **HA reload:** the game restores from that browser's local storage. It is not
  an HA-wide save shared across devices. Clearing site data or switching browser
  profiles loses access to that local save. If storage is unavailable, keep the
  page open; it warns that the game cannot be saved.
- **Lost host save in guessing:** the public invitation cannot restore the
  private number. Start a new game together. Do not rejoin your own invitation
  as a substitute for restoring the host save.

### Message format (for compatible clients)

Players should use the copy buttons; no protocol knowledge is needed to play.

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
