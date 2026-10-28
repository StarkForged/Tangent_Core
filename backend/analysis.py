import re
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from .ingestion import prepare
from .models import Finding, Report

RULES = [('Timeout', ('timeout', 'timed out'), 'Inspect upstream availability, timeout logs and documented retry configuration for these records.'), ('Authentication / authorization', ('unauthorized', 'forbidden', 'authentication'), 'Review access-denial logs and credential validity.'), ('Capacity / rate limit', ('rate limit', 'too many requests', 'capacity'), 'Compare request volumes with documented capacity limits.'), ('Connectivity', ('connection', 'dns', 'unreachable'), 'Review network and endpoint availability logs.'), ('Validation', ('invalid', 'validation', 'malformed'), 'Compare affected payload fields with the documented schema.')]
CODE_CATEGORIES = {code: category for category, codes in [
    ('Timeout', ['ETIMEDOUT', 'TIMEOUT', 'HTTP_408', '408', 'HTTP_504', '504']),
    ('Authentication / authorization', ['HTTP_401', '401', 'HTTP_403', '403']),
    ('Capacity / rate limit', ['HTTP_429', '429']),
    ('Connectivity', ['ECONNREFUSED', 'ECONNRESET', 'ENOTFOUND']),
    ('Validation', ['HTTP_422', '422', 'VALIDATION_ERROR'])] for code in codes}


def classify(row):
    if row.get('exception_category', ''):
        return row['exception_category'], 'Supplied category label; not independently verified.', 'supplied_label'
    code = str(row.get('exception_code', '')).upper()
    if code in CODE_CATEGORIES:
        return 'Likely ' + CODE_CATEGORIES[code], f'Exact code rule: {code!r}; generic interpretation, not a verified cause.', 'code_rule'
    text = (str(row.get('exception_code', '')) + ' ' + str(row.get('exception_message', ''))).lower().replace('_', ' ')
    for category, words, _ in RULES:
        matched = next((w for w in words if re.search(r'\b' + re.escape(w) + r'\b', text)), None)
        if matched:
            return 'Likely ' + category, f'Inferred from text match: {matched!r}; demonstration taxonomy.', 'keyword_rule'
    return 'Unknown / Unclassified', 'No supplied label or supported rule match.', 'unclassified'


def period(rows: pd.DataFrame) -> dict | None:
    values = rows.timestamp.dropna() if 'timestamp' in rows else []
    return {'start': min(values).isoformat(), 'end': max(values).isoformat()} if len(values) else None


def category_steps(category: str, method: str) -> list[str]:
    if method not in ['supplied_label', 'unclassified']:
        return [next((r[2] for r in RULES if category == 'Likely ' + r[0]), 'Review associated exception records.')]
    return ['Review supplied category definitions and associated records.' if method == 'supplied_label' else 'Review original error codes/messages; request additional diagnostic context before assigning a cause.']


