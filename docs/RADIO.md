# Radio workspace · v0.2.0

Open **Radio → Connection** and connect using the existing form. Other tabs use
that exact connection, not another serial handle or another client application.
The aquarium continues receiving/committing/acknowledging fish while you chat.
LoRagotchi-RX firmware is still required; this is not a standalone stock-radio
client for devices without the LRX extension.

## Chat

Choose Channels or Direct messages, then a conversation. Menus show ten items
at a time; Previous/Next reaches the rest. Unknown DM senders are shown by their
six-byte prefix. Save the contact on the radio before replying. If multiple
contacts share that prefix, sending is disabled rather than guessing.

Type a message, then click Send or press Ctrl+Enter in the composer. The byte
counter accounts for UTF-8; messages are rejected rather than silently cut off.
DMs allow 160 bytes. Channel messages reserve space for the node-name prefix
the firmware adds. No splitting, scheduled sends, or automatic retries occur.

- **Sent:** the radio accepted a channel message; not a delivery receipt.
- **Pending:** the radio accepted a DM and an ACK is being awaited.
- **Delivered:** the radio reported its matching MeshCore ACK, not proof a human
  read the message.
- **Unconfirmed:** no ACK before the radio's suggested timeout plus a grace
  period, a disconnect, or an interrupted command. Do not assume it failed.
- **Failed:** explicit rejection by the radio.

Rejected/interrupted sends retain the draft. A successful send clears only the
matching draft, not newly typed text. Changing conversations retains drafts in
memory. A different RX identity clears them. Drafts are not saved on disk.

History lives in a separate `radio_messages` table in the existing live SQLite
file, scoped to RX identity and conversation. It persists across restarts, with
a global bound of **5,000 messages** per database (oldest trimmed). Latest/Older
pages show up to 60 messages. Received retransmissions are deduplicated using
source/timestamp/content, not arrival time. Reusing a channel slot with different
metadata/key gives it a new history identity. The identity fingerprint differs
between direct and bridged connections because the bridge redacts channel keys.
After disconnecting, conversations from the current radio remain browsable.
After restarting the application, reconnect to select that radio's history.

Ordinary channel chat still feeds the existing `#loragotchi-dx` aquarium bubbles.
DMs, other channels, and LFG1 protocol text do not appear on aquarium outputs.

## Contacts and channels

Contacts supports full-key-backed search and paging, Favorites, rename,
add discovered advertisements, remove, reset path, share advertisement on air,
and import/export `meshcore://` contact URLs. Discovered is a bounded list of
advertisements received by the connected companion, not an active RF scan.
The radio's Manual/Auto-add setting still governs firmware-side admission.
Removing a contact needs a second click; local chat history is retained.

Channels displays all firmware-reported slots. `#hashtag` channels derive the
standard first-16-byte SHA256 key. Private names require a supplied 16-byte key
(32 hex characters). Existing keys are not displayed or saved in chat/settings;
there is no channel-key export. Overwriting/clearing an occupied slot needs a
second click within eight seconds. Clearing `#loragotchi-dx` affects reception
of the aquarium's public chat; it does not delete fish or their history.

## Device and Tools

Device shows identity, firmware/model, battery and storage. Explicit buttons
set name, frequency/bandwidth/SF/CR, TX power and coordinates, manual-contact and
advertised-location policies, and clock. RF changes need a second click.
Unedited repeat, telemetry and multi-ACK preferences are preserved. The radio
enforces board-specific values; choose RF settings appropriate for your region.
Local/flood advertisement buttons transmit only when clicked.

Tools selects a saved contact for remote login/logout, command text, status,
telemetry, route discovery and manual path editing (1–3 bytes per hop). Remote
permissions and firmware capabilities still apply. Login passwords are masked,
cleared after queueing and never recorded in application logs or history. Use
the dedicated password field: arbitrary remote command text is stored in the
conversation, so do not put secrets in command text. Remote replies arrive
asynchronously in Activity or direct chat. Activity is scrollable and bounded.
Local radio statistics query core/radio/packet counters without an RF send.

## Keyboard and clipboard

While editing a field, aquarium keyboard shortcuts are suppressed.

- Ctrl+C copies the **whole field**, Ctrl+X copies and clears it.
- Ctrl+V inserts at the cursor; Ctrl+Shift+V replaces the field.
- Masked secret/password fields cannot be copied.
- Ctrl+Enter sends only from the Chat composer; ordinary Enter does not send.

Clipboard access uses Python's Tk binding with a hidden owner window, keeping
all visible controls native Panda3D. If the Python installation lacks Tk (for
example distro Python without `python3-tk` on Linux), manual entry still works
and a clipboard error is displayed. The bundled Aquarium Entry font combines
the existing OFL Liberation Sans/Noto Emoji outlines for editable text. Its
generator and both original licenses are included. Original Unicode wire and
database text is preserved; this is not full-script/colour/ZWJ shaping support.

## Transports

**USB:** full implemented command set over the existing 115200 baud connection.
Do not open another app on the same serial port.

**Bluetooth:** fish fragments remain at most 20 bytes. Chat/contacts/settings
require a negotiated MTU of at least 179; operations are disabled if Bleak cannot
confirm it. Writes are bounded by MTU and never split into speculative fragments.
OS pairing/PIN workflow remains unchanged. Hardware BLE behavior is unverified.

**LAN bridge:** update **both sides** to v0.2.0. Reads are allowed by default;
stock-client writes require this explicit bridge option:

```sh
uv run loragotchi-rx-bridge --radio serial:/dev/ttyUSB0 \
  --token-file .local/rx.token --radio-control
```

The bind remains loopback unless explicitly configured otherwise. The bridge
still has one authenticated consumer and a strict command/length allowlist.
Channel secret bytes are replaced with non-secret fingerprints and BLE PIN bytes
are zeroed in metadata responses. Private-key/signing/raw-packet/factory-reset/
reboot/unrestricted-local-CLI commands remain denied. The existing transport is
not encrypted or server-authenticated: use a trusted network or SSH tunnel.
This update does not claim to remediate every earlier audit finding.

## Scope and validation

Implemented: ordinary client communications, contact/channel management,
everyday device configuration and remote-node operations listed above.
Not implemented: maps/tiles, QR camera workflows, firmware flashing, identity
key backup/import/signing, raw packets, arbitrary local CLI or every advanced
firmware setting. It is not advertised as complete stock-app parity.

Source preflight: maintained `meshcore_py` 2.3.17 and its companion command
layout were reviewed alongside this project's RX firmware. Using a second
library-owned connection would break exclusive serial ownership, so the stock
commands are implemented on the existing transport. Cayenne LPP decoding reuses
the MIT `pycayennelpp` 2.4.0 dependency rather than inventing a sensor codec.

See [v0.2.0 verification](TESTING-v0.2.0.md). Physical radios, real RF delivery,
Windows clipboard/serial/BLE and mixed-DPI behavior need owner acceptance.
