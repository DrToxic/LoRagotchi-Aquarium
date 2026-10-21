# Desktop layout-aware scenery — v0.4.0

## Automatic placement

In **Decorations**, keep **Keep scenery out of deadzones: on**. This applies to
procedural rocks/coral/plants/pebbles and enabled library objects, independently
of a mask's Blackout option. The seabed and water remain continuous: a deadzone
with Blackout off can show empty sand/water. Normal window-edge cropping is
allowed; the aquarium is still one shared physical-desktop panorama.

When masks, windows or shelf supports change, affected unpinned objects try
nearby supported positions, then other candidate floor/shelf patches. Searches
are bounded. Full projected visual envelopes are checked, including plant sway;
collision checks use the original solid parts, not a box filling a ship's hole.
Small objects can use shelves when they fit. Objects are not silently rescaled.

Valid objects do not reshuffle when an unrelated mask changes. **Auto / Pinned**
is available in the Library, Reef and Plants lists. Pinned holds the current
position; it does not permit overlap with a deadzone. A conflict temporarily hides
that object and its solids, with a visible reason. Removing the conflict restores
it. An object's saved enabled checkbox is never silently cleared.

**Reset auto positions** reconsiders unpinned objects from their authored anchors.
It does not change pins. Refresh library reloads models/manifests while retaining
valid remembered positions. During client-area window dragging/resizing, invalid
scenery and bubbles withdraw immediately; expensive relocation waits for release.

Positions are hints, not unconditional overrides: saved positions are revalidated
against the current projection, masks, assets and supports. Use **Save layout**
after arranging windows to retain the window geometry and placement hints.

## Edge shelves

Select a zone in **Deadzones** and set **Edge shelf: auto**. For a new zone,
press **Apply**. The result/reason appears below the controls.

- Enabled, non-inverted Rectangle or Rounded rectangle zones are supported.
- The zone must intersect an exposed aquarium client edge. A covered seam between
  adjoining windows is not an exposed edge.
- A flat upper edge needs enough visible water for the entire ledge and foliage.
  Short/blocked edges are omitted; elliptical/inverted masks report why a shelf
  cannot be generated. All existing shapes still exclude scenery normally.
- The shelf is entirely on the water side. It has matching collision geometry
  and a real usable sand cap. Overlapping supports do not duplicate ledges.
- Existing stacked-window shelves retain their centre and foreground swim routes.

These are manual layout zones, not automatic tracking of other desktop apps.
There is no OS transparency, click-through overlay or monitor/app detection.

## Bubble columns

Use **Aquarium → Appearance → Bubbles** and choose shelves or mixed placement.
Edge and stacked shelves expose stable surface identities; an unrelated shelf
edit does not reroll valid column anchors. The count/particle budget is unchanged.
Columns stop at the first excluded window/mask boundary instead of reappearing
in a disconnected area above. The status reports placed/requested columns when
not all requested emitters fit. Ambient bubbles remain the separate legacy effect.

## Persistence and scope

`display-layout.json` now uses version 2. Existing version-1 rectangles/masks are
retained; the first save preserves the original as `display-layout.v1.json`.
Reading alone does not rewrite the profile. Invalid new placement metadata is
discarded independently rather than erasing valid old window geometry.

No changes to saved fish, radio behavior, firmware, HA or fish expiry. Animated
transfers between disconnected areas remain a later feature; ordinary fish still
stay within their valid visible swimming area.
