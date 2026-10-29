# TangentCore Routing Insight & Exception Analyzer

A functional, read-only routing investigation app: Python/FastAPI, React/Vite, Tailwind CSS, Pandas/NumPy, Isolation Forest and DBSCAN (NumPy implementations in `backend/ml.py`), and Recharts. No database, AI API, credentials, production connection, or permanent server-side dataset storage.

## Run locally (Windows PowerShell)

Use Python 3.12 and Node.js 22 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
npm.cmd ci
.\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second terminal in this folder:

```powershell
npm.cmd run dev
```

Open http://127.0.0.1:5173. FastAPI API documentation: http://127.0.0.1:8000/docs. No environment variables required.

If Windows denies access to its temporary directory during installation, use a project-local temporary directory:

```powershell
New-Item -ItemType Directory -Force .tmp | Out-Null
$env:TEMP = Join-Path $PWD '.tmp'
$env:TMP = $env:TEMP
python -m pip --python .venv install -r requirements-dev.txt --no-cache-dir
```

## Workspace interface

The responsive workspace includes Overview, Data source, Findings, Record explorer, and Methods & guidance. Start with **Explore synthetic demo** for an analyzed example, or upload your own data. Findings expand to show recommendations and link directly to their source records. CSV and JSON exports remain available from report pages. Charts load on demand. Keyboard focus indicators and reduced-motion preferences are supported.

## Workflow and data contract

1. Upload CSV/JSON or choose **Use synthetic sample**.
2. Inspect preview and quality warnings. Map columns if needed. Confirm failure/success labels.
3. Validate changed settings, then run analysis.
4. Inspect findings and their original source records. Filter the evidence table by route, outcome, exception category, or UTC dates; search original values and sort results. Filters never change analysis totals or exports.
5. Export the full report as JSON or findings as CSV. Exports are generated in the browser; they do not upload reports or persist them on the server.

UTF-8 CSV with unique column headers or a JSON array of flat objects; 1–2,000 records, at most 50 columns and 2,000 characters per cell. Request limit: 1,000,000 bytes, including JSON wrapper on analysis requests. A file near this limit may need reduction after CSV-to-JSON expansion. No mandatory business columns: missing fields disable relevant analyses, with warnings. Empty/malformed records, nested JSON, non-finite JSON numbers, and inconsistent CSV row widths are rejected. No silent row truncation.

Canonical columns (UI can map other names):

| Column | Use |
| --- | --- |
| `event_id` | Warn about repeated identifiers |
| `route` | Recurring failure grouping and evidence filtering |
| `status` | Explicit failure/success mapping |
| `timestamp` | UTC coverage and date filtering; timezone-free timestamps treated as UTC |
| `exception_code`, `exception_message` | Grouping / rule evidence |
| `exception_category` | Preserved supplied classification |
| `latency_ms`, `retry_count` | Numeric anomaly and similarity analysis |
| `source`, `destination` | Preserved optional context |

Original values remain in each report record. Source references are 1-based record positions (CSV header is not counted). Exact duplicate imported key/value rows are excluded, preserving types and missing-key distinctions, with their row references and originals retained under `excluded_records` in JSON reports. Differing rows with the same event ID remain because their attempt ordering/relationship is unknown. Retries are observations, not proven independent attempts. Numeric fields must be finite, nonnegative, at most 1e12; retries must be integers. Invalid/missing numeric cells are excluded only from relevant numeric calculations. Invalid dates are excluded from date coverage/filters. `invalid_records` counts distinct input rows with nonempty invalid numeric/date fields; `retained_invalid_records` counts those still retained after deduplication. These are not additional excluded rows. Missing values and invalid values have separate field-level source references. Duplicate source-column mappings and duplicate JSON keys are rejected. Text fields are trimmed; status matching is case-insensitive. Other label spelling/case differences are not silently merged.

## Methods and interpretation

