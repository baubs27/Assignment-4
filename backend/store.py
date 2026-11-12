"""Append-only receipts and immutable observation versions, using SQLite only."""
import hashlib
import json
import math
import sqlite3
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc).timestamp()


class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS observations (
                  id INTEGER PRIMARY KEY, dataset TEXT NOT NULL, source TEXT NOT NULL,
                  symbol TEXT NOT NULL, source_time REAL NOT NULL, price REAL NOT NULL,
                  cumulative_volume REAL, volume_kind TEXT NOT NULL,
                  event_key TEXT, revision INTEGER, raw_json TEXT NOT NULL,
                  fingerprint TEXT NOT NULL UNIQUE,
                  UNIQUE(dataset, source, symbol, event_key, revision)
                );
                CREATE TABLE IF NOT EXISTS receipts (
                  id INTEGER PRIMARY KEY, observation_id INTEGER NOT NULL REFERENCES observations(id),
                  receipt_time REAL NOT NULL, duplicate INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS obs_selection ON observations(dataset,symbol,source_time);
                CREATE INDEX IF NOT EXISTS receipts_obs ON receipts(observation_id,id);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def record(self, *, dataset, source, symbol, source_time, price,
               cumulative_volume=None, volume_kind='session', event_key=None,
               revision=None, raw=None, receipt_time=None, connection=None):
        source_time, price = float(source_time), float(price)
        if not math.isfinite(source_time) or source_time <= 0:
            raise ValueError('Invalid source timestamp')
        if not math.isfinite(price) or price <= 0:
            raise ValueError('Invalid positive price')
        if cumulative_volume is not None:
            cumulative_volume = float(cumulative_volume)
            if not math.isfinite(cumulative_volume) or cumulative_volume < 0:
                raise ValueError('Invalid cumulative volume')
        if (event_key is None) != (revision is None):
            raise ValueError('A provider event identity requires an explicit revision number')
        if revision is not None and (not isinstance(revision, int) or revision < 0):
            raise ValueError('Invalid revision')
        normalized = dict(dataset=dataset, source=source, symbol=symbol,
                          source_time=source_time, price=price,
                          cumulative_volume=cumulative_volume, volume_kind=volume_kind,
                          event_key=event_key, revision=revision, raw=raw or {})
        raw_json = json.dumps(normalized['raw'], sort_keys=True, separators=(',', ':'), allow_nan=False)
        fingerprint = hashlib.sha256(json.dumps(normalized, sort_keys=True, allow_nan=False).encode()).hexdigest()
        with (self.connect() if connection is None else nullcontext(connection)) as db:
            prior = db.execute('SELECT id FROM observations WHERE fingerprint=?', (fingerprint,)).fetchone()
            duplicate = prior is not None
            if prior:
                obs_id = prior['id']
            else:
                # A conflicting payload with the same provider revision is never silently discarded.
                cur = db.execute('''INSERT INTO observations
                    (dataset,source,symbol,source_time,price,cumulative_volume,volume_kind,
                     event_key,revision,raw_json,fingerprint) VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                    (dataset, source, symbol, source_time, price, cumulative_volume,
                     volume_kind, event_key, revision, raw_json, fingerprint))
                obs_id = cur.lastrowid
            cur = db.execute('INSERT INTO receipts(observation_id,receipt_time,duplicate) VALUES (?,?,?)',
                             (obs_id, utc_now() if receipt_time is None else receipt_time, int(duplicate)))
            return dict(observation_id=obs_id, receipt_id=cur.lastrowid, duplicate=duplicate)

    def deliveries(self, dataset, symbol, start=None, end=None):
        where, args = ['o.dataset=?', 'o.symbol=?'], [dataset, symbol]
        if start is not None:
            where.append('r.receipt_time>=?'); args.append(start)
        if end is not None:
            where.append('r.receipt_time<=?'); args.append(end)
        with self.connect() as db:
            return [dict(row) for row in db.execute('''SELECT o.*,r.id AS receipt_id,
                r.receipt_time,r.duplicate FROM receipts r JOIN observations o ON o.id=r.observation_id
                WHERE ''' + ' AND '.join(where) + ' ORDER BY r.id', args)]

    def sessions(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute('''SELECT o.dataset,o.source,o.symbol,
                COUNT(*) deliveries, COUNT(DISTINCT o.id) observations,
                SUM(r.duplicate) duplicates, MIN(r.receipt_time) start, MAX(r.receipt_time) end
                FROM receipts r JOIN observations o ON o.id=r.observation_id
                GROUP BY o.dataset,o.source,o.symbol ORDER BY o.dataset,o.symbol''')]


def project(deliveries):
    """Resolve only identities explicitly provided by the producer, as known now."""
    unique = {d['id']: d for d in deliveries}
    selected = {}
    for d in unique.values():
        key = ('event', d['source'], d['event_key']) if d['event_key'] is not None else ('id', d['id'])
        old = selected.get(key)
        if old is None or (d['revision'] is not None and d['revision'] > old['revision']):
            selected[key] = d
    return sorted(selected.values(), key=lambda d: (d['source_time'], d['id']))
