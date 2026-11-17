"""Persistent historical experiments and paper accounts, isolated from market records."""
import asyncio
import json
import uuid
import threading
from functools import wraps
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from .store import utc_now, project
from .candles import build_candles
from .simulation import Strategy, receipt_step, simulate_bars, simulate_receipts, source_digest


def synchronized(method):
    @wraps(method)
    def call(self,*args,**kwargs):
        with self.lock: return method(self,*args,**kwargs)
    return call


class Research:
    def __init__(self, store):
        self.store = store
        self.task = None
        self.lock = threading.RLock()
        with store.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS history_sets (
                  id TEXT PRIMARY KEY, symbol TEXT NOT NULL, fetched_at REAL NOT NULL,
                  source TEXT NOT NULL, digest TEXT NOT NULL, bars_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS simulation_runs (
                  id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL,
                  created_at REAL NOT NULL, updated_at REAL NOT NULL, config_json TEXT NOT NULL,
                  source_json TEXT NOT NULL, state_json TEXT, result_json TEXT NOT NULL,
                  last_receipt INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS simulated_orders (
                  run_id TEXT NOT NULL REFERENCES simulation_runs(id), order_id INTEGER NOT NULL,
                  status TEXT NOT NULL, payload_json TEXT NOT NULL, PRIMARY KEY(run_id,order_id)
                );
                CREATE TABLE IF NOT EXISTS simulated_fills (
                  run_id TEXT NOT NULL REFERENCES simulation_runs(id), fill_id INTEGER NOT NULL,
                  payload_json TEXT NOT NULL, PRIMARY KEY(run_id,fill_id)
                );
            ''')

    def save(self, run):
        run['updated_at'] = utc_now()
        with self.store.connect() as db:
            db.execute('''INSERT INTO simulation_runs VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at,
                state_json=excluded.state_json,result_json=excluded.result_json,last_receipt=excluded.last_receipt''',
                (run['id'],run['kind'],run['status'],run['created_at'],run['updated_at'],
                 json.dumps(run['config']),json.dumps(run['source']),
                 json.dumps(run.get('state')),json.dumps(run['result']),run.get('last_receipt',0)))
            for order in run['result']['orders']:
                db.execute('''INSERT INTO simulated_orders VALUES (?,?,?,?) ON CONFLICT(run_id,order_id)
                    DO UPDATE SET status=excluded.status,payload_json=excluded.payload_json''',
                    (run['id'],order['id'],order['status'],json.dumps(order)))
            for fill in run['result']['fills']:
                db.execute('INSERT OR IGNORE INTO simulated_fills VALUES (?,?,?)',
                           (run['id'],fill['id'],json.dumps(fill)))
        return run

    def get(self, run_id):
        with self.store.connect() as db:
            row = db.execute('SELECT * FROM simulation_runs WHERE id=?',(run_id,)).fetchone()
        if not row: raise KeyError('Simulation not found')
        r = dict(row)
        for name in ['config','source','state','result']: r[name] = json.loads(r.pop(name+'_json'))
        return r

    def runs(self):
        with self.store.connect() as db:
            return [dict(id=r['id'],kind=r['kind'],status=r['status'],created_at=r['created_at'],
                         config=json.loads(r['config_json'])) for r in db.execute(
                'SELECT id,kind,status,created_at,config_json FROM simulation_runs ORDER BY created_at DESC LIMIT 50')]

    def active_ids(self):
        # Account lifecycle must not depend on the UI's latest-50 experiment list.
        with self.store.connect() as db:
            return [r['id'] for r in db.execute("SELECT id FROM simulation_runs WHERE kind='paper' AND status='active'")]

    def history(self):
        with self.store.connect() as db:
            return [dict(id=r['id'],symbol=r['symbol'],fetched_at=r['fetched_at'],source=r['source'],
                digest=r['digest'],bars=len(json.loads(r['bars_json']))) for r in db.execute(
                'SELECT * FROM history_sets ORDER BY fetched_at DESC')]

    def download_history(self, symbol, period='1y'):
        import yfinance as yf
        import math
        frame = yf.Ticker(symbol).history(period=period, interval='1d', auto_adjust=False,
                                         actions=False, timeout=15)
        today = datetime.now(ZoneInfo('America/New_York')).date()
        bars = []
        for index,row in frame.iterrows():
            # Exclude today's daily candle conservatively, including after-hours refreshes.
            if index.date() >= today: continue
            prices = [float(row[k]) for k in ['Open','High','Low','Close']]
            if not all(math.isfinite(x) and x > 0 for x in prices): continue
            o,h,l,c = prices
            if h < max(o,c) or l > min(o,c) or l > h: continue
            t = datetime.combine(index.date(),datetime.min.time(),tzinfo=timezone.utc).timestamp()
            v = float(row['Volume'])
            bars.append(dict(timestamp=int(t),open=o,high=h,low=l,close=c,
                             volume=v if math.isfinite(v) and v >= 0 else None,complete=True))
        if not bars: raise ValueError('Yahoo returned no completed daily bars; no synthetic fallback was used.')
        key = uuid.uuid4().hex
        source = f'Yahoo Finance historical daily / {period} / unadjusted / no dividends'
        with self.store.connect() as db:
            db.execute('INSERT INTO history_sets VALUES (?,?,?,?,?,?)',
                       (key,symbol,utc_now(),source,source_digest(bars),json.dumps(bars)))
        return next(h for h in self.history() if h['id']==key)

    def backtest(self, config):
        config = dict(config)
        source = config['source']
        if source == 'history':
            with self.store.connect() as db:
                h = db.execute('SELECT * FROM history_sets WHERE id=?',(config['history_id'],)).fetchone()
            if not h or h['symbol'] != config['symbol']: raise ValueError('Select a historical download for this symbol.')
            config['interval'] = '1d'
            bars = json.loads(h['bars_json'])
            bars = [b for b in bars if (config.get('start') is None or b['timestamp']>=config['start'])
                    and (config.get('end') is None or b['timestamp']<=config['end'])]
            metadata = dict(label=h['source'],digest=source_digest(bars),history_id=h['id'],
                            fetched_at=h['fetched_at'],execution='Next completed daily bar open',bars=len(bars))
            result = simulate_bars(bars,config)
        else:
            dataset = 'demo' if source == 'demo' else 'live'
            rows = self.store.deliveries(dataset,config['symbol'],config.get('start'),config.get('end'))
            if len(rows)>5000: raise ValueError('Select a narrower receipt range (maximum 5,000 receipts per experiment).')
            metadata = dict(label='Constructed teaching fixture' if dataset=='demo' else 'Recorded Yahoo observations',
                dataset=dataset,digest=source_digest(rows),receipts=len(rows),
                execution='Next eligible observed source price after the decision receipt')
            result = simulate_receipts(rows,config)
        if not result['decisions']: raise ValueError('No completed candles in this selection.')
        return self.save(dict(id=uuid.uuid4().hex,kind='backtest',status='complete',created_at=utc_now(),
            config=config,source=metadata,state=None,result=result,last_receipt=0))

    @synchronized
    def start_paper(self, config, clock=None):
        clock = utc_now() if clock is None else clock
        config = dict(config)
        dataset = 'demo' if config['source']=='demo' else 'live'
        rows = self.store.deliveries(dataset,config['symbol'])
        s = Strategy(config)
        # Warm up from available completed bars, without placing retrospective orders.
        for c in build_candles(rows,config['interval'],clock): s.close(c,clock,trade=False)
        if rows:
            latest = project(rows)[-1]
            s.last_source = latest['source_time']
            s.broker.mark_to_market(latest['price'],clock)
        return self.save(dict(id=uuid.uuid4().hex,kind='paper',status='active',created_at=clock,
            config=config,source=dict(dataset=dataset,label='Constructed teaching fixture' if dataset=='demo' else 'Yahoo Finance streaming',
                execution='Next new eligible source price after a completed-bar decision',warmup_bars=len(s.decisions)),
            state=s.state(),result=s.result(),last_receipt=rows[-1]['receipt_id'] if rows else 0))

    @synchronized
    def pause(self, run_id, reason='Paused by user; pending orders cancelled'):
        r = self.get(run_id)
        if r['kind'] != 'paper': raise ValueError('Only paper accounts can be paused')
        s = Strategy.restore(r['state']); s.broker.cancel(reason)
        r.update(status='paused',state=s.state(),result=s.result())
        return self.save(r)

    @synchronized
    def resume(self, run_id, clock=None):
        clock = utc_now() if clock is None else clock
        r = self.get(run_id)
        if r['kind']!='paper': raise ValueError('Only paper accounts can be resumed')
        if r['status']=='active': return r
        s=Strategy.restore(r['state'])
        rows=self.store.deliveries(r['source']['dataset'],r['config']['symbol'])
        for c in build_candles(rows,r['config']['interval'],clock): s.close(c,clock,trade=False)
        s.last_clock=clock
        if rows:
            latest=project(rows)[-1]
            s.last_source=latest['source_time'];s.broker.mark_to_market(latest['price'],clock)
        r.update(status='active',state=s.state(),result=s.result(),last_receipt=rows[-1]['receipt_id'] if rows else 0)
        return self.save(r)

    @synchronized
    def tick(self, clock=None):
        clock = utc_now() if clock is None else clock
        for run_id in self.active_ids():
            r = self.get(run_id); s = Strategy.restore(r['state'])
            rows = self.store.deliveries(r['source']['dataset'],r['config']['symbol'])
            seen = [x for x in rows if x['receipt_id']<=r['last_receipt']]
            before = s.last_bar
            new = [x for x in rows if x['receipt_id']>r['last_receipt']]
            for row in new:
                receipt_step(s,seen,row,clock=max(r['created_at'],row['receipt_time']))
            # Settle a candle even when no tick arrives exactly at the boundary.
            if seen: receipt_step(s,seen,clock=clock)
            if new or s.last_bar != before:
                r.update(state=s.state(),result=s.result(),last_receipt=rows[-1]['receipt_id'] if rows else 0)
                self.save(r)

    async def worker(self):
        while True:
            self.tick()
            await asyncio.sleep(.5)

    async def startup(self):
        # Persist balances, but never simulate unobserved downtime trading on restart.
        for run_id in self.active_ids():
            self.pause(run_id,'Paused after server restart; no downtime fills')
        self.task = asyncio.create_task(self.worker())

    async def shutdown(self):
        if self.task:
            self.task.cancel()
            try: await self.task
            except asyncio.CancelledError: pass
