# Native controls and save scopes

The operator is a separate, resizable native Panda3D window, initially 1100×800.
It does not replace the aquarium output or introduce a browser UI. At 800×600,
forms and actions remain reachable by scrolling instead of shrinking all text.
Still smaller widths expose a horizontal scrollbar; sidebar sections remain
fixed. Tab traverses entry fields and reveals clipped fields. Aquarium shortcuts
are suppressed while a native entry actually has keyboard focus. Unicode display
fallbacks and the existing clipboard routes are retained.

## Feature map

- **Overview**: actual demo/replay/live mode, collection count and connection
  status; selected fish snapshot/portrait, Next fish, names and channel-chat
  visibility; separate Remove copy and confirmed End display session. Click a
  fish in an aquarium window to select it; there is no invented selection tool.
- **Appearance**: Theme & fish, Lighting & cycle, Water & bubbles; theme library
  import/export, custom names/IDs and Save current look remain reachable.
- **Scenery & motion**: all Reef/Plants/object checkboxes and Auto/Pinned options,
  arrival/departure styles; desktop-only area travel where supported.
- **Fish & nursery**: nursery settings, parents/pairing and local eggs; copy
  lifespan and retained-expiry summaries.
- **Windows & layout**: add/close/fullscreen, geometry Save layout, edge protection,
  all deadzone shapes/coordinates, blackout, inversion, outlines and edge shelves.
- **Radio & chat**: Connection, Chat, Contacts, Channels, Device and Tools.
  Advanced writes remain disabled while disconnected and retain confirmations.
- **Games**: all three existing manual direct-chat games, saved state and packet
  clipboard flow. Nothing is sent automatically.
- **Performance**: presets, render scale, output/internal dimensions, advanced
  budgets and VSync restart notice; no numeric performance clutter on Overview.

## Appearance drafts

Changing sidebar sections or appearance tabs never discards pending edits.
**Apply & save** validates and saves appearance changes across all three tabs,
including the chosen colour theme, fish mesh style and independent scenery style.
It does not save radio, game, nursery, lifespan, window or deadzone edits.

**Reset edits** asks for confirmation, with Cancel, then reloads the currently
applied settings without saving anything. Closing the operator with pending edits
also offers Keep editing or Discard & quit. Theme library **Draft Classic
appearance defaults** retains the old reset capability as a draft: it restores
appearance defaults only, not quality, scenery style, fish style or collection.
Apply & save is still required. There is no silent Classic reset.

The preview is a small readback of the real applied scene, refreshed at most once
per second only while Appearance is visible. Independent native GL contexts do
not share a render texture. No new render target/camera is allocated for this
preview. Day/Night/Current alter only the temporary applied-scene time preview;
they never apply or save drafts. Aquarium windows continue to show the live scene.

## Deliberately separate saves

Theme library Load theme and Apply fish style keep their immediate save behavior;
Save current look captures the applied look, not unsaved appearance edits. Untouched
editor fields rebase after another controller saves, while edited fields remain
pending. Applying a draft merges only edited fields into current settings, so it
cannot roll back unrelated immediate saves. If the same field is edited in both
places, the explicit later draft Apply intentionally wins for that field.

Performance presets save immediately; render scale has its own Apply scale.
Advanced quality has **Apply quality & save**, affecting only edited quality
fields; pending appearance edits remain. Appearance Apply does not apply quality.
The draft indicator counts both scopes. Reset edits discards both scopes after
confirmation. VSync still needs restart.

Other controllers keep their existing immediate switches and explicit saves:
Save nursery settings, Apply lifespan, Save layout, deadzone Apply, radio writes
and game packets are not folded into appearance. End display session still needs
a second click; Remove copy affects only the selected display copy, not its pet.

## Home Assistant

Managed HA remains one display-only native window with settings in Configuration.
There is no new managed operator or input route. The optional standalone/source
operator shares this redesign while retaining HA-specific connection and hosted
layout restrictions. Desktop-only travel is not added to HA. This update does not
change receiver, persistence, games, genetics, juvenile visuals or live RF behavior.

## Verification scope

Focused headless tests cover navigation inventory, draft validation, independent
save scopes, external-save rebasing and reset/cancel. The native controls smoke
uses actual XTest pointer and keyboard input with synthetic fish, no live radio or
HA server. It captures normal/smaller layouts, scrolling/focus, selected-fish data,
preview, page reachability and retained render targets. Existing native lifecycle,
projection, appearance, Unicode and HA-managed regression suites remain applicable.
Linux Xvfb/llvmpipe checks are not physical Windows/mixed-DPI, GPU performance or
actual HAOS upgrade acceptance.
