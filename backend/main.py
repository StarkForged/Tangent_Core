import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from .models import AnalysisRequest, Config
from .ingestion import parse_file, prepare, MAX_BYTES
from .analysis import analyze
from .sample import sample_records

app = FastAPI(title='TangentCore Routing Insight & Exception Analyzer', version='1.1.0')


@app.middleware('http')
async def bounds(request: Request, call_next):
    if request.method == 'POST':
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_BYTES:
                return JSONResponse({'detail': 'Request exceeds the 1 MB limit.'}, status_code=413, headers={'Cache-Control': 'no-store'})
        request._body = bytes(body)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    # Do not echo raw uploaded values or non-serializable validation context.
    errors = [{'field': '.'.join(map(str, e['loc'])), 'message': e['msg']} for e in exc.errors()]
    return JSONResponse({'detail': 'Invalid request or settings.', 'errors': errors}, status_code=422)


@app.exception_handler(Exception)
async def unexpected(request, exc):
    logging.getLogger('tangentcore').error('Request failed: %s', type(exc).__name__)
    return JSONResponse({'detail': 'Analysis failed. Check the file and settings, then retry.'}, status_code=500)


@app.get('/api/health')
def health():
    return {'status': 'ok', 'version': '1.1.0'}


@app.post('/api/preview')
async def preview(request: Request, filename: str):
    records = parse_file(await request.body(), filename)
    _, quality = prepare(records, Config())
    return {'records': records, 'quality': quality, 'columns': list(dict.fromkeys(k for row in records for k in row)), 'synthetic': False}


@app.post('/api/validate')
def validate(payload: AnalysisRequest):
    _, quality = prepare(payload.records, payload.config)
    return quality


@app.post('/api/analyze')
def analysis(payload: AnalysisRequest):
    report = analyze(payload)
    if len(report.model_dump_json().encode()) > 4_000_000:
        raise HTTPException(413, 'Report is too large; reduce the number of rows or cell lengths.')
    return report


@app.get('/api/sample')
def sample():
    rows = sample_records()
    _, quality = prepare(rows, Config())
    return {'records': rows, 'columns': list(dict.fromkeys(k for row in rows for k in row)), 'quality': quality, 'synthetic': True}
