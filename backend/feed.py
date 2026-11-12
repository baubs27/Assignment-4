"""One shared Yahoo subscription. Transport connectivity is distinct from freshness."""
import asyncio
import contextlib
import logging
from .store import utc_now

log = logging.getLogger(__name__)
SYMBOLS = ['AAPL', 'MSFT', 'BTC-USD']


class YahooFeed:
    def __init__(self, store):
        self.store = store
        self.task = None
        self.enabled = False
        self.state = 'disconnected'
        self.detail = 'Live feed is off.'
        self.connected_at = None
        self.received = {}
        self.latest_source = {}
        self.rejected = 0

    def accept(self, msg):
        symbol = msg.get('id')
        if symbol not in SYMBOLS or 'price' not in msg or 'time' not in msg:
            return
        # Yahoo PricingData.time is milliseconds since the Unix epoch.
        t = float(msg['time']) / 1000
        if t <= 0 or t > utc_now() + 300:
            raise ValueError('Yahoo source timestamp outside expected range')
        volume = msg.get('day_volume')
        self.store.record(dataset='live', source='Yahoo Finance WebSocket', symbol=symbol,
            source_time=t, price=msg['price'], cumulative_volume=volume,
            volume_kind='rolling' if symbol.endswith('-USD') else 'session', raw=msg)
        self.received[symbol] = utc_now()
        self.latest_source[symbol] = max(t, self.latest_source.get(symbol, t))
        self.detail = 'Subscribed to AAPL, MSFT, BTC-USD. Inspect each instrument’s source age.'

    async def run(self):
        import yfinance as yf
        delay = 2
        while self.enabled:
            self.state, self.detail = 'connecting', 'Opening Yahoo Finance WebSocket…'
            try:
                async with yf.AsyncWebSocket(verbose=False) as ws:
                    await asyncio.wait_for(ws.subscribe(SYMBOLS), timeout=20)
                    self.state, self.detail = 'connected', 'Subscribed. Waiting for source observations.'
                    self.connected_at = utc_now()
                    delay = 2
                    def receive(msg):
                        try:
                            self.accept(msg)
                        except Exception as exc:
                            self.rejected += 1
                            log.warning('Rejected market message (%s)', type(exc).__name__)
                    # Bounded listener forces reconnect when a socket silently stops receiving.
                    await asyncio.wait_for(ws.listen(receive), timeout=300)
                    if not self.enabled:
                        return
                    raise ConnectionError('Listener ended')
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.state = 'unavailable'
                self.detail = f'Yahoo connection unavailable ({type(exc).__name__}). Retrying in {delay}s.'
                log.warning(self.detail)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)

    def start(self):
        self.enabled = True
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.run())
        return self.status()

    async def stop(self):
        self.enabled = False
        self.state, self.detail = 'disconnected', 'Yahoo feed disconnected by user. Recorded data remains available.'
        if self.task:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task
            self.task = None

    def status(self):
        return dict(state=self.state, detail=self.detail, connected_at=self.connected_at,
                    received=self.received, latest_source=self.latest_source, rejected=self.rejected)
