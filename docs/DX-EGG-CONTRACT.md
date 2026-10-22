# Aquarium → DX egg handoff: integration boundary (not a wire specification)

Aquarium can now keep immutable local eggs and parent appearances. Firmware work
is owned by the separate DX session. Neither repository's firmware is modified.

Before any transfer implementation, agree:

- Versioned discover/list/select protocol, advertised only when both ends support
  it; an ordinary aquarium visit must remain compatible with existing firmware.
- Exact offspring fields, valid palette/tint ranges, RGB565 quantisation and
  inheritance colour space. The local linear-sRGB preview is not authoritative.
- Globally unique egg ID, aquarium identity, complete destination owner identity,
  transaction nonce and parent provenance that fits the existing MTU/message budget.
- Durable claim reservation with expiry and idempotent retries. Do not mark an egg
  consumed because a message was sent, a link ACK arrived, or a timeout occurred.
- DX persistence before commit acknowledgement; aquarium persistence before final
  confirmation; recovery query for interrupted/ambiguous commits. One egg cannot
  be delivered to two devices. Retain transaction history sufficient for replay
  rejection after restart.
- Existing pet replacement and the dismissible discovery/skip screen are firmware
  decisions, not implied permission for Aquarium to overwrite a pet.
- Capability absence, cancellation, offline HA and storage failure leave eggs
  intact. No credentials or private keys in protocol traces or parent portraits.

Current implementation deliberately has no claim/send endpoint. No LFG1/LRX opcode
or allocation is invented here. A future migration must preserve existing egg IDs,
parents, stored preview fractions and explicit inheritance version, not reroll them.
