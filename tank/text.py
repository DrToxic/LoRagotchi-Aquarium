"""Display-only font fallback; never alter radio names or stored snapshots.

Use Panda's native embedded font properties, not per-frame text rebuilding.
Monochrome emoji are deliberate; this is not a colour/ZWJ emoji shaping engine.
"""
from functools import lru_cache
from pathlib import Path
import unicodedata

from panda3d.core import DynamicTextFont, Filename, TextNode, TextProperties, TextPropertiesManager


EMOJI_STYLE = 'tank-emoji'


@lru_cache(maxsize=1)
def entry_font():
    """PGEntry uses one face: merged OFL outlines keep editable UTF-8 raw."""
    path=Path(__file__).resolve().parent/'assets/AquariumEntry-Regular.ttf'
    font=DynamicTextFont(Filename.fromOsSpecific(str(path)))
    if not font.isValid():raise RuntimeError('Could not load the bundled input font.')
    return font


@lru_cache(maxsize=1)
def configure_text():
    """Load bundled outline fonts once, on the render thread (also headless)."""
    assets = Path(__file__).resolve().parent / 'assets'
    probes = []
    for name in ('LiberationSans-Regular.ttf', 'NotoEmoji.ttf'):
        font = DynamicTextFont(Filename.fromOsSpecific(str(assets / name)))
        if not font.isValid():
            raise RuntimeError(f'Could not load bundled font: {name}')
        probe = TextNode('font-coverage')
        probe.setFont(font)
        probes.append(probe)
    TextNode.setDefaultFont(probes[0].getFont())
    properties = TextProperties()
    properties.setFont(probes[1].getFont())
    TextPropertiesManager.getGlobalPtr().setProperties(EMOJI_STYLE, properties)
    return tuple(probes)


@lru_cache(maxsize=4096)
def _glyph(character):
    primary, emoji = configure_text()
    if _has_character(primary, character):
        return character, False
    if _has_character(emoji, character):
        return character, True
    return '?', False


def _has_character(probe, character):
    code = ord(character)
    if code <= 0xFFFF:
        # Keep Panda's synthesized accents for BMP text. This binding takes
        # wchar_t, which is only 16 bits on Windows; never pass it an emoji.
        return probe.hasCharacter(character)
    font = probe.getFont()
    # getGlyph takes an int on every platform. A missing character can still
    # return a non-null replacement, so compare against a known missing glyph.
    # U+10FFFF is an unmapped noncharacter in both bundled fonts. Compare glyph
    # objects, not getCharacter(): aliases can share a cached glyph whose
    # character field belongs to the first code point requested.
    missing = font.getGlyph(0x10FFFF)
    glyph = font.getGlyph(code)
    return glyph is not None and glyph != missing


@lru_cache(maxsize=1024)
def display_text(value):
    """Make a safe, supported Panda text string without modifying the original.

    Ignore presentation selectors/joiners, and show unsupported glyphs as '?'.
    Strip control characters so external names cannot inject Panda formatting.
    Cache both coverage and formatted strings; callers still cache geometry.
    """
    configure_text()
    output = []
    in_emoji = False
    for character in unicodedata.normalize('NFC', value):
        code = ord(character)
        if 0xFE00 <= code <= 0xFE0F or 0xE0100 <= code <= 0xE01EF:
            continue
        if character == '\t':
            character = ' '
        elif character != '\n' and unicodedata.category(character) in ('Cc', 'Cf', 'Cs'):
            continue
        glyph, use_emoji = ('\n', False) if character == '\n' else _glyph(character)
        if use_emoji != in_emoji:
            output.append(f'\1{EMOJI_STYLE}\1' if use_emoji else '\2')
            in_emoji = use_emoji
        output.append(glyph)
    if in_emoji:
        output.append('\2')
    return ''.join(output)
