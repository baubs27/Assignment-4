import copy
import pytest
from backend.simulation import Broker, Strategy, simulate_bars, simulate_receipts
from backend.store import Store
from backend.research import Research


def config(**kw):
    return dict(symbol='AAPL',source='demo',interval='1m',fast=2,slow=3,
                cash=1000,quantity=4,fee=0,slippage_bps=0,**kw)


def bars():
    closes=[10,9,8,7,8,10,12,10,8,7,9,12]
    return [dict(timestamp=1000000000+i*60,open=c-.5,high=c+1,low=c-1,
                 close=c,volume=100,complete=True) for i,c in enumerate(closes)]


def test_known_account_example_and_partial_sales():
    b=Broker(1000)
    b.submit('buy',4,0,1); b.fill_pending(100,1); b.mark_to_market(110,2)
    assert b.account()['cash']==600 and b.account()['unrealized_pnl']==40
    b.submit('sell',1,2,3); b.fill_pending(110,3)
    b.submit('sell',3,3,4); b.fill_pending(105,4); b.mark_to_market(105,4)
    a=b.account()
    assert (a['cash'],a['quantity'],a['realized_pnl'],a['unrealized_pnl'],a['equity'])==(1025,0,25,0,1025)
    assert len(b.orders)==len(b.fills)==3


def test_fee_basis_slippage_rejections_and_no_repeat_fill():
    b=Broker(1000,fee=1,slippage_bps=100)
    b.submit('buy',4,0,1); b.fill_pending(100,1); b.fill_pending(100,1)
    assert len(b.fills)==1 and b.cash==595 and b.cost==405
    b.submit('sell',1,1,2); b.fill_pending(110,2); b.mark_to_market(110,2)
    assert b.account()['realized_pnl']==6.65
    assert b.account()['unrealized_pnl']==26.25
    assert b.account()['total_pnl']==32.9
    b.submit('buy',1000,2,3); b.submit('sell',1000,2,3); b.fill_pending(100,3)
    assert [o['status'] for o in b.orders][-2:]==['rejected','rejected']


def test_drawdown_and_invalid_marks():
    b=Broker(1000)
    b.submit('buy',4,0,1);b.fill_pending(100,1)
    b.mark_to_market(100,1);b.mark_to_market(110,2);b.mark_to_market(95,3)
    assert b.account()['max_drawdown_pct']==pytest.approx(100*60/1040,abs=.0001)
    with pytest.raises(ValueError): b.mark_to_market(float('nan'),4)
    with pytest.raises(ValueError): Broker(0)


def test_next_open_execution_unfinished_and_no_future_dependency():
    sample=bars()
    result=simulate_bars(sample,config())
    assert result['signals'] and result['fills']
    for fill in result['fills']:
        order=next(o for o in result['orders'] if o['id']==fill['order_id'])
        assert fill['timestamp']>=order['submitted_at']
        bar=next(c for c in sample if c['timestamp']==fill['timestamp'])
        assert fill['price']==bar['open']
    prefix=simulate_bars(sample[:8],config())
    altered=copy.deepcopy(sample)
    for c in altered[8:]: c.update(open=1000,high=1001,low=999,close=1000)
    changed=simulate_bars(altered,config())
    assert prefix['decisions']==changed['decisions'][:8]
    assert prefix['fills']==[f for f in changed['fills'] if f['timestamp']<=sample[7]['timestamp']]
    sample[-1]['complete']=False
    no_preview_trade=simulate_bars(sample,config())
    assert all(d['timestamp']!=sample[-1]['timestamp'] for d in no_preview_trade['decisions'])
    assert no_preview_trade['orders'][-1]['status']!='pending'


def test_strategy_restore_and_paused_account_persistence(tmp_path):
    store=Store(tmp_path/'research.sqlite3'); research=Research(store)
    s=Strategy(config())
    for b in bars()[:7]: s.close(b,b['timestamp']+60)
    restored=Strategy.restore(s.state())
    assert restored.result()==s.result()
    run=research.start_paper(config(),clock=1000000000)
    s=Strategy.restore(run['state']); s.broker.submit('buy',4,1000000000,1000000001)
    run.update(state=s.state(),result=s.result()); research.save(run)
    research.pause(run['id']); research.tick(clock=1000000500)
    loaded=Research(Store(store.path)).get(run['id'])
    assert loaded['status']=='paused' and loaded['result']['account']['cash']==1000
    assert loaded['result']['orders'][0]['status']=='cancelled'


def test_receipt_backtest_causality_duplicates_late_changes(tmp_path):
    store=Store(tmp_path/'events.sqlite3')
    t=1794236400
    for i,c in enumerate([10,9,8,7,8,10,12,10,8,7,9,12]):
        store.record(dataset='demo',source='test fixture',symbol='AAPL',source_time=t+i*60+5,
                     price=c,receipt_time=t+i*60+5.5)
    rows=store.deliveries('demo','AAPL')
    result=simulate_receipts(rows,config())
    for fill in result['fills']:
        o=next(o for o in result['orders'] if o['id']==fill['order_id'])
        assert fill['receipt_id']>o['decision_receipt']
        assert fill['timestamp']>=o['submitted_at']
    # A correction arriving after decisions were made cannot rewrite earlier decisions.
    store.record(dataset='demo',source='test fixture',symbol='AAPL',source_time=t+5,
                 price=1000,receipt_time=t+800)
    later=simulate_receipts(store.deliveries('demo','AAPL'),config())
    assert result['decisions']==later['decisions'][:len(result['decisions'])]


def test_active_paper_does_not_trade_warmup_then_persists_fill(tmp_path):
    store=Store(tmp_path/'paper.sqlite3'); research=Research(store)
    t=1794236400
    def tick(i,p):
        store.record(dataset='demo',source='constructed test',symbol='AAPL',source_time=t+i*60+5,
                     price=p,receipt_time=t+i*60+5.5)
    for i,p in enumerate([10,9,8,7]): tick(i,p)
    r=research.start_paper(config(),clock=t+4*60)
    assert not r['result']['orders']
    for i,p in enumerate([8,10,12,11],4):
        tick(i,p); research.tick(clock=t+i*60+6)
    final=research.get(r['id'])
    assert final['result']['account']['quantity']==4
    assert len(final['result']['fills'])==1
    again=Research(Store(store.path)).get(r['id'])
    assert again['result']==final['result']
