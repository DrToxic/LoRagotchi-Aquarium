# Fish lifespan

Expiry is **off by default** and controls aquarium copies, not the original pet.

- **Standalone:** Aquarium → Fish lifespan. Choose After last share, enter Hours
  or Days, then Apply lifespan. Fractions are accepted; maximum 365 days.
- **Home Assistant:** Configuration → Fish lifespan (hours). `0` is off,
  `24` is one day, `168` is a week; maximum `8760`. Save + Restart.
- Quick test: `0.02` hours is 72 seconds. Demo copies use their local fixture
  receipt time and stay isolated from live collections.

A genuinely new accepted snapshot renews its timer, including unchanged
appearance. Duplicate stored RX events, older RX events, duplicate HA COMMITs,
return status, restarts, graphics changes and desktop window transfers do not.
Each owner keeps one current copy; duplicate names remain separate identities.

The timestamp is persisted in UTC in the existing fish database. Existing valid
SQLite timestamps are honored without resetting them or rewriting the database.
Time spent shut down counts. Correct system time is required; DST and display
lighting timezone do not affect expiry. Undated/damaged legacy timestamps retain
their copies and are reported as undated until a genuine new share provides a time.

Expiry removes the copy from the **desired active roster**, then uses the chosen
exit animation. With animations disabled it disappears immediately. A copy already
expired at startup is not rendered just to animate it away. Interrupted arrivals
and desktop transfers yield to the removal, and a new share can return once.

Snapshots and event history are retained. No expired flag is written into manual
hiding: disabling expiry or increasing the lifespan can make retained copies
eligible again. Explicit Remove copy / End display session remains hidden until
a genuinely new accepted share. Expiry does not prune the database.

The timer is based on when Aquarium first commits a share, not the sender's
unavailable wall-clock time. An RX snapshot first downloaded after an offline
period gets its first local receipt time; re-downloading a known event does not
refresh it. JSONL replay is synthetic/offline input, not a live renewal mechanism.

HA keeps expiry independent of its receiver/return state machine. Accepted return
jobs continue even if their display copy expires or the renderer crashes. A
running display caches accepted timestamps and can expire known copies during a
backend outage. HA Logs report active/expired/undated counts on change. Direct RX
mode checks on its storage worker (normally within one second; transport work can
delay the check). HA display checks follow its half-second IPC loop.

## Acceptance checks

Use a disposable/demo collection first. Verify expiry off leaves copies alone;
short lifespan expires them; restart does not renew them; longer/off restores only
expired copies; a real new share refreshes unchanged appearance; manual hiding
stays hidden when changing the rule. Test Windows native and actual HAOS update
behavior on the target systems. No firmware update is required.
