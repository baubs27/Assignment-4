"""Causal long-only simulator. Decimal accounting; shared strategy for all runs."""
import hashlib
import json
from decimal import Decimal
from .candles import build_candles, INTERVALS
from .indicators import RollingSMA, crossover, validate_windows
from .store import project


def D(value):
    return Decimal(str(value))


def number(value, places=8):
    return round(float(value), places)


class Broker:
    def __init__(self, cash=10000, fee=0, slippage_bps=0):
        if not (D(cash).is_finite() and D(cash)>0 and D(fee).is_finite() and D(fee)>=0
                and D(slippage_bps).is_finite() and 0<=D(slippage_bps)<=1000):
            raise ValueError('Invalid cash, fee, or slippage')
        self.initial = D(cash)
        self.cash, self.qty, self.cost, self.realized, self.fees = self.initial, D(0), D(0), D(0), D(0)
        self.fee, self.slippage = D(fee), D(slippage_bps) / D(10000)
        self.mark = None
        self.orders, self.fills, self.curve = [], [], []

    def submit(self, side, qty, at, eligible_at, decision_receipt=0):
        if side not in ['buy', 'sell'] or D(qty) <= 0:
            raise ValueError('Invalid order')
        order = dict(id=len(self.orders)+1, side=side, quantity=number(qty),
            submitted_at=at, eligible_at=eligible_at, decision_receipt=decision_receipt,
            status='pending', reason='Awaiting next eligible price')
        self.orders.append(order)
        return order

    def cancel(self, reason):
        for o in self.orders:
            if o['status'] == 'pending':
                o.update(status='cancelled', reason=reason)

    def fill_pending(self, price, at, receipt_id=None):
        price = D(price)
        if not price.is_finite() or price <= 0:
            raise ValueError('Invalid execution price')
        for o in self.orders:
            if o['status'] != 'pending' or at < o['eligible_at']:
                continue
            if receipt_id is not None and receipt_id <= o['decision_receipt']:
                continue
            qty = D(o['quantity'])
            fill_price = price * (1 + self.slippage if o['side'] == 'buy' else 1 - self.slippage)
            proceeds, realized = qty * fill_price, D(0)
            if o['side'] == 'buy':
                if proceeds + self.fee > self.cash:
                    o.update(status='rejected', reason='Insufficient simulated cash'); continue
                self.cash -= proceeds + self.fee
                self.cost += proceeds + self.fee
                self.qty += qty
            else:
                if qty > self.qty:
                    o.update(status='rejected', reason='Insufficient simulated position'); continue
                if self.cash + proceeds - self.fee < 0:
                    o.update(status='rejected', reason='Insufficient simulated cash for fee'); continue
                basis = self.cost * qty / self.qty
                self.cash += proceeds - self.fee
                self.cost -= basis
                self.qty -= qty
                realized = proceeds - self.fee - basis
                self.realized += realized
                if self.qty == 0:
                    self.cost = D(0)
            self.fees += self.fee
            o.update(status='filled', reason='Simulated fill', filled_at=at)
            self.fills.append(dict(id=len(self.fills)+1, order_id=o['id'], side=o['side'],
                quantity=number(qty), price=number(fill_price), fee=number(self.fee),
                timestamp=at, receipt_id=receipt_id, realized_pnl=number(realized)))

    def account(self):
        market_value = self.qty * self.mark if self.mark is not None else self.cost
        equity = self.cash + market_value
        peak, drawdown = self.initial, D(0)
        for point in self.curve:
            value = D(point['equity'])
            peak = max(peak, value)
            drawdown = max(drawdown, (peak-value)/peak if peak else D(0))
        return dict(initial_cash=number(self.initial, 2), cash=number(self.cash, 2),
            quantity=number(self.qty), average_cost=number(self.cost/self.qty) if self.qty else 0,
            mark=number(self.mark) if self.mark is not None else None,
            market_value=number(market_value, 2), equity=number(equity, 2),
            realized_pnl=number(self.realized, 2), unrealized_pnl=number(market_value-self.cost, 2),
            total_pnl=number(equity-self.initial, 2), fees=number(self.fees, 2),
            return_pct=number((equity/self.initial-1)*100, 4),
            max_drawdown_pct=number(drawdown*100, 4), fills=len(self.fills),
            pending_orders=sum(o['status']=='pending' for o in self.orders))

    def mark_to_market(self, price, at):
        if not D(price).is_finite() or D(price)<=0: raise ValueError('Invalid market mark')
        self.mark = D(price)
        self.curve.append(dict(timestamp=at, equity=number(self.cash+self.qty*self.mark),
                               cash=number(self.cash), quantity=number(self.qty)))


