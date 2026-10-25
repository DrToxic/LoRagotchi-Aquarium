# Promoted to the default scene

Tidal Garden is now the default (standalone 0.8.0 / HA preview 9). Classic remains selectable. The study notes below are historical measurements, not current opt-in requirements.

# Tidal Garden — original reef scene study

**Local prototype on top of v0.7.0, not a new release or HA option.**
The normal `loragotchi-tank` entry point and Classic scenery are unchanged.

## Try it

From the extracted source folder, with Python 3.10+ and `uv`:

```sh
uv sync --extra test
uv run python -m tools.reef_study --interactive
```

Without uv, use a virtual environment, `python -m pip install .`, then
`python -m tools.reef_study --interactive` from this folder. A real native desktop
is required for interactive use; this is not a webpage.

Use `--quality low` or `--quality compatibility` to examine the simplified art.
`--scene classic` opens the comparison scene instead. Both launch with twelve
synthetic fish, an in-memory demo store and temporary settings under `.local/`;
no real saved collection or preferences are loaded. The ordinary native controls
are retained for inspecting appearance/windows. Do not select a live connection
in this art study. Nothing is installed into HA.

## Vegetation update (study 2)

Classic is retained, including its original scenery and lower measured rendering
cost. The study now restores the full configured plant count: 8 / 16 / 32 / 48 /
72 tufts for Compatibility / Low / Balanced / High / Ultra. Interactive launch
offers the first four; Ultra remains available in the native graphics controls.
The earlier study capped all presets at eight sparse tufts.

Seagrass now has five curved, folded blades per tuft, shaded roots, brighter
centre ridges and seeded colour/height variation. Taller eelgrass behind the
inner reef and shorter foreground patches frame the open central swimming lane.
Each tuft is a single opaque geometry batch and a single animated transform;
no textures, shaders, transparency layers or per-frame mesh allocations are added.

- **Aquarium → Appearance & advanced graphics → Quality → Plant count** controls
  density (0–100; zero removes all grass). Choose **Apply & save**.
- **Appearance → Light → Plant sway / Sway speed** controls the existing motion.
  Zero sway leaves the grass still.
- **Decorations → Reef / Plants** now lists every study placement with readable
  names and working Auto/Pinned controls. These are placement controls, not new
  library assets or per-object visibility switches. The **Library** tab is unchanged.

The category bug was a Classic-only prefix filter: study objects retained their
own stable IDs but were omitted from both lists. Those IDs remain unchanged.
As before, this demo's settings are temporary and are discarded on exit.

## Art direction

An asymmetric, calm **Tidal Garden**: a taller weathered limestone outcrop on the
left, a lower foliose-coral garden on the right, and a broad open swimming lane.
Cool, quiet silhouettes sit behind the reef; warm plate rims, purple sponges,
branching sea fans and small foreground colonies provide scale and contrast.

This is original editable mathematical artwork. No SereneScreen or stock art,
models, screenshots, generated raster assets or external downloads are used.
The earlier reference informs mood only, not asset layout or exact forms.

- Coherent rock deformation avoids the noisy seams of independently jittered
  vertices. Vertex colours supply mineral strata and underside shading.
- Scalloped plate coral has top, bottom and edge geometry.
- Sponges have recessed open mouths and dark inner walls.
- One shared 128×128 RGB surface texture, generated locally, supplies subtle
  grain. Existing sand and caustics are reused; there are no texture downloads.
- The large composition survives every quality tier. Detail controls subdivision
  and fan branch count, rather than removing focal structures.
- The configured number of seagrass tufts sway. Static pieces are batched through
  the existing placement system; no per-frame mesh rebuild, real-time shadows,
  new engine, postprocessing chain or runtime dependency.
- Fish retain the existing received colours, stage, meshes, motion and identity.
  Fish-animation redesign is deliberately not bundled into the art study.

## Implementation and existing-solutions preflight

`tank/reef_art.py` is an opt-in scenery provider matching the existing
`art.scenery` interface. `tools/reef_study.py` selects it **only in that process**.
The normal app is not wired to it. Existing Panda3D meshes, texture loading,
lighting, Bullet hulls, layout placement and static batching cover this work;
no asset marketplace, extra engine or paid service is needed.

[Panda3D's batching guidance](https://docs.panda3d.org/1.10/python/optimization/performance-issues/too-many-meshes)
confirms the distinction between scene-graph Geom counts and actual rendered
batches. The report intentionally labels the former accurately.

Ten main rocks, eight plates and six sponge groups have convex proxies generated
from their authored vertices. The sponge openings are decorative and too small
for adult fish; proxies conservatively close them. Fine fans, seagrass and tiny
polyps are flexible/non-solid, like the existing plants. No implied swim-through
cave is enclosed by a single invisible hull. Distant silhouettes sit beyond the
normal fish volume and have no rigid proxy.

Every object uses the production full-footprint placement path; masks remove or
relocate scenery and its proxies together. This study does not modify radio,
receiver, expiry, themes, settings schemas, layout solving or transfer code.

## Reproduce the native probe

On Linux with Xvfb (no xauth needed):

```sh
uv run python tools/run_native.py tools.reef_study --quality balanced --samples 60 --output .local/reef-balanced
uv run python tools/run_native.py tools.reef_study --quality low --samples 60 --output .local/reef-low
uv run python tools/run_native.py tools.reef_study --quality compatibility --samples 60 --output .local/reef-compatibility
uv run pytest -q
```

The comparison is **Classic / Reef / Classic / Reef** at the same 1280×720
internal and output resolution, twelve identical frozen fish poses, fixed light,
quality, labels off, disabled library decorations, no VSync or frame cap, warmup,
and explicit render completion. Sway/caustics are frozen during timing. The
measurement covers update plus synchronous full render, not GPU-only time.

The probe records median/p95 frame time, update time, current process RSS,
scene/scenery Geoms, vertices and triangles, animated plant count and placements.
RSS is an alternating-process snapshot, **not** isolated GPU memory or a proven
incremental allocation. Geoms are all scene-graph batches including hidden or
out-of-view ones, **not actual driver draw calls**. Intersecting surfaces in either scene may have a few depth-tie pixels after
batching; their measured count and mean RGB error are retained, with a strict
0.01% pixel / 0.00001 mean-error ceiling, not called pixel-identical. The ordinary Classic application source is
byte-unchanged; this repeat check rebuilds and re-batches geometry.

Separate checks cover night lighting, six seconds of live simulation, 24 solid
proxy groups, full-footprint masks and restoration, 256 fish, finite poses and
rebuilds without extra collision bodies. Dense simulation is not an FPS claim.
Study 2 also checks visible grass motion with frozen fish/caustics, pixel-identical
sway-off frames, stable geometry/node counts, both native category lists and
pin/refresh round-trips, plus zero-plant removal and count restoration.

## Historical acceptance and integration

The scene/default decision was completed: Tidal Garden shipped as the default in
standalone 0.8.0 / HA preview 9, with Classic retained. Use [Scenery](SCENERY.md)
for current controls. The study measurements above remain historical evidence,
not outstanding approval requests or predictions of target-hardware performance.
