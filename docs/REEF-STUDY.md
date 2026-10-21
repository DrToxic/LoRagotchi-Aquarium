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
- At most eight small seagrass groups sway. Static pieces are batched through
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
receiver, expiry, themes, settings schemas, desktop-layout or transfer code.

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

## Acceptance and next integration

This is a reviewable visual/technical study, **not** a claim that software-GL
results predict Windows/GPU or the owner's HAOS host. See the accompanying
report for measured values, exact source commit and final-package test evidence.

Before making this a normal setting: review the composition in motion on target
hardware, choose the scene selector/default policy, wire it into both products,
retain Classic, regenerate the HA context, and run the HA container/browser and
actual upgrade checks. Keep appearance and performance independent. Nothing in
this study proves that an engine migration is necessary.
