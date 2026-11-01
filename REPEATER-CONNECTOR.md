# Stock repeater tank adapter

The local RX feature/repeater-tank-connector branch supplies stock MeshCore 1.18.0
repeater firmware with durable Water/legacy intake. It is not a companion-radio
firmware. HELLO link flags 0x80 identify this LRX-only role; low bits are 1 USB,
2 BLE or 4 onboard Wi-Fi. This adapter suppresses companion polling, Radio tab
refresh/config/chat and bridge-control negotiation, but leaves fish polling,
Water capability negotiation, SQLite-before-ACK and reconnect/replay unchanged.
The Radio panel identifies the role. Manage using the stock repeater USB CLI or
authenticated over-radio admin, not the tank connection. Older companion RX
profiles behave as before, including the BLE MTU restriction for chat.

Use the existing USB serial or BLE connections. Onboard Wi-Fi uses the existing
Network connection tcp:HOST:8765, with the same raw 32-byte token file and
LRXB/HMAC-SHA256 handshake as the PC/SBC bridge; no anonymous direct-radio URI
or automatic credential fallback is added. Provision the token's hex encoding
on physical USB as described in RX's REPEATER-TANK.md. HMAC authenticates clients
but does not encrypt/protect later TCP frames or authenticate the server. Trusted
protected LAN/WLAN or VPN only; never expose it publicly. A printable 64-character
hex file is not the required raw token file. No credentials are created here.

Separate RX USB/BLE/Wi-Fi images avoid carrier/management conflicts. ESP32 V3/V4
OLED have Wi-Fi; nRF52840 T096 has USB/BLE, **no onboard Wi-Fi hardware**. Only one
tank consumer/connection is supported. Existing HA MeshCoMod/HACS overlay remains
unchanged; this is not its multi-client companion protocol.

A patched DX picker is required because ordinary DX deliberately filters out
repeater adverts. DrToxic's separate feature/repeater-tank-destinations sender
branch accepts fish-marked repeaters with exact "LRX1 " name prefix without
misadvertising the repeater as a companion. Wire compatibility is not picker
compatibility. All source changes are local, unpushed and unflashed.

Tests: pytest -q tests/test_repeater_connector.py tests/test_adapters.py tests/test_radio.py
Production repeater/RX/SQLite boundary test lives in RX test/rx/check_repeater.py.
Mocks and local compiles do not prove physical BLE, USB, Wi-Fi, RF or power-cut
behavior. Renderer/deployment and installed HA source are not changed here.
