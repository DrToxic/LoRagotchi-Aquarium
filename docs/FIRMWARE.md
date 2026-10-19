# Firmware handoff (separate project)

The RX/DX firmware is maintained separately; it is not included in this
repository. The build evidence below describes the local prototype, not a
published firmware download. Checkout name: `LoRagotchi-RX`.

Branch: `feature/community-tank-rx`, accepted base `6a7b41a`.
Reviewed RX source commit: `af5309a`; unchanged normal-DX images use `d1e078f`
(full hashes per image in `firmware-artifacts.json`).
The original `LoRagotchi-DX` checkout remains on its accepted
branch/revision with no checked-out source changes.

See the firmware's `COMMUNITY-RX.md` for build commands, behavior and hardware
checklist. This application does not flash, configure or transmit DMs through
that firmware. No flashing, RF operation, push, PR, release or public service was
performed by this implementation task.

## Tested build targets

| Environment | Product | Artifact | Bytes | Format validation |
|---|---|---|---:|---|
| Heltec_v3_LoRagotchi_RX_usb | Heltec V3 RX / USB | firmware.bin | 652512 | ESP32 checksum/hash, app partition at 0x10000 |
| Heltec_v3_LoRagotchi_RX_ble | Heltec V3 RX / BLE | firmware.bin | 1276784 | ESP32 checksum/hash, app partition at 0x10000 |
| Heltec_v3_LoRaFish_companion_ble | Normal V3 DX + host return | firmware.bin | 1317872 | ESP32 checksum/hash, app partition at 0x10000 |
| heltec_v4_LoRaFish_companion_ble | Normal V4 DX + host return | firmware.bin | 1317936 | ESP32 checksum/hash, app partition at 0x10000 |
| Heltec_t096_LoRaFish_companion_ble | Normal T096 DX + host return | firmware.uf2 | 966656 | family 0xada52840, 1888 blocks, 0x26000..0x9c000 exclusive |

Each is under `LoRagotchi-RX/.pio/build/<environment>/`. Full SHA-256 hashes and
paths relative to the separate RX checkout: [firmware-artifacts.json](firmware-artifacts.json).
ESP32 application binaries are **not merged installers** and are not offset-zero
images. No data-preservation or hardware-acceptance claim is made. Keep the
accepted `6a7b41a` firmware as the known-good rollback reference when a separately
authorized physical test is arranged.

No T096/V4 **RX** build is supplied: the new RX journal backend is explicitly
ESP32 SPIFFS and only V3 RX targets were defined/compiled. T096/V4 builds above
verify the normal-DX changes, not an unsupported receiver port.

The first receiver UI is status-only. Contact/RF setup uses existing MeshCore
management tools, disconnected from the aquarium's exclusive consumer connection.
Saved node names override the fresh `Community Tank 🐟` default. RX requires an
existing mountable SPIFFS filesystem and refuses automatic formatting on failure.

## Changed production code map

- `LoRagotchiRX.h`: transport-independent production intake/return/outbox core.
- `LoRagotchiRXBridge.{h,cpp}`: ESP32 two-bank journal and MeshCore boundaries.
- `ui-rx/UITask.h`: receiver-only screen; no pet/care/breeding state.
- `MyMesh.{h,cpp}`: bounded owner-key-bound normal-DX return plus guarded RX hooks.
- `LoRaFishGuestReturn.h`: normal-DX return retry/ACK tracking.
- `ui-new/LoRaFishMenu.h`, `ui-new/UITask.cpp`: optional Send visitor home action,
  destination identity capture and return status display.
- `main.cpp`: guarded RX initialization and no-auto-format RX mount policy.
- `variants/heltec_v3/platformio.ini`: two explicitly selected RX targets.

No files in shared `src/`, radio/board pin settings, partitions, BLE internals or
RF defaults were changed. Normal DX keeps pet/lifecycle/care behavior and the
existing mono/colour return policy.
