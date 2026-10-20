# Fish pickup actors

Original MIT-licensed, local Panda3D models: `shark.bam`, `net.bam`, `bag.bam`,
`bowl.bam`, `cage.bam`. No downloaded art, textures, scripts or asset service.
Their editable source is `tank/transition_art.py`; regenerate with:

```sh
uv run python -m tools.build_transition_assets
```

These are temporary animated actors, separate from the static seabed decoration
library. Choose which pickups participate in the random selection in **Animations**.
Each uses world coordinates and is rendered once across the panoramic wall.
Model changes must retain the shark's `tail` and `jaw` joints.
