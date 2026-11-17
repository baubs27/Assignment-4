"""Closing-price SMA and crossover; no signal is actionable before bar completion."""
import math
from collections import deque


def validate_windows(fast, slow):
    if not (isinstance(fast, int) and isinstance(slow, int) and 1 <= fast < slow <= 500):
        raise ValueError('SMA windows must satisfy 1 <= fast < slow <= 500')


def sma_batch(values, window):
    if not isinstance(window, int) or not 1 <= window <= 500:
        raise ValueError('Invalid SMA window')
    return [None if i + 1 < window else math.fsum(values[i-window+1:i+1]) / window
            for i in range(len(values))]


class RollingSMA:
    def __init__(self, window):
        self.window = window
        self.values = deque(maxlen=window)

    def update(self, value):
        value = float(value)
        if not math.isfinite(value) or value <= 0:
            raise ValueError('Closing prices must be finite and positive')
        self.values.append(value)
        return math.fsum(self.values) / self.window if len(self.values) == self.window else None


def crossover(previous, fast, slow):
    if previous is None or fast is None or slow is None:
        return None
    difference = fast - slow
    if previous <= 0 < difference:
        return 'buy'
    if previous >= 0 > difference:
        return 'sell'
    return None


def indicator_rows(candles, fast=5, slow=20):
    validate_windows(fast, slow)
    short, long = RollingSMA(fast), RollingSMA(slow)
    previous, result = None, []
    for c in candles:
        # An unfinished value is displayed as a preview, without committing state.
        if c['complete']:
            a, b = short.update(c['close']), long.update(c['close'])
        else:
            a_values = [*short.values, c['close']][-fast:]
            b_values = [*long.values, c['close']][-slow:]
            a = math.fsum(a_values) / fast if len(a_values) == fast else None
            b = math.fsum(b_values) / slow if len(b_values) == slow else None
        signal = crossover(previous, a, b)
        result.append(dict(timestamp=c['timestamp'], fast=a, slow=b,
                           crossover=signal, confirmed=bool(c['complete'])))
        if c['complete'] and a is not None and b is not None:
            previous = a - b
    return result
