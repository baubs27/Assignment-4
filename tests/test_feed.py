import asyncio
import sys
from types import SimpleNamespace
from backend.feed import YahooFeed
from backend.store import Store


def test_stop_prevents_reconnect_when_provider_swallows_cancellation(tmp_path, monkeypatch):
    entered = asyncio.Event()
    connections = []

    class Client:
        def __init__(self, **kw): pass
        async def __aenter__(self):
            connections.append(self)
            return self
        async def __aexit__(self, *args): pass
        async def subscribe(self, symbols): pass
        async def listen(self, handler):
            entered.set()
            try:
                await asyncio.sleep(100)
            except asyncio.CancelledError:
                return  # Match yfinance's cancellation behavior.

    monkeypatch.setitem(sys.modules, 'yfinance', SimpleNamespace(AsyncWebSocket=Client))
    async def check():
        feed = YahooFeed(Store(tmp_path / 'feed.sqlite3'))
        feed.start()
        await asyncio.wait_for(entered.wait(), 2)
        await asyncio.wait_for(feed.stop(), 2)
        assert feed.state == 'disconnected'
        assert feed.task is None and not feed.enabled
        assert len(connections) == 1
    asyncio.run(check())
