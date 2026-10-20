from dataclasses import asdict
import json
import struct

import pytest
from panda3d.core import NodePath, PerspectiveLens

from tank.chat import CHANNEL, ChatBubbles, ChatQueue, MAX_ACTIVE, MAX_PENDING
from tank.client import Client
from tank.demo import RX
from tank.protocol import bridge_command_allowed, channel_info, mesh_message, ProtocolError
from tank.settings import Settings
from tank.simulator import SimulatedRadio
from tank.store import Store


def packet(text="Nickel: Hello reef 🐟", index=3, timestamp=42, version=3, text_type=0):
    header = b"\x11\x04\0\0" if version == 3 else b"\x08"
    return header+bytes([index, 255, text_type])+struct.pack("<I", timestamp)+text.encode()


def event(text="Nickel: Hello reef 🐟", **changes):
    msg = dict(kind="mesh", route="channel 3", channel_index=3, channel_name=CHANNEL,
               timestamp=42, rx=RX, text_type=0, text=text)
    return msg | changes


@pytest.mark.parametrize("version", [2, 3])
def test_wire_channel_header_and_plain_message_type(version):
    decoded = mesh_message(packet(version=version))
    assert decoded["channel_index"] == 3 and decoded["timestamp"] == 42
    assert decoded["text"] == "Nickel: Hello reef 🐟" and decoded["text_type"] == 0
    assert mesh_message(packet(version=version, text_type=2))["text_type"] == 2
    assert mesh_message(packet(version=version)[:6]) is None


def test_channel_metadata_does_not_return_secret():
    reply = b"\x12\x05"+CHANNEL.encode().ljust(32,b"\0")+bytes(range(16))
    assert channel_info(reply) == (5, CHANNEL)
    with pytest.raises(ProtocolError):
        channel_info(reply[:-1])


def test_client_resolves_channel_not_fixed_slot_and_caches_read_only_lookup(tmp_path):
    radio = SimulatedRadio(1, {3: CHANNEL, 7: "#other"}, [
        packet(), packet("Nickel: second", timestamp=43),
        packet("Not the requested channel", index=7)])
    received = []
    with_store = Store(tmp_path/"fish.sqlite")
    client = Client(radio, with_store, received.append, token=1)
    try:
        client.connect()
        assert client.poll()  # Fish keeps its existing save-before-ACK path.
        for _ in range(3):
            client.poll_messages()
        chat = [e for e in received if isinstance(e, dict)]
        assert [e["channel_name"] for e in chat] == [CHANNEL, CHANNEL, "#other"]
        assert all(e["rx"] == RX for e in chat)
        assert radio.commands.count(bytes([31,3])) == 1
        assert bytes([31,7]) in radio.commands
        assert len(with_store.roster()) == 1 and 1 in radio.acked
        queue = ChatQueue()
        assert [queue.accept(e, 0) for e in chat] == [True, True, False]
    finally:
        client.close();with_store.close()


def test_interleaved_message_waits_for_lrx_response_before_channel_query(tmp_path):
    radio = SimulatedRadio(0, {3: CHANNEL})
    store = Store(tmp_path/"fish.sqlite")
    received = []
    client = Client(radio, store, received.append, token=1)
    try:
        client.connect()
        radio.replies.put(packet())
        assert not client.poll()
        assert not received
        client.poll_messages()
        assert received[0]["channel_name"] == CHANNEL
    finally:
        client.close();store.close()


def test_missing_channel_and_small_mtu_do_not_show_unverified_chat(tmp_path):
    radio = SimulatedRadio(0, messages=[packet()])
    store = Store(tmp_path/"fish.sqlite")
    received = []
    client = Client(radio, store, received.append)
    try:
        client.connect();client.poll_messages()
        assert received[0]["channel_name"] == ""
        assert not ChatQueue().accept(received[0], 0)
        radio.supports_mesh_messages = False
        before = len(radio.commands)
        client.poll_messages()
        assert len(radio.commands) == before
    finally:
        client.close();store.close()


@pytest.mark.parametrize("changes", [
    {"route":"direct"}, {"channel_name":"#other"}, {"channel_name":""},
    {"channel_index":None}, {"text_type":1}, {"kind":"snapshot"},
    {"text":"Nickel: LFG1|COMMIT|123|456"}, {"text":"LFG1 REQ 123"},
    {"text":"Nickel:   "}, {"text":""},
])
def test_chat_filters_other_routes_fish_protocol_and_empty_messages(changes):
    assert not ChatQueue().accept(event(**changes), 0)


def test_queue_bounds_dedup_age_and_disabled_messages():
    queue = ChatQueue()
    for n in range(600):
        assert queue.accept(event(text=f"A: {n}", timestamp=n), 0)
    assert len(queue.pending) == MAX_PENDING and len(queue.seen) == 512
    assert not queue.accept(event(text="A: 599", timestamp=599), 0)
    assert queue.pop(121) is None
    queue.enabled = False
    assert not queue.accept(event(text="A: disabled"), 122)
    queue.enabled = True
    assert not queue.accept(event(text="A: disabled"), 123)
    assert queue.accept(event(text="A: Fish are looking good! 🐟", timestamp=44), 123)
    message = queue.pop(123)
    assert message.sender == "A" and message.text == "Fish are looking good! 🐟"


def test_bridge_only_adds_exact_channel_read_command():
    assert bridge_command_allowed(b"\x1f\x03")
    assert bridge_command_allowed(b"\x0a")
    for bad in (b"\x1f", b"\x1f\x03\0", b"\x20\x03"+bytes(48), b"\x03", b""):
        assert not bridge_command_allowed(bad)


def test_bubble_lifetime_bounds_cached_geometry_and_world_motion():
    render = NodePath("render")
    camera = render.attachNewNode("camera")
    camera.setPos(0,-32,12);camera.lookAt(0,0,5.5)
    lens = PerspectiveLens();lens.setFov(60);lens.setAspectRatio(16/9)
    chat = ChatBubbles(render, camera, render)
    chat.set_view(lens)
    for i in range(40):
        chat.accept(event(text="A: Long Unicode message 🐟 ☣️ "+"water "*18, timestamp=i))
    peak = 0
    first = None
    for _ in range(400):
        chat.update(.1)
        peak = max(peak, len(chat.active))
        assert len(chat.active) <= MAX_ACTIVE
        if first is None and chat.active:
            first = chat.active[0]["node"]
            before = first.getZ()
            builds = chat.builds
            chat.update(.1)
            assert first.getZ() > before and chat.builds == builds
        assert chat.root.getNumChildren() == len(chat.active)
    assert peak == MAX_ACTIVE
    chat.set_enabled(False)
    assert not chat.active and not chat.queue.pending and chat.root.getNumChildren() == 0
    chat.destroy()


def test_old_settings_enable_chat_and_toggle_survives_preset(tmp_path):
    path = tmp_path/"settings.json"
    old = asdict(Settings());old.pop("chat_bubbles")
    path.write_text(json.dumps(old))
    settings = Settings.load(path)
    assert settings.chat_bubbles
    settings.chat_bubbles = False
    settings.apply("high");settings.save(path)
    assert not Settings.load(path).chat_bubbles
