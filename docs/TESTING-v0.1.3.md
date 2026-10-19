# v0.1.3: compact options and RX connection controls

## Changes

- Native DirectGUI controls use a 432×594 **output-pixel** panel, anchored at the
  top right. It no longer stretches its spacing with display height. Smaller
  windows scale the panel down to fit. Aquarium and RX Radio tabs separate
  graphics/fish controls from connection details.
- USB port discovery/manual port entry, BLE discovery/manual address entry, and
  authenticated network bridge host/port/token-file controls use the existing
  pyserial/Bleak/socket adapters. No new dependency or radio firmware change.
- Connect/disconnect and visible connection/retry/error states work without
  restarting the renderer. The service worker owns discovery, token-file reads,
  transport lifecycle and SQLite. UI callbacks only queue work.
- Input focus suppresses aquarium shortcuts while editing a field; Tab cycles
  fields and Escape closes controls. Selecting a tab or clicking a button releases
  text focus. Existing shortcuts still operate when not editing.
- Connection preferences persist beside graphics settings, but only the token
  file path is stored. Saved preferences do not cause an automatic connection.
- Demo/replay switching opens the separate live store before replacing the
  synthetic/recorded view. Invalid token files or storage errors preserve the
  existing collection. Disconnect retains live copies and stops retries.
- Superseded connection requests cannot begin a late handshake. BLE connection
  cancellation and failed TCP handshakes close their private loop/socket resources.

## Evidence and reproduction

```sh
uv sync --extra test
uv run pytest -q
uv run python tools/run_render_smoke.py
uv run python -m tools.options_smoke
```

The options smoke launches a temporary Xvfb display and an isolated settings/live
store. It uses a simulated RX protocol peer and mocked discovery; it never scans
physical devices or opens the user's saved live database.

Checks include:

- Panel dimensions/containment at 1280×720, 2560×1440, 3840×2160 and 800×450;
  screenshots of graphics and radio tabs inspected.
- Actual native menu/button callbacks: discovered device selection, transport
  switching, retained fields, malformed-port validation, entry-focus shortcut
  suppression, demo-to-live switching, connect/disconnect/reconnect.
- Worker integration through an **actual authenticated loopback TCP socket**,
  production LRX client and SQLite, with a simulated radio behind the bridge.
  Demo and live database counts prove synthetic records are not carried across.
- Connection failure/retry, cancellation while opening, failed capability
  handshake cleanup, invalid token/storage failure, worker-thread discovery,
  BLE cancellation cleanup and TCP incomplete-handshake socket cleanup.
- Existing 256-fish native renderer/name-cache checks, fullscreen restore,
  separate windows, frozen-world reconstruction, offset resizing, close/reopen
  lifecycle and fish removal/session clearing.

No physical radio, BLE adapter, Windows desktop or Pi was used for these checks.
BLE discovery/pairing, USB device identification and actual RX interoperability
need owner hardware testing. Xvfb/Mesa output verifies this Linux software-rendered
path; it does not measure Windows/NVIDIA or Pi frame pacing. A listed serial/BLE
device is not automatically RX-compatible; the capability handshake determines
that after Connect. Stock MeshCore/DX firmware does not supply the LRX extension.

## Owner test

```sh
uv sync
uv run loragotchi-tank --demo 256 --preset high
```

Press Tab and check the tighter Aquarium tab. Open RX Radio, choose the connection
method, select/enter the radio details and click Connect. On a real RX, verify the
status progresses to connected and a shared fish arrives. Disconnect and confirm
that the saved fish remains. Reconnect and verify replay does not create copies.
Use the bridge token **file path**, not its contents, for network connections.

Only use an RX build supporting the documented protocol. BLE pairing stays in
Windows/macOS/Linux device settings; no PIN or wireless password is stored here.
