# Local Storage

In a source checkout, Aquarium's automatic persistent state is stored under
`<Aquarium>/.local/`. It does not use Windows application-data directories or
the XDG config/data directories for these defaults. The directory is ignored by
Git.

| File or directory | Purpose |
| --- | --- |
| `settings.json` | Aquarium, appearance, nursery, and performance preferences. |
| `live.sqlite` | Received live fish, event history, and bounded radio history. Created when live storage is opened. |
| `display-layout.json` | Saved window layout and positions. |
| `rx-connection.json` | Saved serial, BLE, or bridge connection profile; stores a token path, never token bytes. |
| `aquarium-game.json` | Saved local copy/paste game state. |
| `nursery-local.sqlite3` | Local/demo and live nursery state. |
| `nursery-replay.sqlite3` | Replay-mode nursery state. |
| `themes/*.json` | Custom themes saved in the theme library. |

Demo and replay fish data use an in-memory database unless `--database` is
provided. The theme import/export field defaults to `.local/my-theme.json`;
imports and exports use the path shown in that field. Screenshots use the path
provided to `--screenshot`. The RX bridge creates its secret only at the path
provided by `--token-file` (the documented example is `.local/rx.token`). These
explicitly selected paths can point outside `.local`.

`--settings` and `--database` remain available for explicit alternate paths.
Files previously created in home-directory config/data locations are not moved
or deleted automatically; they remain untouched when the new local defaults are
used. The project virtual environment is `.venv/`; package-download caches are
managed separately by `uv`, not by the Aquarium application.

Atomic saves may briefly create sibling `.tmp` files or `.theme-*` files. A
settings or display-layout migration can preserve its original bytes in a
`.pre-migration*.bak` sibling. SQLite can create `-wal`, `-shm`, or journal
sidecars beside its databases; these are also under `.local/`. Legacy
`nursery-demo.sqlite3` and `nursery-live.sqlite3` databases may remain there
after their contents are migrated into `nursery-local.sqlite3`.

The standalone renderer does not configure a log file; Panda3D output goes to
the process output streams.