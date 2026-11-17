from typing import Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from .feed import SYMBOLS
from .candles import INTERVALS


class Parameters(BaseModel):
    symbol: str = 'AAPL'
    source: Literal['demo','recorded','history'] = 'demo'
    interval: str = '1m'
    fast: int = Field(5,ge=1,le=499)
    slow: int = Field(20,ge=2,le=500)
    cash: float = Field(10000,ge=1,le=1e9,allow_inf_nan=False)
    quantity: int = Field(10,ge=1,le=1000000)
    fee: float = Field(0,ge=0,le=1000,allow_inf_nan=False)
    slippage_bps: float = Field(0,ge=0,le=1000,allow_inf_nan=False)
    start: float | None = Field(None,allow_inf_nan=False)
    end: float | None = Field(None,allow_inf_nan=False)
    history_id: str | None = None

    @model_validator(mode='after')
    def validate_selection(self):
        if self.symbol not in SYMBOLS or self.interval not in INTERVALS: raise ValueError('Invalid symbol or interval')
        if self.fast >= self.slow: raise ValueError('Fast SMA must be shorter than slow SMA')
        if self.start is not None and self.end is not None and self.start > self.end: raise ValueError('Start must not follow end')
        return self


class HistoryRequest(BaseModel):
    symbol: Literal['AAPL','MSFT','BTC-USD'] = 'AAPL'
    period: Literal['1mo','3mo','6mo','1y','2y'] = '1y'


def router(service):
    api = APIRouter(prefix='/api/research')

    @api.get('/runs')
    def runs(): return {'runs':service.runs()}

    @api.get('/runs/{run_id}')
    def run(run_id: str):
        try: return service.get(run_id)
        except KeyError: raise HTTPException(404,'Simulation not found')

    @api.get('/history')
    def history(): return {'history':service.history()}

    @api.post('/history')
    def download(body: HistoryRequest):
        try: return service.download_history(body.symbol,body.period)
        except Exception as exc: raise HTTPException(502,f'Historical feed unavailable ({type(exc).__name__}). No data was fabricated.')

    @api.post('/backtest')
    def backtest(body: Parameters):
        try: return service.backtest(body.model_dump())
        except ValueError as exc: raise HTTPException(400,str(exc))

    @api.post('/paper')
    def paper(body: Parameters):
        if body.source=='history': raise HTTPException(400,'Paper streaming uses demo or recorded Yahoo observations; use backtest for daily history.')
        return service.start_paper(body.model_dump())

    @api.post('/paper/{run_id}/pause')
    def pause(run_id: str):
        try: return service.pause(run_id)
        except KeyError: raise HTTPException(404,'Simulation not found')
        except ValueError as exc: raise HTTPException(400,str(exc))

    @api.post('/paper/{run_id}/resume')
    def resume(run_id: str):
        try: return service.resume(run_id)
        except KeyError: raise HTTPException(404,'Simulation not found')
        except ValueError as exc: raise HTTPException(400,str(exc))

    return api
