"""Reproducible local runtime check, not a claim about Vercel cold starts."""
import json
import sys
import time
from pathlib import Path
from importlib import metadata

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.analysis import analyze
from backend.models import AnalysisRequest
from backend.sample import sample_records

started = time.perf_counter()
sample = sample_records()
rows = [{**sample[i % len(sample)], 'event_id': f'BENCH-{i}', 'status': 'failed'} for i in range(2000)]
report = analyze(AnalysisRequest(records=rows, synthetic=True))
elapsed = time.perf_counter() - started
peak_rss = None
if sys.platform == 'win32':
    import ctypes
    class MemoryCounters(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('faults', ctypes.c_ulong)] + [(name, ctypes.c_size_t) for name in ['peak_rss', 'rss', 'peak_paged', 'paged', 'peak_nonpaged', 'nonpaged', 'pagefile', 'peak_pagefile']]
    counters = MemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    if ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(-1), ctypes.byref(counters), counters.cb):
        peak_rss = counters.peak_rss
packages = ['fastapi', 'starlette', 'pydantic', 'pydantic-core', 'numpy', 'pandas', 'scipy', 'scikit-learn', 'uvicorn']
sizes = {}
for name in packages:
    dist = metadata.distribution(name)
    sizes[name] = {'version': dist.version, 'installed_bytes': sum(p.stat().st_size for f in dist.files or [] if (p := Path(dist.locate_file(f))).is_file())}
print(json.dumps({'scope': 'Local Windows warm analysis; installed package sizes are not the Linux deployment bundle.', 'records': len(rows), 'analysis_seconds': round(elapsed, 3), 'peak_process_working_set_bytes': peak_rss, 'report_bytes': len(report.model_dump_json().encode()), 'findings': len(report.findings), 'major_packages': sizes}, indent=2))
