import asyncio
import importlib
from types import SimpleNamespace
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from backend.research import Research
from backend.store import Store


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('MARKET_DB',str(tmp_path/'api.sqlite3'))
    monkeypatch.setenv('MARKET_LIVE','0')
    import backend.main
    main=importlib.reload(backend.main)
    with TestClient(main.app) as c: yield c,main


def test_saved_backtest_validation_websocket_indicators_and_paper_pause(client):
    c,main=client
    params=dict(source='demo',fast=2,slow=3,cash=1000,quantity=4)
    before=c.get('/api/sessions').json()
    response=c.post('/api/research/backtest',json=params)
    assert response.status_code==200,response.text
    run=response.json()
    assert run['result']['fills'] and run['source']['digest']
    assert c.get('/api/research/runs/'+run['id']).json()==run
    assert c.get('/api/sessions').json()==before
    assert c.post('/api/research/backtest',json={**params,'fast':20,'slow':5}).status_code==422
    assert c.post('/api/research/backtest',json={**params,'start':200,'end':100}).status_code==422
    assert c.post('/api/research/backtest',json={**params,'source':'recorded'}).status_code==400
    assert c.post('/api/research/backtest',json={**params,'source':'history','history_id':'missing'}).status_code==400
    with c.websocket_connect('/ws/market?mode=replay&dataset=demo&symbol=AAPL') as ws:
        ws.receive_json();ws.send_json({'action':'seek','cursor':276})
        full=ws.receive_json()
        assert full['cursor']==276 and not full['indicators'][-1]['confirmed']
        ws.send_json({'action':'indicators','fast':2,'slow':3})
        result=ws.receive_json()
        assert result['cursor']==276
        assert result['indicators'][-1]['fast']==pytest.approx(101.86)
    paper=c.post('/api/research/paper',json={**params,'source':'recorded'}).json()
    paused=c.post('/api/research/paper/'+paper['id']+'/pause').json()
    assert paused['status']=='paused' and paused['result']['account']['fills']==0
    resumed=c.post('/api/research/paper/'+paper['id']+'/resume').json()
    assert resumed['status']=='active' and resumed['result']['account']['cash']==1000


def test_historical_provider_boundary_and_failure(client,monkeypatch):
    c,main=client
    prices=[10,9,8,7,8,10,12,10,8,7,9,12]
    frame=pd.DataFrame({'Open':[p-.5 for p in prices],'High':[p+1 for p in prices],
        'Low':[p-1 for p in prices],'Close':prices,'Volume':[100]*len(prices)},
        index=pd.date_range('2020-01-01',periods=len(prices),tz='America/New_York'))
    calls=[]
    def history(**kw):calls.append(kw);return frame
    import yfinance
    monkeypatch.setattr(yfinance,'Ticker',lambda symbol:SimpleNamespace(history=history))
    response=c.post('/api/research/history',json={'symbol':'AAPL','period':'1y'})
    assert response.status_code==200,response.text
    h=response.json();assert h['bars']==12 and calls[0]['auto_adjust'] is False
    run=c.post('/api/research/backtest',json=dict(source='history',history_id=h['id'],fast=2,slow=3,cash=1000,quantity=4)).json()
    assert run['config']['interval']=='1d' and run['result']['fills']
    assert 'daily' in run['source']['execution']
    def fail(**kw):raise ConnectionError('Fixture provider failure')
    monkeypatch.setattr(yfinance,'Ticker',lambda symbol:SimpleNamespace(history=fail))
    assert c.post('/api/research/history',json={'symbol':'AAPL'}).status_code==502
    assert len(c.get('/api/research/history').json()['history'])==1


def test_restart_pauses_active_account_and_resume_skips_downtime(tmp_path):
    store=Store(tmp_path/'restart.sqlite3'); research=Research(store)
    params=dict(symbol='AAPL',source='recorded',interval='1m',fast=2,slow=3,cash=1000,quantity=4,fee=0,slippage_bps=0)
    r=research.start_paper(params)
    # More recent experiments must not hide an older active account from lifecycle processing.
    with store.connect() as db:
        for i in range(60):
            db.execute('''INSERT INTO simulation_runs SELECT ?, 'backtest', 'complete',created_at+?,
                updated_at,config_json,source_json,state_json,result_json,last_receipt
                FROM simulation_runs WHERE id=?''',(f'constructed-backtest-{i}',i+1,r['id']))
    assert r['id'] not in [x['id'] for x in research.runs()]
    async def restart():
        next_service=Research(Store(store.path))
        await next_service.startup()
        assert next_service.get(r['id'])['status']=='paused'
        await next_service.shutdown()
        resumed=next_service.resume(r['id'])
        assert resumed['result']['account']['cash']==1000 and not resumed['result']['fills']
    asyncio.run(restart())
