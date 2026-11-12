"""Constructed teaching data. Never enters the Yahoo/live dataset."""
import math
from .store import Store


def seed_demo(store: Store):
    if store.deliveries('demo', 'AAPL'):
        return
    start = 1794236400  # 2026-11-09 15:00 UTC; intentionally fixed, not current quotes.
    total = 100000
    rows = []
    for i in range(91):
        for j, offset in enumerate([5, 22, 48]):
            total += 35 + (i * 17 + j * 23) % 180
            price = round(100 + i * .025 + math.sin(i / 5) * 1.3 + math.sin(i * 2 + j) * .24, 2)
            t = start + i * 60 + offset
            row = dict(dataset='demo', source='Constructed teaching fixture', symbol='AAPL',
                source_time=t, price=price, cumulative_volume=total,
                raw={'fixture': True, 'sequence': i * 3 + j}, receipt_time=t + .2)
            rows.append(row)
    deliveries = []
    for i, row in enumerate(rows):
        if i == 100:
            continue  # deliver it late after the next observation
        deliveries.append(row)
        if i == 101:
            deliveries.append({**rows[100], 'receipt_time': row['receipt_time'] + .1})
        if i == 40:
            deliveries.append({**row, 'receipt_time': row['receipt_time'] + .1})
    # Explicit identity/revision, in contrast to ambiguous Yahoo same-time ticks.
    base = dict(dataset='demo', source='Constructed teaching fixture', symbol='AAPL',
        source_time=start + 91 * 60 + 5, cumulative_volume=total + 100,
        event_key='demo-correction', raw={'fixture': True})
    deliveries.append(dict(**base, price=102, revision=0, receipt_time=start + 91 * 60 + 5.2))
    deliveries.append(dict(**base, price=102.5, revision=1, receipt_time=start + 91 * 60 + 10.2))
    with store.connect() as db:
        for row in deliveries:
            store.record(**row, connection=db)
