import math
import random
import pandas as pd
import pytest
from backend.indicators import RollingSMA, sma_batch, indicator_rows, crossover


def test_tradingview_published_three_period_example():
    # TradingView Moving Averages reference: closes 5,6,7,8,9 -> SMA3 6,7,8.
    assert sma_batch([5,6,7,8,9],3) == [None,None,6,7,8]


@pytest.mark.parametrize('window',[1,2,5,20,200])
def test_batch_incremental_and_pandas_reference(window):
    rng = random.Random(402)
    values = [100+rng.uniform(-20,20) for _ in range(1200)]
    reference = pd.Series(values).rolling(window,min_periods=window).mean().tolist()
    incremental = RollingSMA(window)
    for batch,stream,expected in zip(sma_batch(values,window),map(incremental.update,values),reference):
        if math.isnan(expected): assert batch is None and stream is None
        else:
            assert batch == pytest.approx(expected,abs=1e-11)
            assert stream == pytest.approx(batch,abs=1e-11)


def test_crossovers_match_pandas_shift_reference_and_preview_does_not_commit():
    closes = [10,9,8,7,8,10,12,10,8,7,9,12]
    bars = [dict(timestamp=i*60,close=c,complete=True) for i,c in enumerate(closes)]
    actual = indicator_rows(bars,2,3)
    a,b = pd.Series(closes).rolling(2).mean(),pd.Series(closes).rolling(3).mean()
    up = (a>b)&(a.shift(1)<=b.shift(1))
    down = (a<b)&(a.shift(1)>=b.shift(1))
    expected=['buy' if u else 'sell' if d else None for u,d in zip(up,down)]
    assert [r['crossover'] for r in actual] == expected
    bars[-1]['complete']=False
    preview=indicator_rows(bars,2,3)[-1]
    assert not preview['confirmed'] and preview['crossover']=='buy'
    assert indicator_rows(bars[:-1],2,3)==actual[:-1]
    assert crossover(0,2,1)=='buy' and crossover(0,1,2)=='sell'
    assert crossover(None,2,1) is None


def test_invalid_windows():
    with pytest.raises(ValueError): indicator_rows([],20,5)