- **Failures:** defaults `failed,failure,error`; successes `success,completed,ok`. These generic defaults are editable and are not company policy. Unmapped/missing statuses are reported and excluded from failure-rate denominators. Failure rate = explicitly mapped failures / all explicitly mapped outcomes.
- **Recurring failures:** group by available route and exception category/source, falling back to exception code; at least 3 mapped failure observations by default, configurable down to 2. Findings reference failed rows and show the group's known-outcome denominator. Without a route or usable exception information, this analysis is unavailable. Group rates use known outcomes in that group; route-comparison rates use all known outcomes on the route. Identically worded supplied and inferred labels remain separate. Category findings with precisely the same record set as a recurring finding are omitted, but their distribution and record classifications remain available.
- **Isolation Forest:** 100 trees, fixed seed 42, default contamination 0.05. Uses varying latency/retry features and complete numeric rows, with at least 30 observations. Fitted against the full retained dataset, including successes. Reports baseline medians, affected feature ranges, row references, scores and each flagged row's feature values/deviations. Deviations are descriptive comparisons, not model feature attribution. Numeric fields are not zero-filled; only complete rows for selected features are used. Isolation Forest does not require feature standardization for its axis-aligned splits. Positive anomaly score means below the model's fitted decision boundary. Contamination is a cutoff setting, not measured accuracy; some tied/constant distributions produce fewer outliers. Small samples have explicit warnings.
- **DBSCAN:** groups explicitly failed complete numeric observations after StandardScaler normalization. Default epsilon 0.75 and minimum samples 3, configurable. Noise is left ungrouped. Features, scaling parameters and noise count are reported. Numeric similarity does not establish a shared failure cause.
- **Exception categories:** supplied category preferred; otherwise exact structured-code rules (such as ETIMEDOUT, HTTP_429, ECONNREFUSED), followed by word-boundary keyword rules for timeout, authentication/authorization, capacity/rate limit, connectivity, validation. Numeric substrings inside arbitrary text are not treated as structured codes. Rules and evidence are in `backend/analysis.py`. Inferred categories are prefixed `Likely`; unsupported cases remain `Unknown / Unclassified`. These generic categories are not an official taxonomy. A category does not establish failure status. No supervised model is trained without a suitable labelled evaluation dataset; supplied labels are retained directly.
- **Recommendations:** deterministic investigation steps attached to findings, never executed. Findings separate observations, interpretations, reasons flagged and suggested investigation actions, and include affected routes, available time coverage, methods, supporting evidence, row references and limitations. Code/category-specific steps require matching evidence; elevated latency/retry recommendations require flagged measurements above their reported baseline medians. No causal or predictive accuracy claims. Coverage can differ among groups; rates are descriptive and not normalized for workload or time coverage. Absence of a detected pattern is not proof of healthy routing.

Threshold defaults are demonstration settings, visible in the UI and report. Filters change the evidence table only; summary, model baseline, findings and exports always cover the full retained dataset. The sample uses a fixed seed and synthetic IDs/routes/messages. It includes timeout recurrence, rate limits, connectivity failures, supplied labels, unclassified failures, unusual successes, high latency/retries, missing/invalid optional values, three pending statuses, and two distinct observations sharing one event ID. Dataset/report are labelled synthetic. Expected counts: 150 retained, 30 failures, 117 successes, 3 unknown outcomes, 147 known outcomes, 20.408% failure rate, 2 rows with invalid fields. No exact duplicates are present in the sample; tests cover duplicates separately. Downloads of the full JSON report include original records; handle them according to your data policy. CSV findings neutralize spreadsheet-formula prefixes. JSON preserves literal values.

## Tests and build

```powershell
.\.venv\Scripts\python -m pytest -q
npm.cmd run build
node --test tests/export.test.js tests/evidence.test.js
.\.venv\Scripts\python scripts/check_runtime.py
```

Tests use pytest and HTTPX through FastAPI TestClient, covering ingestion errors/limits, counts/denominators, duplicate references, custom mappings, invalid numeric/date values, classification, missing fields, and deterministic synthetic end-to-end analysis.

Verified during this improvement: 27 Python tests passed; 3 Node tests passed; Vite production build passed. Live frontend proxy/API check passed. Browser checks confirmed dashboard totals, all new chart sections, search/sorting that retains repeated IDs, and actual JSON/CSV downloads. Downloaded reports were parsed and all seven findings' evidence references, evidence objects and recommendations matched between formats. There is no configured linter or static type-checker in this JavaScript/Python project; those checks were not claimed or installed. Non-blocking warnings remain: Recharts' bundled JavaScript exceeds Vite's 500 kB chunk advisory, and Starlette TestClient emits an AnyIO deprecation warning.

