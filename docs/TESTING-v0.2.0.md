# v0.2.0 · shared Radio workspace verification

The new workspace uses the same native operator window, radio worker,
transport and SQLite connection as the aquarium. No physical radio was opened,
flashed or transmitted through during development. The firmware trees were
read as protocol references and not modified.

## Automated coverage

`uv run pytest -q` covers the existing fish/rendering/protocol suite plus:

- Stock wire fixtures: contacts including zero-valued path hashes, signed DM
  headers, exact CLI text types, UTF-8 byte limits and invalid RF/path inputs.
- One session handling fish snapshot commit/ACKs, multi-contact streams,
  channel metadata, channel sends, DMs and ACK pushes before/after responses.
- Explicit rejection, timeout, pending expiry and restart states with no
  automatic resend; ambiguous six-byte contact prefixes fail closed.
- Contact edits retain unrelated path/identity fields; channel changes isolate
  histories and never publish secret bytes; preferences preserve other flags.
- Bounded persistent chat history, duplicate suppression, earlier pages,
  RX-identity isolation, disconnect browsing, and queued-action generation guards.
- Real POSIX serial PTY exchange using framed bytes and an independent controlled
  companion peer, plus actual TCP/HMAC bridge I/O in read-only and write-enabled
  modes. No second serial owner, radio worker/renderer thread crossover or
  actual RF is used by these tests.
- BLE payload bounds/cancellation, allowlist rejection and metadata key/PIN
  redaction; decoded/unknown/truncated Cayenne LPP telemetry.

The native Radio suite (`uv run python -m tools.run_native tools.radio_smoke`)
exercises all six sub-tabs, connection form, channel/DM history and sending,
delivery state, Unicode editing, actual X11 clipboard round-trip, input shortcut
isolation, more than ten contacts/channels, discovered contact admission, device
controls, statistics, disconnect and retained aquarium fish. Screenshots are
saved under `.local/radio-ui/` for visual inspection.

The package verification runner installs the exact source ZIP in a fresh,
isolated directory, checks every archive member and wheel asset, and runs unit
tests plus ten native suites: Radio, operator, transitions, renderer, options,
deadzones, Unicode text, chat bubbles, framing and projection. Native log gates
reject glyph/property/GL errors. Two tests requiring optional sibling firmware
trees skip in an isolated source ZIP; they run in the main development checkout.
Development evidence is retained in `.local/v020-*-verification.json` and logs.

## Physical acceptance still needed

1. Extract the ZIP into a new directory; install/update dependencies with
   `uv sync --extra test` or `python -m pip install -e .`. Existing user settings
   and live SQLite storage are retained; no reset or migration of fish is needed.
2. Windows: open Radio → Connection, choose the RX COM port, and connect.
   Open Chat; confirm channels, full contact list and device name/settings load.
3. Exchange a channel message and a DM with another actual node. Verify the
   difference between channel enqueue, DM ACK and no-ACK/failed states. Check
   Unicode, clipboard and a new fish arrival while chat remains open.
4. Try favorite/rename and a disposable test channel. Confirm the second-click
   overwrite/remove interaction. Check a compatible repeater/room login and
   status/telemetry response; only change RF settings intentionally.
5. Unplug/reconnect and disconnect while a send is pending. Existing fish and
   chat history must remain; a message must not be resent automatically.
6. For BLE, confirm the OS-reported negotiated MTU permits stock messages; a
   low/unknown MTU should leave fish intake available but other tabs disabled.
7. For LAN, update both copies. Confirm writes fail in default read-only mode
   and work only with the bridge's explicit `--radio-control` option.

Linux/Xvfb/Mesa software rendering is evidence for these native paths, not proof
of Windows/NVIDIA, mixed DPI, physical BLE/USB/RF or Raspberry Pi performance.
This is feature verification, not a new full-project security audit.