def analyze(request):
    config = request.config
    df, quality = prepare(request.records, config)
    status = df['status'].str.lower() if 'status' in df else pd.Series('', index=df.index)
    failure = status.isin(config.failure_statuses)
    success = status.isin(config.success_statuses)
    known = failure | success
    categories = df.apply(lambda row: classify(row.to_dict()), axis=1)
    df['_category'] = categories.map(lambda x: x[0])
    df['_category_evidence'] = categories.map(lambda x: x[1])
    df['_classification_method'] = categories.map(lambda x: x[2])
    # Keep supplied labels distinct from identically worded inferred labels.
    df['_category_source'] = df['_classification_method'].map(lambda x: 'supplied' if x == 'supplied_label' else 'inferred' if x != 'unclassified' else 'unknown')
    findings = []
    common = ['Observational evidence only; no root cause or predictive accuracy is established.', 'Coverage may be incomplete; group rates are not adjusted for different time windows.']

    def add(kind, title, rows, evidence, method, recommendations, limitations=None):
        evidence['classification_methods'] = sorted(rows._classification_method.unique().tolist())
        findings.append(Finding(finding_id=f'F{len(findings)+1:03}', finding_type=kind, title=title, observation=f'{len(rows)} retained observations: {title}.', affected_routes=sorted(rows.route[rows.route.ne('')].unique().tolist()) if 'route' in rows else [], observed_period=period(rows), reason_flagged=evidence.get('criterion', method), interpretation='A pattern for human investigation; neither a confirmed root cause nor a count of independent incidents.', record_count=len(rows), source_record_references=rows['_row'].tolist(), evidence=evidence, detection_method=method, recommendations=recommendations, limitations=common + (limitations or [])))

    group_keys = ['route'] if 'route' in df and df.route.ne('').any() else []
    if df._category.ne('Unknown / Unclassified').any():
        group_keys += ['_category', '_category_source']
    elif 'exception_code' in df and df.exception_code.ne('').any():
        group_keys += ['exception_code']
    if group_keys:
        for key, group in df.groupby(group_keys, dropna=False, sort=True):
            failed = group.loc[failure.loc[group.index]]
            if len(failed) >= config.recurring_min:
                values = key if isinstance(key, tuple) else (key,)
                denominator = int(known.loc[group.index].sum())
                recommendations = ['Review referenced exception messages and attempt IDs.', 'Compare affected routes and relevant service configuration over the same time window.']
                recommendations += category_steps(failed._category.iloc[0], failed._classification_method.iloc[0])
                add('recurring_failure', 'Recurring failures: ' + ' / '.join(str(v) or '(missing)' for v in values), failed,
                    {'group': dict(zip([k.lstrip('_') for k in group_keys], values)), 'failure_count': len(failed), 'known_outcome_denominator': denominator, 'failure_rate': len(failed)/denominator, 'denominator_scope': 'Same group, not all route traffic. Use route comparisons for overall route rates.', 'minimum_count': config.recurring_min, 'criterion': f'{len(failed)} mapped failures meet minimum recurrence count {config.recurring_min}.'},
                    'Count explicitly mapped failures by available route and exception category/source, falling back to code.', recommendations, ['Repeated observations can include retries or repeated events; independent incident counts are unknown.'])
    else:
        quality['warnings'].append('Recurring group analysis unavailable: map route or exception fields.')

    features = [f for f in ['latency_ms', 'retry_count'] if f in df and df[f].nunique() > 1]
    complete = df.dropna(subset=features) if features else df.iloc[:0]
    methods = {'recurring_group_keys': group_keys, 'numeric_features': features, 'numeric_complete_records': len(complete), 'numeric_excluded_records': len(df)-len(complete), 'isolation_forest': 'Skipped: needs >=30 complete rows and a varying numeric feature.', 'dbscan': 'Skipped: needs sufficient failed rows with complete, varying numeric features.'}
    anomaly_rows = set()
    anomaly_scores = {}
    cluster_by_row = {}
    if features and len(complete) >= 30:
        model = IsolationForest(n_estimators=100, contamination=config.contamination, random_state=42, n_jobs=1)
        flags = model.fit_predict(complete[features]) == -1
        scores = -model.decision_function(complete[features])
        medians = complete[features].median()
        methods['isolation_forest'] = {'features': features, 'baseline': 'All retained records with complete numeric features, including successes.', 'contamination': config.contamination, 'seed': 42, 'meaning': 'Unusual numeric combinations; not confirmed failures. Higher score is more unusual; zero is the fitted decision boundary.'}
        anomalies = complete.loc[flags]
        anomaly_rows = set(anomalies._row.tolist())
        anomaly_scores = dict(zip(complete._row.tolist(), scores.tolist()))
        if len(anomalies):
            steps = ['Compare referenced values with baseline medians and surrounding events.', 'Check workload mix and measurement quality before treating outliers as faults.']
            for feature in features:
                if (anomalies[feature] > medians[feature]).any():
                    steps.append('Inspect latency measurements at affected timestamps against the reported baseline.' if feature == 'latency_ms' else 'Inspect elevated retry counts and associated error records against the reported baseline.')
            add('unusual_pattern', 'Unusual latency / retry observations', anomalies, {'criterion': 'Isolation Forest decision_function < 0 (reported anomaly score > 0).', 'contamination': config.contamination, 'baseline_medians': medians.to_dict(), 'baseline_records': len(complete), 'feature_ranges': {f: {'min': float(anomalies[f].min()), 'max': float(anomalies[f].max())} for f in features}, 'scores_by_row': dict(zip(anomalies._row.astype(str), scores[flags].tolist())), 'measurements_by_row': {str(r._row): {f: {'value': float(r[f]), 'delta_from_median': float(r[f]-medians[f])} for f in features} for _, r in anomalies.iterrows()}}, 'Isolation Forest on available numeric features; seed 42, 100 trees.', steps, ['Contamination controls the outlier cutoff; this is not a measured error rate.', 'Feature deviations describe observations, not causal feature attribution.'])
    failed_complete = complete.loc[failure.loc[complete.index]]
    if features and len(failed_complete) >= config.dbscan_min_samples and failed_complete[features].nunique().max() > 1:
        scaler = StandardScaler()
        matrix = scaler.fit_transform(failed_complete[features])
        labels = DBSCAN(eps=config.dbscan_eps, min_samples=config.dbscan_min_samples, n_jobs=1).fit_predict(matrix)
        cluster_by_row = dict(zip(failed_complete._row.tolist(), labels.tolist()))
        methods['dbscan'] = {'features': features, 'scaling': 'StandardScaler fitted to failed complete rows', 'mean': scaler.mean_.tolist(), 'scale': scaler.scale_.tolist(), 'eps': config.dbscan_eps, 'min_samples': config.dbscan_min_samples, 'noise_records': int((labels == -1).sum())}
        for label in sorted(set(labels) - {-1}):
            group = failed_complete.loc[labels == label]
            add('failure_cluster', f'Similar failure measurements: cluster {label}', group, {'cluster': int(label), 'feature_medians': group[features].median().to_dict(), 'failed_complete_records': len(failed_complete), 'eps': config.dbscan_eps, 'min_samples': config.dbscan_min_samples, 'criterion': f'Density-connected numeric failure measurements at eps={config.dbscan_eps}, min_samples={config.dbscan_min_samples} after standardization.'}, 'DBSCAN on standardized numeric failure measurements.', ['Review whether these records share exception codes, destinations, or workload conditions.'], ['Clusters indicate numeric similarity, not a shared cause. Noise is left ungrouped.'])
    for (category, source), group in df.groupby(['_category', '_category_source'], sort=True):
        if category != 'Unknown / Unclassified':
            if any(f.finding_type == 'recurring_failure' and f.source_record_references == group._row.tolist() for f in findings):
                continue  # Same category evidence already present in recurrence; charts retain it.
            add('exception_category', category, group, {'category': category, 'source': source, 'rule_evidence': sorted(group._category_evidence.unique().tolist())}, 'Supplied category preferred; exact code rules before keyword fallback.', category_steps(category, group._classification_method.iloc[0]), ['Category does not establish failure status; rules are generic and may misclassify ambiguous text.'])
    records = []
    for index, row in df.iterrows():
        records.append({'row_reference': int(row['_row']), 'original': request.records[index], 'route': row.get('route', ''), 'timestamp': row.timestamp.isoformat() if 'timestamp' in row and pd.notna(row.timestamp) else None, 'status': row.get('status', ''), 'outcome': 'failure' if failure.loc[index] else 'success' if success.loc[index] else 'unknown', 'exception_category': row['_category'], 'classification_evidence': row['_category_evidence'], 'classification_method': row['_classification_method'], 'classification_source': row['_category_source'], 'is_anomaly': bool(row._row in anomaly_rows) if row._row in anomaly_scores else None, 'anomaly_score': anomaly_scores.get(row._row), 'failure_cluster': cluster_by_row.get(row._row), 'numeric_measurements': {f: float(row[f]) if pd.notna(row[f]) else None for f in ['latency_ms', 'retry_count'] if f in row}})
    timestamps = df.timestamp.dropna() if 'timestamp' in df else pd.Series(dtype='datetime64[ns, UTC]')
    summary = {'analyzed_records': len(df), 'failure_count': int(failure.sum()) if 'status' in df else None, 'success_count': int(success.sum()) if 'status' in df else None, 'known_outcome_denominator': int(known.sum()), 'failure_rate': float(failure.sum()/known.sum()) if known.any() else None, 'observed_period': {'start': timestamps.min().isoformat(), 'end': timestamps.max().isoformat()} if len(timestamps) else None, 'unknown_category_count': int(df._category.eq('Unknown / Unclassified').sum())}
    summary.update(input_records=len(request.records), excluded_exact_duplicates=quality['excluded_exact_duplicates'], invalid_records=quality['invalid_records'], retained_invalid_records=quality['retained_invalid_records'], unknown_outcome_count=int((~known).sum()), anomalous_records=len(anomaly_rows) if anomaly_scores else None, cluster_count=len(set(cluster_by_row.values())-{-1}) if cluster_by_row else None, clustering_noise_records=sum(v == -1 for v in cluster_by_row.values()) if cluster_by_row else None)
    from .summaries import distributions
    return Report(synthetic=request.synthetic, config=config, quality=quality, summary=summary, methods=methods, findings=findings, records=records, distributions=distributions(records, config.trend_interval), excluded_records=[{'row_reference': r, 'original': request.records[r-1], 'reason': 'Exact duplicate'} for r in quality['excluded_row_references']])
