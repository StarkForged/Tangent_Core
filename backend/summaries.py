"""Counts use disjoint outcomes; time buckets are observed, never invented."""
import pandas as pd


def distributions(records: list[dict], interval: str) -> dict:
    frame = pd.DataFrame(records)

    def counts(group):
        failures = int(group.outcome.eq('failure').sum())
        successes = int(group.outcome.eq('success').sum())
        known = failures + successes
        return {'records': len(group), 'failure_count': failures, 'success_count': successes,
                'unknown_count': int(group.outcome.eq('unknown').sum()), 'known_outcome_denominator': known,
                'failure_rate_percent': failures / known * 100 if known else None}

    routes = [{'route': route or '(missing route)', **counts(group), 'observed_start': min(group.timestamp.dropna()) if group.timestamp.notna().any() else None, 'observed_end': max(group.timestamp.dropna()) if group.timestamp.notna().any() else None} for route, group in frame.groupby('route', sort=True)] if frame.route.ne('').any() else []
    categories = [{'category': category, 'source': source, **counts(group)} for (category, source), group in frame.groupby(['exception_category', 'classification_source'], sort=True)]
    dated = frame.loc[frame.timestamp.notna()].copy()
    trend = []
    if len(dated):
        dated['bucket'] = pd.to_datetime(dated.timestamp, utc=True).dt.floor('h' if interval == 'hour' else 'D')
        trend = [{'timestamp': bucket.isoformat(), **counts(group)} for bucket, group in dated.groupby('bucket', sort=True)]
    return {'routes': routes, 'categories': categories, 'trend': trend, 'trend_interval': interval,
            'trend_excluded_records': len(frame)-len(dated),
            'trend_note': 'Observed UTC buckets only; gaps are not zero activity. Rates exclude unknown outcomes. Small counts and unequal coverage limit comparisons.'}