class Strategy:
    def __init__(self, config):
        self.config = config
        validate_windows(config['fast'], config['slow'])
        self.short, self.long = RollingSMA(config['fast']), RollingSMA(config['slow'])
        self.previous = None
        self.last_bar = -1
        self.last_source = -1
        self.last_clock = -1
        self.broker = Broker(config['cash'], config['fee'], config['slippage_bps'])
        self.signals, self.decisions = [], []

    def close(self, c, at, receipt_id=0, trade=True):
        if not c['complete'] or c['timestamp'] <= self.last_bar:
            return
        self.last_bar = c['timestamp']
        a, b = self.short.update(c['close']), self.long.update(c['close'])
        signal = crossover(self.previous, a, b)
        self.decisions.append(dict(**c, fast=a, slow=b,
            crossover=signal, known_at=at, receipt_id=receipt_id))
        if a is not None and b is not None:
            self.previous = a-b
        if signal and trade:
            self.signals.append(dict(timestamp=c['timestamp'], side=signal, known_at=at))
            self.broker.cancel('Superseded by a newer crossover')
            quantity = self.config['quantity'] if signal == 'buy' else self.broker.qty
            if (signal == 'buy' and not self.broker.qty) or (signal == 'sell' and self.broker.qty):
                self.broker.submit(signal, quantity, at,
                    max(at, c['timestamp']+INTERVALS[self.config['interval']]), receipt_id)

    def state(self):
        b = self.broker
        return dict(config=self.config, short=list(self.short.values), long=list(self.long.values),
            previous=self.previous, last_bar=self.last_bar, last_source=self.last_source, last_clock=self.last_clock,
            decimals={k:str(getattr(b,k)) for k in ['initial','cash','qty','cost','realized','fees','fee','slippage']},
            mark=str(b.mark) if b.mark is not None else None,
            orders=b.orders, fills=b.fills, curve=b.curve, signals=self.signals, decisions=self.decisions)

    @classmethod
    def restore(cls, state):
        s = cls(state['config'])
        s.short.values.extend(state['short']); s.long.values.extend(state['long'])
        for key in ['previous','last_bar','last_source','last_clock','signals','decisions']:
            setattr(s, key, state[key])
        for key,value in state['decimals'].items(): setattr(s.broker,key,D(value))
        s.broker.mark = D(state['mark']) if state['mark'] is not None else None
        for key in ['orders','fills','curve']: setattr(s.broker,key,state[key])
        return s

    def result(self):
        return dict(account=self.broker.account(), orders=self.broker.orders, fills=self.broker.fills,
                    equity_curve=self.broker.curve, signals=self.signals, decisions=self.decisions)


def receipt_step(strategy, seen, row=None, clock=None):
    """Only previously submitted orders may use this receipt; decisions come afterward."""
    if row is not None:
        clock = max(row['receipt_time'], clock or row['receipt_time'],strategy.last_clock)
        effective_ids = {r['id'] for r in project([*seen,row])}
        if not row['duplicate'] and row['id'] in effective_ids:
            strategy.broker.fill_pending(row['price'], row['source_time'], row['receipt_id'])
        seen.append(row)
    if clock is None: return
    clock = max(clock,strategy.last_clock)
    strategy.last_clock = clock
    for c in build_candles(seen, strategy.config['interval'], clock):
        strategy.close(c, clock, row['receipt_id'] if row else (seen[-1]['receipt_id'] if seen else 0))
    if seen:
        latest = project(seen)[-1]
        if latest['source_time'] >= strategy.last_source:
            strategy.last_source = latest['source_time']
            strategy.broker.mark_to_market(latest['price'], clock)


def simulate_receipts(rows, config):
    s, seen, clock = Strategy(config), [], None
    for row in rows:
        clock = max(clock or row['receipt_time'], row['receipt_time'])
        receipt_step(s, seen, row, clock)
    s.broker.cancel('End of recorded sample; no future execution price')
    return s.result()


def simulate_bars(bars, config):
    s, last_time = Strategy(config), -1
    for c in bars:
        if not c['complete']: continue
        if c['timestamp'] <= last_time: raise ValueError('Historical bars must be strictly ordered')
        last_time = c['timestamp']
        s.broker.fill_pending(c['open'], c['timestamp'])
        at = c['timestamp'] + INTERVALS[config['interval']]
        s.broker.mark_to_market(c['close'], at)
        s.close(c, at)
    s.broker.cancel('End of historical sample; no next open')
    return s.result()


def source_digest(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',',':')).encode()).hexdigest()
