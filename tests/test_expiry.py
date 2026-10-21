from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace
import json
import queue
import time
import pytest
from tank.demo import visitors
from tank.expiry import display_state, timestamp, validate_hours
from tank.protocol import ReturnStatus, ProtocolError
from tank.settings import Settings
from tank.store import Store
from tank.service import Service


def test_expiry_boundary_restart_and_non_destructive_policy_changes(tmp_path):
    clock = [1700000000.0]
    path = tmp_path/'copies.sqlite'
    store = Store(path, clock=lambda: clock[0])
    first, second = list(visitors(2))
    store.save(first); store.save(second); store.remove(second.owner)
    assert store.roster(1, clock[0]+3599.999) == [first]
    assert not store.roster(1, clock[0]+3600)
    store.close()
    clock[0] += 7200
    store = Store(path, clock=lambda: clock[0])
    assert not store.roster(1)
    assert store.display_state(1)['lifespan']['expired'] == 1
    assert store.roster(3) == store.roster(0) == [first]
    assert store.db.execute('SELECT count(*) FROM fish').fetchone()[0] == 2
    assert store.db.execute('SELECT count(*) FROM events').fetchone()[0] == 2
    # End-session hide includes expired rows, so disabling cannot resurrect them.
    store.end_session(); assert not store.roster(0)
    store.close()


def test_only_new_share_renews_even_if_appearance_unchanged(tmp_path):
    clock = [1700000000.0]
    store = Store(tmp_path/'copies.sqlite', clock=lambda: clock[0])
    first = next(visitors())
    assert store.save(first)
    original = store.collection()[0][1]
    clock[0] += 7200
    assert not store.save(first)  # Same RX event, including restart/replay.
    store.save(ReturnStatus(first.rx, 100, first.event_id, 'delivery-confirmed', 1))
    assert store.collection()[0][1] == original and not store.roster(1)
    with pytest.raises(ProtocolError): store.save(replace(first, name='conflicting packet'))
    fresh = replace(first, event_id=101, tx_id=first.tx_id+1)
    assert store.save(fresh) and store.roster(1) == [fresh]
    assert store.collection()[0][1] == clock[0]
    clock[0] += 7200
    assert not store.save(replace(first, event_id=99))  # Unseen but older RX replay.
    assert store.collection()[0][1] != clock[0] and not store.roster(1)
    store.close()


def test_failed_commit_cannot_renew_or_create_partial_event(tmp_path):
    clock = [1700000000.0]
    store = Store(tmp_path/'copies.sqlite', clock=lambda: clock[0])
    fish = next(visitors()); store.save(fish)
    original = store.collection()
    store.db.execute("CREATE TRIGGER fail_refresh BEFORE UPDATE ON fish BEGIN SELECT RAISE(ABORT,'disk fault'); END")
    clock[0] += 7200
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError): store.save(replace(fish,event_id=101,tx_id=99))
    assert store.collection() == original
    assert store.db.execute('SELECT count(*) FROM events').fetchone()[0] == 1
    store.close()


def test_legacy_utc_dates_and_unknown_dates_do_not_reset_age(tmp_path):
    store = Store(tmp_path/'legacy.sqlite')
    one, two = list(visitors(2)); store.save(one); store.save(two)
    with store.db:
        store.db.execute("UPDATE fish SET updated='2020-01-02 03:04:05' WHERE owner=?", (one.owner,))
        store.db.execute("UPDATE fish SET updated='damaged' WHERE owner=?", (two.owner,))
    now = datetime(2020,1,2,4,4,5,tzinfo=timezone.utc).timestamp()
    assert store.roster(1, now) == [two]
    assert store.display_state(1, now)['lifespan']['undated'] == 1
    assert timestamp('2020-01-02T05:04:05+02:00') == now-3600
    assert timestamp('2020-01-02T03:04:05Z') == now-3600
    assert store.db.execute('SELECT updated FROM fish WHERE owner=?',(one.owner,)).fetchone()[0] == '2020-01-02 03:04:05'
    store.close()


@pytest.mark.parametrize('value', [-1, 8761, float('inf'), float('nan'), True, '24', None])
def test_invalid_lifespan_rejected(value):
    with pytest.raises(ValueError): validate_hours(value)


def test_settings_migration_and_preset_independence(tmp_path):
    path = tmp_path/'settings.json'
    path.write_text(json.dumps(dict(fish_animations=False, future_field='preserve')))
    settings = Settings.load(path); assert settings.fish_lifespan_hours == 0
    settings.fish_lifespan_hours = 168; settings.apply('low'); settings.save(path)
    assert Settings.load(path).fish_lifespan_hours == 168
    assert json.loads(path.read_text())['future_field'] == 'preserve'
    path.write_text('{"fish_lifespan_hours":-1}')
    settings = Settings.load(path)
    assert settings.fish_lifespan_hours == 0 and settings.load_warnings


def wait_roster(service, predicate):
    end = time.monotonic()+5
    while time.monotonic() < end:
        try: event = service.events.get(timeout=.1)
        except queue.Empty: continue
        if event.get('kind') == 'roster' and predicate(event): return event
    raise AssertionError('Roster update not delivered')


def test_disconnected_worker_expires_without_packets_and_policy_restores(tmp_path):
    path = tmp_path/'live.sqlite'
    store = Store(path); fish = next(visitors()); store.save(fish); store.close()
    args = SimpleNamespace(database=path, session='community', demo=None, replay=None,
                           connect=None, settings=tmp_path/'settings.json', fish_lifespan_hours=.0004)
    service = Service(args)
    try:
        wait_roster(service, lambda e: e['fish'] == [fish])
        gone = wait_roster(service, lambda e: not e['fish'])
        assert gone['lifespan']['expired'] == 1
        service.commands.put(('lifespan', 0))
        wait_roster(service, lambda e: e['fish'] == [fish])
        service.commands.put(('remove', fish.owner))
        wait_roster(service, lambda e: not e['fish'])
        service.commands.put(('lifespan', 1))
        hidden = wait_roster(service, lambda e: e['lifespan']['hours'] == 1)
        assert not hidden['fish'] and hidden['lifespan']['expired'] == 0
    finally: service.close()
    store = Store(path)
    assert store.db.execute('SELECT count(*) FROM fish').fetchone()[0] == 1
    store.close()


def test_render_only_operations_cannot_renew_persisted_time(tmp_path):
    store = Store(tmp_path/'live.sqlite', clock=lambda: 1700000000)
    fish = next(visitors()); store.save(fish)
    records = store.collection()
    for _ in range(10):
        assert display_state(records, 1, now=1700003600)['fish'] == []
    assert store.collection() == records
    store.close()
