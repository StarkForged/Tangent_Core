import csv
import io
import json
import math
import pandas as pd
from fastapi import HTTPException

MAX_BYTES = 1_000_000
MAX_ROWS = 2000
FIELDS = ['event_id', 'route', 'timestamp', 'status', 'exception_code', 'exception_message', 'exception_category', 'latency_ms', 'retry_count', 'source', 'destination']


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON keys are ambiguous.')
        result[key] = value
    return result


def validate_records(records):
    if not isinstance(records, list) or not records or len(records) > MAX_ROWS:
        raise HTTPException(422, 'Provide 1–2000 flat records.')
    for row in records:
        if not isinstance(row, dict) or not row or len(row) > 50:
            raise HTTPException(422, 'Each record must be a nonempty object with at most 50 columns.')
        for key, value in row.items():
            if not isinstance(key, str) or not key.strip() or len(key) > 100:
                raise HTTPException(422, 'Column names must contain 1–100 characters.')
            if isinstance(value, (dict, list)) or (isinstance(value, float) and not math.isfinite(value)):
                raise HTTPException(422, 'Use flat scalar values; non-finite numbers are unsupported.')
            if isinstance(value, str) and len(value) > 2000:
                raise HTTPException(422, 'Cell values must not exceed 2000 characters.')
    if len(set().union(*(r.keys() for r in records))) > 50:
        raise HTTPException(422, 'At most 50 columns are supported.')
    return records


def parse_file(data, filename):
    try:
        content = data.decode('utf-8-sig')
        if filename.lower().endswith('.json'):
            records = json.loads(content, object_pairs_hook=unique_object)
        elif filename.lower().endswith('.csv'):
            reader = csv.reader(io.StringIO(content), strict=True)
            headers = next(reader)
            if len(set(headers)) != len(headers):
                raise ValueError('duplicate headers')
            records = []
            for row in reader:
                if len(row) != len(headers):
                    raise ValueError('inconsistent columns')
                records.append(dict(zip(headers, row)))
                if len(records) > MAX_ROWS:
                    raise HTTPException(422, 'At most 2000 records are supported.')
        else:
            raise HTTPException(415, 'Use a UTF-8 CSV or JSON file.')
        return validate_records(records)
    except (UnicodeError, ValueError, StopIteration, csv.Error, RecursionError):
        raise HTTPException(422, 'Malformed or empty file. Use UTF-8 CSV with unique headers or a JSON array of flat objects.')


def prepare(records, config):
    validate_records(records)
    raw = pd.DataFrame(records, dtype=object)
    mapping = {f: config.columns.get(f, f) for f in FIELDS}
    for field, column in config.columns.items():
        if field not in FIELDS or (column and column not in raw.columns):
            raise HTTPException(422, 'Column mapping references an unsupported field or missing column.')
    used = [column for column in mapping.values() if column and column in raw.columns]
    if len(used) != len(set(used)):
        raise HTTPException(422, 'Map each source column to only one field; mark the other field Unused.')
    frame = pd.DataFrame(index=raw.index)
    for field, column in mapping.items():
        if column in raw.columns:
            frame[field] = raw[column].map(lambda v: str(v).strip() if pd.notna(v) else '')
    frame['_row'] = raw.index + 1
    issues = []
    invalid_cells = {}
    missing_cells = {}
    for field in frame.columns:
        if field != '_row':
            count = int(frame[field].eq('').sum())
            missing_cells[field] = frame.loc[frame[field].eq(''), '_row'].tolist()
            if count:
                issues.append(f'{field}: {count} missing values.')
    for field in ['latency_ms', 'retry_count']:
        if field in frame:
            values = pd.to_numeric(frame[field], errors='coerce')
            invalid = values.isna() | ~values.between(0, 1e12)
            if field == 'retry_count':
                invalid |= values.mod(1).ne(0)
            invalid_cells[field] = frame.loc[invalid & frame[field].ne(''), '_row'].tolist()
            frame[field] = values.mask(invalid)
            if invalid.any():
                issues.append(f'{field}: {int(invalid.sum())} missing/invalid values excluded from numeric analysis.')
    if 'timestamp' in frame:
        supplied = frame.timestamp.ne('')
        frame['timestamp'] = pd.to_datetime(frame.timestamp, errors='coerce', utc=True, format='mixed')
        invalid_cells['timestamp'] = frame.loc[supplied & frame.timestamp.isna(), '_row'].tolist()
        if frame.timestamp.isna().any():
            issues.append(f'timestamp: {int(frame.timestamp.isna().sum())} missing/invalid values excluded from time filtering/coverage.')
    # Compare original key/value pairs, preserving type and missing-key distinctions.
    duplicate = pd.Series([json.dumps(row, sort_keys=True, ensure_ascii=False) for row in records]).duplicated()
    if 'event_id' in frame:
        repeated = frame.event_id.ne('') & frame.event_id.duplicated(keep=False)
        if repeated.any():
            issues.append(f'{int(repeated.sum())} rows share event IDs; differing rows retained because attempt ordering is unknown.')
    issues.append('Exact duplicate rows excluded; retries and differing repeated IDs remain separate observations. Independent attempts cannot be established.')
    frame = frame.loc[~duplicate].copy()
    missing = [f for f in FIELDS if f not in frame]
    if 'status' not in frame:
        issues.append('No status mapping: failure counts and recurring failure analysis unavailable.')
    else:
        statuses = frame.status.str.lower()
        unknown = ~statuses.isin(config.failure_statuses + config.success_statuses)
        if unknown.any():
            issues.append(f'{int(unknown.sum())} unmapped/missing statuses: excluded from failure-rate denominators. Review status mappings.')
    if len(frame) < 30:
        issues.append('Small sample: fewer than 30 retained records; anomaly detection unavailable and rates are descriptive only.')
    invalid_rows = sorted(set(r for refs in invalid_cells.values() for r in refs))
    statuses = frame.status.str.lower() if 'status' in frame else pd.Series('', index=frame.index)
    unknown = ~statuses.isin(config.failure_statuses + config.success_statuses)
    return frame, {'input_records': len(raw), 'analyzed_records': len(frame), 'excluded_exact_duplicates': int(duplicate.sum()), 'excluded_row_references': (raw.index[duplicate] + 1).tolist(), 'invalid_records': len(invalid_rows), 'invalid_row_references': invalid_rows, 'retained_invalid_records': len(set(invalid_rows) & set(frame._row)), 'invalid_fields': invalid_cells, 'missing_values': missing_cells, 'unmapped_status_count': int(unknown.sum()), 'unmapped_status_values': sorted(statuses[unknown].unique().tolist()), 'missing_fields': missing, 'warnings': issues}
