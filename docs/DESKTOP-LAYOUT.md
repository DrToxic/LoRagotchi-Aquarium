# Desktop layout and fish travel — v0.5.0

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

## Fish transfers

Open **Animations → Travel between disconnected areas**. Transfers default **Off**
on both new installations and upgrades. **Occasional** attempts a journey every
60–120 seconds; **Frequent** every 20–40 seconds. Attempts can be skipped: at most
one voluntary journey runs at a time, each fish has a five-minute cooldown, and
both source and destination need clear routes before departure. A status explains
why transfers are unavailable. Turning transfers off lets an active trip finish;
turning fish animations off stops it and restores a safe ordinary placement.

The aquarium stays one physical-desktop panorama. Touching/overlapping windows
are connected, corner-only contact is not a passage, and a U-shaped arrangement
can still be connected around a gap. A mask can split one window. Conservative
curved-mask analysis may decline a transfer if separation cannot be proved.
Ordinary swimming never crosses excluded areas.

The full fish outline must leave the source image before its existing model and
swimmer relocate to the destination entry. There is no whole-fish fade, saved
visit renewal or synthetic radio event. The fish swims out/in; existing pickup
actors still handle normal lifecycle updates/removals. Carrier travel is deferred
until the complete carrier/boarding choreography has region-local routes.

Portals are exposed output edges and sufficiently large **opaque rectangular**
blackouts. Non-blackout masks, curved blackouts and inverted-mask boundaries are
not portals in this pass, though all still affect connectivity and avoidance.
A fish may use another clear output edge instead. Whole swept outlines are checked
against every output and all scenery/fish bodies; conservative temporary corridor
solids keep other swimmers from occupying a reserved route. Very narrow strips,
crowded tanks, shelves or large fish can make a route unavailable. No forced trip.

Valid journeys survive unrelated layout edits and graphics rebuilds. An invalidated
route stops at a valid visible pose, retreats if possible, or parks if an edit has
removed its visible water. Closing all outputs retains the fish; opening usable
water lets it re-enter through a safe route. This is emergency layout recovery,
not a scheduled transfer. Removing a fish cancels re-entry. Real updates during
departure coalesce while hidden; updates during entry retain old-out/new-in order.

Connectivity is cached by layout revision. Route attempts inspect at most four
eligible fish and bounded landing candidates, not every fish on every frame.
Travel preferences belong to the display profile, not exportable appearance themes.

## Persistence and scope

`display-layout.json` now uses version 2. Existing version-1 rectangles/masks are
retained; the first save preserves the original as `display-layout.v1.json`.
Reading alone does not rewrite the profile. Invalid new placement metadata is
discarded independently rather than erasing valid old window geometry.

No changes to saved fish, radio behavior, firmware, HA or fish expiry.
