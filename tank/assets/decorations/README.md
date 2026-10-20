# Decoration library

Each child folder is one checkbox in **Controls → Decorations**. The bundled
models are original low-poly artwork under the project MIT license. Their
editable generator is `tools/build_decorations.py`; the app loads the saved files
and does not run that generator.

To add an object:

1. Create a uniquely named folder here, e.g. `my-castle/`.
2. Put a static Panda3D `.egg` or `.bam` model in it. EGG is editable text; export
   or convert your model with Panda3D tooling. Other formats need conversion;
   there is no automatic download or glTF/OBJ plugin.
3. Add `decoration.json` as below.
4. Press **Refresh library** in the Decorations tab and enable its checkbox.
   Invalid entries show an error; they do not prevent the other objects loading.

```json
{
  "name": "My castle",
  "description": "A small castle with an open gateway.",
  "model": "model.egg",
  "position": [0, 3, 0.05],
  "hpr": [0, 0, 0],
  "scale": 1.0,
  "enabled": false,
  "solids": [
    {"center": [-2, 0, 2], "size": [1, 2, 4]},
    {"center": [2, 0, 2], "size": [1, 2, 4]},
    {"center": [0, 0, 4], "size": [5, 2, 0.5]}
  ]
}
```

- Coordinates are **Z-up**, X left/right, Y front/back. Sand is roughly Z=0.
  Water spans X=-22..22, Y=-7..8, Z=0.25..16; visibility depends on the panorama.
- Position and `hpr` (heading, pitch, roll in degrees) place the entire model.
  Uniform `scale` applies to the model and its collision boxes.
- `solids` are full-size boxes in **model-local** coordinates, with optional
  local `hpr`. Use separate boxes for pillars, planks and walls, leaving openings
  empty. A whole-object box would block the very doorway you want fish to use.
  With `solids: []`, the decoration is visual only and fish can pass through it.
  Art and collision proxies must agree; leave generous clearance for adult fish.
- Checkbox changes persist in the user's `settings.json` independently of
  graphics presets. The folder name is the persistent ID. `enabled` only sets
  the default for an object the user has not toggled.
- Keep assets self-contained and use only models you trust. The loader does not
  execute Python plugins. A model path may not escape its decoration folder.
- The built-in ship has a broad passage through its broken middle, across Y at
  local X=-2, Z≈2.7. Its mast and end decks remain solid.
- Keep your custom folders when extracting a newer source ZIP. Fresh installs
  contain the bundled set, not copies of your local additions.

Sand shelves are automatic shared-world scenery for vertically stacked views;
they are not individual checkbox decorations. Their centre gap and foreground
remain open between upper and lower water.
