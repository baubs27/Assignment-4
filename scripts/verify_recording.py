"""Read-only verification against an existing local Yahoo capture (feed must be off)."""
import asyncio
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from websockets.asyncio.client import connect

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get('MARKET_URL', 'http://127.0.0.1:8000').rstrip('/')


def get(path):
    with urlopen(BASE + path, timeout=10) as response:
        return json.load(response)


async def main():
    assert get('/api/feed')['state'] == 'disconnected', 'Disconnect Yahoo before this read-only check.'
    before = get('/api/sessions')
    checks = []
    for symbol in ['AAPL', 'MSFT', 'BTC-USD']:
        async with connect(f'{BASE.replace("http", "ws", 1)}/ws/market?symbol={symbol}&mode=replay&dataset=live') as ws:
            initial = json.loads(await ws.recv())
            assert initial['total'] > 0, f'No saved Yahoo observations for {symbol}'
            await ws.send(json.dumps({'action': 'seek', 'cursor': initial['total']}))
            final = json.loads(await ws.recv())
            db_path = os.environ.get('MARKET_DB', ROOT / 'data' / 'market.sqlite3')
            with sqlite3.connect(db_path) as db:
                rows = db.execute("SELECT id,source_time,price FROM observations WHERE dataset='live' AND symbol=? ORDER BY source_time,id", (symbol,)).fetchall()
            # Independent OHLC construction from immutable SQLite observations.
            grouped = {}
            for obs_id, timestamp, price in rows:
                bucket = int(timestamp // 60) * 60
                grouped.setdefault(bucket, []).append(price)
            expected = [dict(timestamp=t, open=p[0], high=max(p), low=min(p), close=p[-1]) for t, p in grouped.items()]
            actual = [{k: c[k] for k in ['timestamp','open','high','low','close']} for c in final['candles']]
            assert actual == expected
            # Run the same replay again; it must not change the outcome or database.
            await ws.send(json.dumps({'action': 'reset'})); await ws.recv()
            await ws.send(json.dumps({'action': 'seek', 'cursor': initial['total']}))
            again = json.loads(await ws.recv())
            assert again['candles'] == final['candles']
            checks.append(dict(symbol=symbol, receipts=final['total'], observations=len(rows),
                bars=len(actual), first_candle=final['candles'][0], last_candle=final['candles'][-1],
                sqlite_ohlc_match=True, repeated_replay_equal=True))
    assert get('/api/sessions') == before, 'Replay changed the stored session!'
    result = dict(checked_at=datetime.now(timezone.utc).isoformat(), source='Actual Yahoo Finance capture',
                  upstream='disconnected', read_only_verified=True, sessions=before['sessions'], checks=checks)
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if output:
        output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
