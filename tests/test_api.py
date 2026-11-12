import importlib
from fastapi.testclient import TestClient


def test_health_websocket_replay_feed_off_and_readonly(tmp_path, monkeypatch):
    monkeypatch.setenv('MARKET_DB', str(tmp_path / 'api.sqlite3'))
    monkeypatch.setenv('MARKET_LIVE', '0')
    import backend.main
    main = importlib.reload(backend.main)
    with TestClient(main.app) as client:
        assert client.get('/api/health').json()['status'] == 'ok'
        before = client.get('/api/sessions').json()
        assert client.get('/api/feed').json()['state'] == 'disconnected'
        with client.websocket_connect('/ws/market?dataset=demo&mode=replay&symbol=AAPL') as ws:
            state = ws.receive_json()
            assert state['cursor'] == 0 and state['total'] == 276
            ws.send_json({'action': 'step'})
            assert ws.receive_json()['cursor'] == 1
            ws.send_json({'action': 'seek', 'cursor': 276})
            state = ws.receive_json()
            assert state['candles'][-1]['close'] == 102.5
            assert state['stats']['duplicates'] == 1
            ws.send_json({'action': 'reset'})
            assert ws.receive_json()['candles'] == []
        assert client.get('/api/sessions').json() == before
        assert client.post('/api/feed/disconnect').json()['state'] == 'disconnected'
        with client.websocket_connect('/ws/market?dataset=live&mode=replay&symbol=MSFT') as ws:
            assert ws.receive_json()['total'] == 0
