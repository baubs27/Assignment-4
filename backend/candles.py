"""Deterministic aggregation, shared by live snapshots and receipt-order replay."""
from datetime import datetime, timezone
from .store import project

INTERVALS = {'1m': 60, '5m': 300, '15m': 900, '1h': 3600, '1d': 86400}


def session_date(t):
    # Equities use the New York trading date; crypto volume is not treated as session volume.
    from zoneinfo import ZoneInfo
    return datetime.fromtimestamp(t, ZoneInfo('America/New_York')).date()


def build_candles(deliveries, interval='1m', clock=None):
    if clock is None:
        from .store import utc_now
        clock = utc_now()
    seconds = INTERVALS[interval]
    candles, previous = {}, None
    for d in project(deliveries):
        t, price = d['source_time'], d['price']
        bucket = int(t // seconds) * seconds
        delta = None
        if (d['volume_kind'] == 'session' and previous and previous['volume_kind'] == 'session'
                and session_date(t) == session_date(previous['source_time'])
                and d['cumulative_volume'] is not None and previous['cumulative_volume'] is not None
                and d['cumulative_volume'] >= previous['cumulative_volume']):
            delta = d['cumulative_volume'] - previous['cumulative_volume']
        c = candles.setdefault(bucket, dict(timestamp=bucket, open=price, high=price,
            low=price, close=price, volume=0, volume_known=True, observations=0,
            complete=bucket + seconds <= clock))
        c['high'], c['low'], c['close'] = max(c['high'], price), min(c['low'], price), price
        c['observations'] += 1
        if delta is None:
            c['volume_known'] = False
        else:
            c['volume'] += delta
        previous = d
    for c in candles.values():
        if not c.pop('volume_known'):
            c['volume'] = None
    return list(candles.values())
