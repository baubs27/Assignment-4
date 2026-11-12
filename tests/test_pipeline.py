import sqlite3
from datetime import datetime, timezone
import pytest
from backend.store import Store, project
from backend.candles import build_candles
from backend.demo import seed_demo

T = datetime(2026, 11, 9, 15, tzinfo=timezone.utc).timestamp()


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / 'test.sqlite3')


def add(store, t=5, price=100, vol=1004, **kw):
    return store.record(dataset='test', source='fixture', symbol='AAPL', source_time=T+t,
                        price=price, cumulative_volume=vol, receipt_time=T+t+.5, **kw)


def test_course_candle_volume_and_late_delivery(store):
    add(store, -1, 99, 1000)
    add(store, 5, 100, 1004)
    add(store, 50, 101, 1011)
    add(store, 20, 103, 1009)  # Source time orders prices, not arrival order.
    rows = store.deliveries('test', 'AAPL')
    c = build_candles(rows, clock=T+55)[-1]
    assert (c['open'], c['high'], c['low'], c['close'], c['volume'], c['complete']) == (100,103,100,101,11,False)
    assert build_candles(rows, clock=T+60)[-1]['complete'] is True


def test_duplicate_same_time_ambiguity_and_restart(store):
    first = add(store)
    assert add(store)['duplicate']
    add(store, price=102)
    rows = Store(store.path).deliveries('test', 'AAPL')
    assert len(rows) == 3
    assert len(project(rows)) == 2
    assert rows[0]['id'] == rows[1]['id'] == first['observation_id']
    assert build_candles(rows, clock=T+60)[0]['high'] == 102


def test_revision_as_of_receipt_not_future_information(store):
    add(store, event_key='tick-1', revision=0)
    add(store, price=105, event_key='tick-1', revision=1)
    # A stale revision arriving again cannot supersede the newer version.
    add(store, event_key='tick-1', revision=0)
    rows = store.deliveries('test','AAPL')
    assert build_candles(rows[:1], clock=T+60)[0]['close'] == 100
    assert build_candles(rows, clock=T+60)[0]['close'] == 105
    assert len(project(rows)) == 1
    assert len({r['id'] for r in rows}) == 2
    with pytest.raises(sqlite3.IntegrityError):
        add(store, price=107, event_key='tick-1', revision=1)


def test_volume_unknown_on_missing_baseline_reset_and_rolling(store):
    add(store, vol=1000)
    add(store, t=65, vol=20)  # Reset
    add(store, t=125, vol=None)
    add(store, t=185, vol=500, volume_kind='rolling')
    assert all(c['volume'] is None for c in build_candles(store.deliveries('test','AAPL'), clock=T+300))


def test_higher_intervals_and_empty(store):
    add(store, -1, 99, 1000)
    add(store, 5, 100, 1004)
    add(store, 65, 103, 1009)
    rows = store.deliveries('test','AAPL')
    c = build_candles(rows, '5m', clock=T+300)[-1]
    assert (c['open'],c['close'],c['volume'],c['complete']) == (100,103,9,True)
    assert build_candles([], '1d') == []


def test_demo_idempotent_replay_readonly_and_range(store):
    seed_demo(store)
    before = store.sessions()
    rows = store.deliveries('demo','AAPL')
    assert len(rows) == 276
    assert sum(r['duplicate'] for r in rows) == 1
    for _ in range(2):
        result = build_candles(rows, clock=rows[-1]['receipt_time'])
        assert result[-1]['close'] == 102.5
        seed_demo(store)
    assert store.sessions() == before
    selected = store.deliveries('demo','AAPL', start=rows[10]['receipt_time'], end=rows[20]['receipt_time'])
    assert len(selected) == 11


def test_validation(store):
    with pytest.raises(ValueError): add(store, price=float('nan'))
    with pytest.raises(ValueError): add(store, vol=-1)
    with pytest.raises(ValueError): add(store, event_key='no-revision')
