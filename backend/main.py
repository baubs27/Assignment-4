import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from .store import Store, utc_now, project
from .candles import build_candles, INTERVALS
from .demo import seed_demo
from .feed import YahooFeed, SYMBOLS
from .indicators import indicator_rows, validate_windows
from .research import Research
from .research_api import router as research_router

ROOT = Path(__file__).resolve().parent.parent
store = Store(os.environ.get('MARKET_DB', ROOT / 'data' / 'market.sqlite3'))
feed = YahooFeed(store)
research = Research(store)


@asynccontextmanager
async def lifespan(app):
    seed_demo(store)
    await research.startup()
    if os.environ.get('MARKET_LIVE', '1') == '1':
        feed.start()
    yield
    await research.shutdown()
    await feed.stop()


app = FastAPI(title='Market Workstation', lifespan=lifespan)
app.include_router(research_router(research))


@app.get('/api/health')
def health():
    return {'status': 'ok', 'service': 'market-workstation', 'storage': 'SQLite'}


@app.get('/api/sessions')
def sessions():
    return {'sessions': store.sessions(), 'symbols': SYMBOLS, 'intervals': list(INTERVALS)}


@app.get('/api/feed')
def status():
    return feed.status()


@app.post('/api/feed/{action}')
async def control_feed(action: str):
    if action == 'connect':
        feed.start()
    elif action == 'disconnect':
        await feed.stop()
    else:
        raise HTTPException(400, 'Use connect or disconnect')
    return feed.status()


def snapshot(rows, symbol, dataset, interval, clock, mode, cursor, total, fast=5, slow=20):
    effective = project(rows)
    latest = effective[-1] if effective else None
    last_receipt = rows[-1] if rows else None
    candles = build_candles(rows, interval, clock)
    audit = []
    for r in reversed(rows[-12:]):
        audit.append({k: r[k] for k in ['id', 'receipt_id', 'source_time', 'receipt_time',
            'price', 'cumulative_volume', 'duplicate', 'event_key', 'revision']})
    return dict(type='snapshot', symbol=symbol, dataset=dataset, interval=interval, mode=mode,
        clock=clock, server_time=utc_now(), candles=candles, audit=audit,
        stats=dict(deliveries=len(rows), observations=len({r['id'] for r in rows}),
                   effective=len(effective), duplicates=sum(r['duplicate'] for r in rows)),
        latest=latest, last_receipt_time=last_receipt['receipt_time'] if last_receipt else None,
        feed=feed.status(), cursor=cursor, total=total,
        indicators=indicator_rows(candles,fast,slow), sma_windows={'fast':fast,'slow':slow})


@app.websocket('/ws/market')
async def market(ws: WebSocket):
    await ws.accept()
    q = ws.query_params
    symbol, dataset = q.get('symbol', 'AAPL'), q.get('dataset', 'live')
    interval, mode = q.get('interval', '1m'), q.get('mode', 'live')
    if (symbol not in SYMBOLS or dataset not in ['live', 'demo'] or interval not in INTERVALS
            or mode not in ['live', 'replay'] or (dataset == 'demo' and mode != 'replay')):
        await ws.close(code=1008, reason='Invalid market selection'); return
    try:
        fast, slow = int(q.get('fast',5)), int(q.get('slow',20))
        validate_windows(fast,slow)
        start = float(q['start']) if q.get('start') else None
        end = float(q['end']) if q.get('end') else None
        if start is not None and end is not None and start > end:
            raise ValueError()
    except ValueError:
        await ws.close(code=1008, reason='Invalid receipt range or SMA windows'); return
    # Freeze selected receipts for deterministic, read-only replay.
    recorded = store.deliveries(dataset, symbol, start, end) if mode == 'replay' else []
    cursor, playing, batch = 0, False, 10
    try:
        while True:
            rows = recorded[:cursor] if mode == 'replay' else store.deliveries(dataset, symbol)
            clock = (rows[-1]['receipt_time'] if rows else (recorded[0]['receipt_time'] if recorded else utc_now())) if mode == 'replay' else utc_now()
            payload = snapshot(rows, symbol, dataset, interval, clock, mode, cursor, len(recorded),fast,slow)
            payload['playing'] = playing
            await ws.send_json(payload)
            try:
                command = await asyncio.wait_for(ws.receive_json(), timeout=.5 if playing else 1)
                action = command.get('action')
                if action=='indicators':
                    try:
                        a,b = int(command['fast']),int(command['slow'])
                        validate_windows(a,b)
                        fast,slow = a,b
                    except (ValueError,KeyError,TypeError):
                        await ws.send_json({'type':'error','message':'SMA windows require 1 <= fast < slow <= 500'})
                if mode == 'replay':
                    if action == 'play': playing = True
                    elif action == 'pause': playing = False
                    elif action == 'reset': cursor, playing = 0, False
                    elif action == 'step': cursor, playing = min(cursor + 1, len(recorded)), False
                    elif action == 'seek':
                        cursor = max(0, min(int(command.get('cursor', 0)), len(recorded)))
                    elif action == 'speed':
                        batch = max(1, min(int(command.get('batch', 10)), 100))
            except asyncio.TimeoutError:
                if playing:
                    cursor = min(cursor + batch, len(recorded))
                    if cursor == len(recorded): playing = False
    except (WebSocketDisconnect, RuntimeError):
        pass


if (ROOT / 'frontend' / 'dist').exists():
    app.mount('/', StaticFiles(directory=ROOT / 'frontend' / 'dist', html=True), name='frontend')
