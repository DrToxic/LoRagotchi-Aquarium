"""Headless check using the installed platform's real Panda/Python bindings.

Run with the Windows Python executable on Windows (or explicitly under Wine).
No window, radio, settings, or live database is opened.
"""
import ctypes
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from panda3d.core import TextAssembler, TextNode

from tank.text import configure_text, display_text


def main():
    primary, _ = configure_text()
    narrow = ctypes.sizeof(ctypes.c_wchar) == 2
    try:
        primary.hasCharacter('\U0001f41f')
    except TypeError:
        assert narrow
        print('REPRODUCED old hasCharacter crash with a supplementary fish code point')
    else:
        assert not narrow, 'Expected the Panda3D 1.10.16 Windows wchar_t limitation'
        print('Wide wchar_t platform: old binding accepts supplementary characters')

    cases = (
        ('\U0001f41f Tank \u2623\ufe0f', '\U0001f41f Tank \u2623'),
        ('\U0001f420\U0001f421\U0001f988\U0001f600', '\U0001f420\U0001f421\U0001f988\U0001f600'),
        ('Cafe\u0301 / \u0420\u044b\u0431\u0430', 'Café / Рыба'),
        ('A\U0010ffffB\U0010fffeC\u4e2d', 'A?B?C?'),
        ('\U0001f41f\u200d\U0001f420', '\U0001f41f\U0001f420'),
    )
    for source, expected in cases:
        rendered = display_text(source)
        node = TextNode('platform-binding-proof')
        node.setText(rendered)
        assert not node.generate().getBounds().isEmpty()
        assembled = TextAssembler(node)
        assembled.setWtext(rendered)
        assert assembled.getPlainWtext() == expected
    print(f'PASS {len(cases)} Unicode cases through real {sys.platform} bindings; '
          f'wchar_t={ctypes.sizeof(ctypes.c_wchar) * 8} bits')


if __name__ == '__main__':
    main()
