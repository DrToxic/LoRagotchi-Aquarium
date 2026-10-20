from dataclasses import replace

from panda3d.core import NodePath, TextNode, TextAssembler

from tank.demo import RX, visitors
from tank.protocol import decode_event, encode_event
from tank.store import Store
from tank.text import EMOJI_STYLE, configure_text, display_text
from tank.views import NameLabels


def test_reported_glyphs_use_bundled_fallback_without_missing_definitions(capfd):
    primary, emoji = configure_text()
    for character in '🐟🐠🐡🦈☣😀':
        assert not primary.hasCharacter(character)
        assert emoji.hasCharacter(character)
    source = '🐟 Tank ☣️ / 🐠🐡🦈😀'
    rendered = display_text(source)
    assert EMOJI_STYLE in rendered and '\ufe0f' not in rendered
    node = TextNode('emoji-proof')
    node.setText(rendered)
    assert not node.generate().getBounds().isEmpty()
    assembled = TextAssembler(node)
    assembled.setWtext(rendered)
    assert assembled.getPlainWtext() == source.replace('\ufe0f', '')
    assert 'No definition' not in capfd.readouterr().err


def test_display_fallback_handles_unknowns_controls_and_combining_text(capfd):
    assert display_text('Cafe\u0301 · Ελληνικά · Рыба') == 'Café · Ελληνικά · Рыба'
    assert display_text('A中B\U0010ffffC') == 'A?B?C'
    assert display_text('A\1B\2C\5D\0E\tF\nG') == 'ABCDE F\nG'
    assert display_text('☣\ufe0e') == display_text('☣\ufe0f') == display_text('☣')
    assert display_text('🐟\u200d🐠') == display_text('🐟🐠')
    node = TextNode('unknown-proof')
    node.setText(display_text('Hello 中 \U0001fae9 ☣️'))
    node.generate()
    assert 'No definition' not in capfd.readouterr().err


def test_unicode_roundtrip_store_and_label_cache_preserve_raw_names(tmp_path, capfd):
    raw = '🐟 ☣️ Café'
    fish = [replace(f, name=raw) for f in visitors(2)]
    store = Store(tmp_path / 'unicode.sqlite')
    for item in fish:
        decoded = decode_event(RX, encode_event(item))
        assert decoded.name == raw
        store.save(decoded)
    store.close()
    store = Store(tmp_path / 'unicode.sqlite')
    roster = store.roster()
    assert len(roster) == 2 and all(f.name == raw for f in roster)
    labels = NameLabels(NodePath('root'))
    labels.sync(roster)
    assert labels.builds == 1 and labels.root.getNumChildren() == 2
    assert len({node for node, name in labels.labels.values()}) == 2
    labels.sync(roster)
    assert labels.builds == 1
    renamed = replace(roster[0], name='🦈 Updated')
    labels.sync([renamed, roster[1]])
    assert labels.builds == 2 and labels.labels[renamed.owner][1] == renamed.name
    labels.sync([])
    assert not labels.geometry and not labels.labels
    labels.destroy()
    store.close()
    assert 'No definition' not in capfd.readouterr().err
