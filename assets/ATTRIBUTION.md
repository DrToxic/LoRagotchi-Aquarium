# Asset and dependency attribution

- **Fish geometry, fins, tail joints, colour masks, plants, rocks, corals, sand and
  caustic textures:** original procedural source in `tank/art.py`, MIT (project
  LICENSE). No SereneScreen artwork, textures, sounds or software was copied.
  All editable source is retained; procedural geometry is built at runtime.
- **Shark, net, water bag, bowl and cage pickup actors:** original procedural
  source in `tank/transition_art.py`, MIT (project LICENSE). Generated native
  models are bundled in `tank/assets/transitions/`; regenerate with
  `python -m tools.build_transition_assets`. No third-party art.
- **Liberation Sans Regular:** unmodified font in `tank/assets/`, SIL Open Font
  License 1.1. Copyright Google Corporation / Red Hat, Inc.; full notices in
  `tank/assets/Liberation-LICENSE.txt`. Source: https://github.com/liberationfonts.
  Copied from the host's Debian fonts-liberation package.
- **Noto Emoji:** unmodified monochrome outline font, SIL Open Font License 1.1,
  Copyright 2013 Google LLC. `tank/assets/NotoEmoji.ttf` is the upstream
  `NotoEmoji[wght].ttf` with only the filename shortened; full license in
  `tank/assets/NotoEmoji-LICENSE.txt`.
  [Pinned Google Fonts source](https://github.com/google/fonts/tree/8b0a1d0f5983c89bc2b93f1b5fb55f9e252744b5/ofl/notoemoji).
  SHA256: `de6c18832938afc99caf132b39d6a30a19bac7f2e812e28db2535b4608d27551`.
- **Panda3D 1.10.16:** BSD licence, https://github.com/panda3d/panda3d.
- **pyserial 3.5:** BSD licence, https://github.com/pyserial/pyserial.
- **Bleak:** MIT licence, https://github.com/hbldh/bleak.
- **SQLite:** public domain (Python standard library sqlite3).

The RX firmware remains in its existing separately licensed MIT repository,
retaining MeshCore and LoRaGotchi authors' notices. No stock aquarium assets
were downloaded. Prototype art is deliberately editable, not final fidelity.
