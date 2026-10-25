> Historical v0.1 evidence, not current project status or an owner action list.
> See [README](../README.md) for current usage and support.

# v0.1 implementation report

Date: 2026-10-19. Development/verification record from the local first iteration; **no physical-radio, Pi, Windows
or hardware GPU acceptance**. No firmware publication, flashing, deployment or public listener. The aquarium
application is now prepared for publication in
[DrToxic/LoRagotchi-Aquarium](https://github.com/DrToxic/LoRagotchi-Aquarium).

## Result

Runnable native **Python/Panda3D** 3D aquarium plus isolated **LoRagotchi-RX**
firmware and the minimal normal-DX host-return feature. The stack is selected
for this prototype, not a declaration that original Pi/Zero packaging is solved.
The goal of accommodating that hardware family remains an explicit next gate.

Paths:

- Application: this repository (`LoRagotchi-Aquarium`)
- Firmware: separate `LoRagotchi-RX` checkout, branch
  `feature/community-tank-rx`, reviewed head **af5309a**, base **6a7b41a**.
  Parent review added CPU-width-independent RX numeric validation after the
  initial **d1e078f** prototype. RX USB/BLE images were rebuilt; unchanged normal
  DX images remain from d1e078f, with exact source recorded per artifact.
- Original DX checkout untouched. The app is a separate Git project; its exact
  source revision is available with `git rev-parse HEAD`.
- Aquarium publication preserves the owner-created README links and MIT licence;
  firmware remains separate and unpublished by this task.

## Run

```sh
cd LoRagotchi-Aquarium
uv sync --extra test
uv run loragotchi-tank --demo 16 --preset high
# headless visual check on this host
uv run python tools/headless_capture.py --demo 16 --preset high \
  --settings .local/settings.json --screenshot .local/aquarium-high.png --run-seconds 6
```

Replay: `uv run loragotchi-tank --replay docs/example-replay.jsonl`.
USB: `--connect serial:/dev/ttyUSB0`; Windows port: `serial:COM4`.
BLE: `--connect ble:ADDRESS`; authenticated TCP bridge instructions are in README.
No live connection was attempted during development.

## Implemented

- Original procedural real-3D fish family: stage sizes/silhouettes, distinct
  body/scales/eye colours and mono tint; tail/pectoral joints, smooth curved
  cruising, bank/pitch, depth variation, gentle separation and reef avoidance.
- Sand, caustics, fog, reef stones, vegetation, corals, bubbles, directional and
  ambient light. Static fish/scenery geometry batched; no proprietary artwork.
  Art is a coherent editable prototype, **not final SereneScreen fidelity**.
- Five graphics presets and individual CLI controls for implemented options;
  operator render-scale slider. Output resolution and internal scene size are
  separate; native UI stays at output resolution. Resize/fullscreen support.
- One shared simulation feeding one or two off-axis camera crops, not duplicated
  tanks. No hardcoded live 32-fish cap or quality-driven participant culling.
- Native operator panel, selecting/naming/removing copies, two-click end-session,
  connection/return status and bounded ordinary MeshCore inbox. Main thread never
  performs serial/network/database I/O; the service worker owns those boundaries.
- SQLite event deduplication, immutable ID validation, owner-key roster updates,
  colour preservation on incomplete re-share, durable-before-ACK workflow,
  independent return status. Demo/replay are memory-only by default.
- Concrete serial, BLE and authenticated TCP bridge adapters. BLE uses actual
  Nordic UART frame semantics and explicit <=20-byte LRX pull fragments. No
  debug-Serial scraping, fake remote DMs or competing PC LFG1 handler.
- RX four-slot intake/hold/return engine, full owner identity, bounded retries,
  independent durable outbox/status ACKs, two-bank journal, reset recovery, recent
  tombstones, storage failure admission guards, consumer lease/capabilities.
- RX has its own no-pet status UI. USB/BLE are separate V3 builds. Bridge is an
  explicit PC/SBC endpoint; onboard Wi-Fi is **not** pretended to exist.
- Normal DX adds Send visitor home and bounded return status/retries. Return
  mode stays mono/colour-appropriate; unsolicited RETURN, late ARRIVED and
  repeated packets are covered by extracted production-handler tests.

## Verification actually performed

| Check | Result |
|---|---|
| Application pytest | **19 passing**: parser, crash/save-before-ACK replay, identity collisions, refresh/colour policy, normal-message separation, actual TCP loopback/HMAC and serial PTY I/O, simulation/settings, firmware golden bytes and PC client against production C++ RX command core |
| Native renderer/operator smoke | **Passed**: roster, panel, quality/no culling, scale, resize, selection, removal, session clear; single/two-frustum frozen-world reconstruction mean RGB difference **0.0000021** |
| Production RX/return core | **13 scenarios passed**: duplicate/short COMMIT, hold/early recall, identity collisions, reset, full queue, failed persistence/ACK, bounded attempts, consumer lease, corrupt-bank fail-closed, stale tombstones, CPU-width-independent numeric boundaries |
| Extracted production DX handlers | **4 checks passed**: full-key identity, real mono/colour return, bounded retries, existing unsolicited return, late ARRIVED/duplicate RETURN, missing owner contact |
| New normal-DX menu route | **Passed with and without sound** from aquarium through Options; browse/send guards, disappearing guest and 128x64 status bounds |
| Firmware native suites | **99/99 passed** (`native`, `native_kiss_modem`) |
| Existing production UI checks | Menu, emoji/DX, local savings, happiness, lifecycle all exit 0 |
| Firmware builds | **5/5 passed**: V3 RX USB/BLE, V3/V4 normal DX, T096 normal DX UF2; one compiler job at a time |
| Artifact integrity | Four ESP32 checksum/hash/partition validations; T096 UF2 family/block/address validation |
| Python package | `uv sync --extra test` and wheel/sdist build succeed; bundled font licence/source assets retained |

Host runtime is CPython **3.12.14**, Panda3D **1.10.16**, x86_64 Linux. Rendering
was Mesa **llvmpipe**, OpenGL 4.5 compatibility under local Xvfb. It proves visual
and callback behavior, **not Pi FPS, accelerated GPU speed or physical input**.
Expected Xvfb warnings about `/dev/input` and XFree86-DGA do not represent an
attached device test. No live radio used. The C++ pipe fixture mocks radio/flash
boundaries while compiling the real production receiver/command implementation.

Evidence remains in `.local/` (app) and firmware `.local-dev/`, deliberately not
committed as generated logs/binaries. Specific logs: `pytest.log`,
`render-smoke.log`, `render.log`, `wall-render.log`, firmware
`final-build-results.json`, `regression-results.json`, `rx-core.log`,
`dx-handlers.log`, `return-menu.log`. Full artifacts in
[firmware-artifacts.json](firmware-artifacts.json).

PNG captures (actual native app, visually inspected):

- `.local/aquarium-high.png` — 1280×720, high, 16 synthetic fish.
- `.local/aquarium-controls.png` — operator panel, balanced profile.
- `.local/aquarium-two-tile.png` — 1920×1080 output, 960×540 scene, two cropped
  viewports sharing the same simulation. Low quality is intentionally visible.

## Honest support matrix / remaining work

Parent review recovered the completed local work after the completion handoff
failed to surface in chat. App tests were rerun (19 passed) and native rendering/
operator/two-view checks passed under software GL. The RX source review found
that `strtoul` overflow handling depended on host word size; checked decimal
accumulation now rejects overflow before multiplication on both MCU and host.
Thirteen production-core scenarios and both rebuilt RX images pass; esptool
checksum/hash validation was repeated. All five firmware files match the updated
manifest. Original accepted DX checkout remains unchanged. This is a local
prototype review, not an exhaustive audit or physical hardware acceptance.

| Area | Implemented / tested | Still outstanding |
|---|---|---|
| Linux desktop | Native app rendered and callbacks tested on x86_64 software GL | Real GPU/X11/Wayland/session behavior |
| Raspberry Pi | One scalable real-3D renderer, low/compatibility profiles | All physical Pi tests; especially ARMv6/32-bit build/install path and acceptable original Pi/Zero performance |
| Windows | Cross-platform dependencies, COM ports, packaging source | Runtime, fullscreen, USB/BLE and installer checks |
| macOS | No intentionally Linux-only app API outside optional test tooling | Entirely untested, opportunistic |
| 4K / walls | Arbitrary output size, internal scaling, 1/2 contiguous crops | 4K throughput, actual multi-monitor modes, arbitrary tile grid/orientation/bezel calibration, distributed LAN rendering/frame sync |
| USB | Firmware compiled; PC adapter real PTY I/O tested | Physical cable/board handoff, unplug/replug |
| BLE | V3 BLE compiled; real Bleak adapter; small-fragment core exercised | Pairing, notifications, reconnect on actual hardware/OS; ordinary inbox disabled if MTU >=179 cannot be confirmed |
| WLAN | Authenticated bridge endpoint and TCP client exercised via loopback | Physical trusted LAN, attached radio, optional on-board endpoint; HMAC does not encrypt |
| RX storage | Production journal code compiled, core faults/restarts tested | Physical power cuts/torn SPIFFS writes/wear; existing mounted filesystem required; no auto-format or erase recovery |
| RX capacity/recovery | Four slots, safe BUSY, unresolved jobs retained, protocol retry op | UI for retrying unresolved jobs and diagnosing full backlog; contact/RF management still external |
| Appearance | Original editable 3D family with four stage variants/traits | Art direction polish, more graceful fish silhouettes/animation, more family models; no invented species |
| Expensive graphics | Lighting, caustics, geometry density, bubbles | Shadows/reflections/AA/postprocessing, auto-performance/hysteresis, renderer capability-based fallback; no nonfunctional controls shown |
| Product lifecycle | Session copies, re-share refresh, removal and ending session | User preference on timed retention, packaging/kiosk/screensaver integration |

An RX transport ACK does not prove the owner has displayed/saved HOME. No such
legacy receipt exists, and none was invented. Physical acceptance should first
exercise unplugged-PC visits and repeated/power-interrupted returns between
accepted DX and RX before a firmware release or deployment decision.
