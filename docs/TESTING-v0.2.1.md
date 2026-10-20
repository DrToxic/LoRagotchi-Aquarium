# v0.2.1 · Radio scroll clipping

## Reproduction and fix

The v0.2.0 chat transcript used one mutable DirectLabel. Changing its text
updated the glyph geometry but left the original one-line PGItem frame in
place. Once that stale frame scrolled out of view, Panda3D culled the entire
label rather than clipping its visible lines. The Tools activity log used the
same pattern. The point at which it vanished depended on history length.

Both panes now refresh the label frame after changing text and measure the
rendered bounds to size the scroll canvas. This also removes blank overscroll
caused by estimated line heights and resets the range for short/empty histories.
The existing Panda3D scrolling/clipping implementation is retained; no added
dependency, database migration, firmware change or radio behavior change.

## Regression checks

Run `uv run python -m tools.run_native tools.radio_scroll_smoke` on Linux with
Xvfb installed. Synthetic data only; it opens no radio or live database.

- Checks native screenshot pixels at 101 scroll positions in each of five
  cases: short channel history, a full 60-message page, an earlier page,
  scaled-window DM history and a full Tools activity log.
- Covers Unicode/emoji, long wrapped messages, scrolling to the last line,
  actual clipping above/below the viewport, and empty/short content resets.
- Stores screenshots and pixel counts under `.local/radio-scroll/`.
- The original code fails with zero visible message pixels after scrolling;
  checking only stored text or widget text would have missed this bug.

The source-package handoff also runs the existing unit suite and native Radio
workflow from an isolated install of the exact ZIP. The existing Radio workflow
covers the shared transport, fish intake, chat sending/delivery, contacts,
channels, device tools and disconnect behavior using a controlled local peer.

## Owner retest

Extract v0.2.1 into a new folder and run with the usual installation/start
commands. Existing user settings and stored histories need no reset. On Windows,
slowly scroll a populated Radio → Chat conversation through the entire range,
including around two-thirds down; messages should clip line by line. Check
Older messages, Latest, switching conversations and the Tools log.

Linux/Xvfb/Mesa native pixels do not establish physical Windows/GPU acceptance.
No push, release, firmware flash or live-radio operation is part of this fix.
