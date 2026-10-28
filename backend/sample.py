"""Deterministic demonstration observations; never operational evidence."""
import numpy as np
import pandas as pd


def sample_records() -> list[dict]:
    rng = np.random.default_rng(42)
    rows = []
    for i in range(150):
        row = {'event_id': f'SYN-{i+1:04}', 'route': f'SYN-route-{i%3+1}',
               'timestamp': (pd.Timestamp('2026-01-01', tz='UTC') + pd.Timedelta(minutes=i*5)).isoformat(),
               'status': 'success', 'exception_code': '', 'exception_message': '',
               'latency_ms': int(rng.integers(40, 150)), 'retry_count': 0}
        if i % 5 == 0:
            row.update(status='failed', latency_ms=int(rng.integers(250, 450)), retry_count=3)
            if i < 75:
                row.update(route='SYN-route-timeout', exception_code='ETIMEDOUT', exception_message='Synthetic upstream timeout')
            elif i < 100:
                row.update(exception_code='HTTP_429', exception_message='Synthetic rate limit')
            elif i < 120:
                row.update(exception_category='Synthetic operator access label', exception_code='HTTP_403')
            elif i < 135:
                row.update(exception_code='ECONNREFUSED', exception_message='Synthetic connection refused')
            else:
                row.update(exception_message='Synthetic unspecified error Z9')
        if i in [20, 60, 100, 140]:
            row.update(latency_ms=10000+i*100, retry_count=15+i//20)
        if i in [21, 61]:  # Unusual successes are not confirmed routing failures.
            row.update(latency_ms=15000+i*100, retry_count=18)
        if i in [7, 17, 27]:
            row['status'] = 'pending'
        if i in [12, 22]:
            row['latency_ms'] = None
        if i == 32:
            row['timestamp'] = None
        if i == 42:
            row['latency_ms'] = 'invalid measurement'
        if i == 52:
            row['timestamp'] = 'invalid timestamp'
        if i == 80:
            row['event_id'] = 'SYN-0076'  # Same ID, different time/measurement: retain.
        rows.append(row)
    return rows