### Dashboard scope

Input = retained + excluded exact duplicates. Retained = mapped failures + mapped successes + unknown outcomes. Invalid-field records, anomaly counts and cluster counts overlap outcomes and must not be added to those totals. Missing status mapping makes success/failure counts unavailable; unknown outcomes still count all retained observations.

Time trends use observed UTC hourly/daily buckets only, show counts and denominators, and omit records without valid timestamps. Unknown-only buckets have a null rate, not zero. At least two observed buckets are needed to draw a trend chart. No empty buckets or traffic are invented. Route comparisons include observed coverage; charts show up to 20 routes/categories, with complete data in the accompanying tables/JSON. Category distributions include Unknown / Unclassified and all outcomes. Records show classification method/source, normalized numeric measurements, anomaly score/flag and cluster ID; `-1` means DBSCAN noise, null means not evaluated.

## Vercel and GitHub

`vercel.json` builds Vite into `dist` and routes `/api/*` to `api/index.py` (FastAPI). Root `requirements.txt` supplies the exact pinned runtime dependencies. Development dependencies are separate. Vercel's function request/response limit is 4.5 MB and Python bundle limit is 500 MB; this app caps requests at 1 MB, rows at 2,000 and report responses at 4 MB. Scientific dependencies can cause cold starts. DBSCAN is bounded by the row limit, but processing remains subject to available execution/memory limits.

Publishing is intentionally deferred at the user's request until their Git account is switched. No commits, pushes, remote changes or deployments were made during this improvement. When ready, confirm the destination repository/account before publishing (never commit operational datasets):

1. Set the confirmed remote with `git remote add origin <your-repository-url>`, then commit and run `git push -u origin main` only when authorized.
2. Import that repository into Vercel using the root folder. Select Vite if prompted; use `npm run build` and `dist`. Use Python 3.12 for the backend runtime where configurable. Do not enable paid features.
3. Verify `/api/health`, load the synthetic sample, analyze, inspect records and download reports on the deployed URL.

Hosting has not been deployed or verified by this project setup. Linux Python 3.12 binary wheels resolved for all 23 runtime packages; their combined uncompressed wheel contents total 265,299,615 bytes (~253 MiB). This is a preflight estimate, not a Vercel build artifact; runtime/bootstrap, bytecode and application files add overhead. Local Windows benchmark of 2,000 all-failure records: 1.21 seconds warm analysis, 201,105,408 bytes (~192 MiB) peak process working set, 1,407,797-byte report. This is not a worst-case bound or a prediction of Vercel cold-start latency/concurrent memory usage. Vercel build, final bundle, production rewrites, account eligibility, actual memory and execution behavior still require verification after authorized deployment. Free-tier availability, usage quotas, account eligibility and dependency bundle size must be checked in your Vercel account. The application has no authentication and is intended for local use or a controlled demo; review access controls before exposing confidential operational data. Requests have no app-level persistence, but the hosting provider processes network traffic. No raw dataset contents are intentionally logged by application code.

Official hosting references: [Python runtime](https://vercel.com/docs/functions/runtimes/python), [function limits](https://vercel.com/docs/functions/limitations), [configuration](https://vercel.com/docs/project-configuration/vercel-json).

## Layout

`backend/ingestion.py`: parsing, quality and normalization; `backend/analysis.py`: analysis and evidence; `backend/models.py`: typed settings/findings/report; `backend/main.py`: stateless API; `src/main.jsx`: upload, configuration, metrics and drill-down; `src/Overview.jsx`: trend/route/category charts; `src/evidence.js`: filtering/search/sorting; `src/export.js`: safe CSV export; `backend/sample.py`: reproducible scenarios; `backend/summaries.py`: consistent chart aggregates; `scripts/check_runtime.py`: maximum-row local benchmark; `tests/`: automated verification. No external API keys, databases or automatic remediation.
