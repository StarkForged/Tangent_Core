import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import {ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid} from 'recharts';
import './style.css';
import {findingsCsv} from './export.js';
import {evidenceRows} from './evidence.js';
import Overview from './Overview.jsx';

const fields = ['event_id','route','timestamp','status','exception_code','exception_message','exception_category','latency_ms','retry_count','source','destination'];
const defaults = {columns:{},failure_statuses:['failed','failure','error'],success_statuses:['success','completed','ok'],recurring_min:3,contamination:.05,dbscan_eps:.75,dbscan_min_samples:3,trend_interval:'hour'};
async function api(path, options) {
  const response = await fetch('/api/'+path,options);
  let data;
  try {data = await response.json();} catch {throw new Error(`Server returned HTTP ${response.status}. Check the API connection or request size and retry.`);}
  if (!response.ok) throw new Error((typeof data.detail === 'string' ? data.detail : 'Invalid settings or records.') + (data.errors ? ' '+data.errors.map(e=>e.field+': '+e.message).join('; ') : ''));
  return data;
}
const post = payload => ({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
function download(name, content, type) {
  const url = URL.createObjectURL(new Blob([content],{type}));
  const link = document.createElement('a'); link.href=url; link.download=name; link.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function Table({records}) {
  if (!records.length) return <p>No matching records.</p>;
  const keys = [...new Set(records.flatMap(Object.keys))].sort((a,b)=>(a==='original')-(b==='original'));
  return <div className="overflow-x-auto"><table><thead><tr>{keys.map(k=><th key={k}>{k}</th>)}</tr></thead><tbody>{records.map((row,i)=><tr key={i}>{keys.map(k=><td key={k}>{row[k]!==null && typeof row[k]==='object' ? <details><summary>View values</summary><pre>{JSON.stringify(row[k],null,2)}</pre></details> : String(row[k]??'Unavailable')}</td>)}</tr>)}</tbody></table></div>;
}
function App() {
  const [dataset,setDataset]=useState(null),[config,setConfig]=useState(defaults),[quality,setQuality]=useState(null),[report,setReport]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [filters,setFilters]=useState({route:'',outcome:'',category:'',start:'',end:''}),[finding,setFinding]=useState(null),[page,setPage]=useState(0);
  const [search,setSearch]=useState(''),[sort,setSort]=useState('row_reference'),[direction,setDirection]=useState('asc');
  async function task(work) {setBusy(true);setError('');try {await work();} catch(e){setError(e.message);} finally{setBusy(false);}}
  function loaded(data){setDataset(data);setQuality(data.quality);setReport(null);setFinding(null);setConfig(defaults);setPage(0);setSearch('');setFilters({route:'',outcome:'',category:'',start:'',end:''});}
  function change(next){setConfig(next);setReport(null);setFinding(null);setQuality(null);}
  function filter(key,value){setFilters({...filters,[key]:value});setPage(0);}
  async function analyze(){await task(async()=>{const payload={records:dataset.records,synthetic:dataset.synthetic,config};const result=await api('analyze',post(payload));setReport(result);setQuality(result.quality);setPage(0);setFinding(null);});}
  const selected=report?.findings.find(f=>f.finding_id===finding);
  const rows = evidenceRows(report?.records||[],filters,selected,search,sort,direction);
  const chart=report ? ['failure','success','unknown'].map(outcome=>({outcome,count:report.records.filter(r=>r.outcome===outcome).length})) : [];
  return <main className="max-w-7xl mx-auto p-4 md:p-8 space-y-5">
    <header><h1 className="text-2xl font-bold">TangentCore Routing Insight & Exception Analyzer</h1><p>Evidence-backed investigation only. Recommendations require human review; this application cannot change production routing.</p></header>
    {error&&<div role="alert" className="bg-red-100 text-red-900 p-3 rounded">{error}</div>}
    <section><h2>1. Load routing data</h2><p>UTF-8 CSV or JSON array of flat objects. Maximum 1 MB, 2,000 rows, 50 columns. Data is processed in memory without permanent server storage.</p>
      <div className="flex flex-wrap gap-3 items-center"><label className="control">Upload dataset<input aria-label="Upload dataset" type="file" accept=".csv,.json" disabled={busy} onChange={e=>{const file=e.target.files[0];if(file)task(async()=>{if(file.size>1000000)throw new Error('File exceeds 1 MB.');loaded(await api('preview?filename='+encodeURIComponent(file.name),{method:'POST',body:file,headers:{'Content-Type':'application/octet-stream'}}));});e.target.value='';}}/></label>
      <button disabled={busy} onClick={()=>task(async()=>loaded(await api('sample')))}>Use synthetic sample</button></div>
    </section>
    {busy&&<p role="status">Processing…</p>}
    {dataset&&<>
      <section><h2>2. Preview and configure</h2><strong>{dataset.synthetic?'SYNTHETIC DEMONSTRATION DATA':'Uploaded dataset — provenance supplied by user'}</strong><p>{dataset.records.length} input records. Preview shows the first 10. Source references are 1-based imported record positions (CSV header excluded).</p>
        <Table records={dataset.records.slice(0,10)}/>
        <fieldset disabled={busy}>
        <details className="mt-4"><summary>Column mapping (choose unused for unavailable fields)</summary><div className="grid sm:grid-cols-3 gap-3 mt-3">{fields.map(field=><label key={field}>{field}<select value={config.columns[field]??(dataset.columns.includes(field)?field:'')} onChange={e=>change({...config,columns:{...config.columns,[field]:e.target.value}})}><option value="">Unused</option>{dataset.columns.map(c=><option key={c}>{c}</option>)}</select></label>)}</div></details>
        <p className="mt-4">Confirm these generic status mappings against your dataset. Unmapped statuses are excluded from failure rates.</p>
        <div className="grid md:grid-cols-2 gap-3">{['failure_statuses','success_statuses'].map(key=><label key={key}>{key.replaceAll('_',' ')} (comma separated)<input value={config[key].join(',')} onChange={e=>change({...config,[key]:e.target.value.split(',')})}/></label>)}</div>
        <details className="mt-3"><summary>Detection thresholds</summary><div className="grid sm:grid-cols-4 gap-3 mt-3">{[['recurring_min',2,2000,1],['contamination',.001,.3,.001],['dbscan_eps',.05,10,.05],['dbscan_min_samples',2,100,1]].map(([key,min,max,step])=><label key={key}>{key}<input type="number" min={min} max={max} step={step} value={config[key]} onChange={e=>change({...config,[key]:Number(e.target.value)})}/></label>)}</div></details>
        <button className="mt-4" disabled={busy} onClick={()=>task(async()=>setQuality(await api('validate',post({records:dataset.records,config,synthetic:dataset.synthetic}))))}>Validate current settings</button>
        <label className="block mt-3">Trend aggregation (UTC)<select value={config.trend_interval} onChange={e=>change({...config,trend_interval:e.target.value})}><option value="hour">Hourly</option><option value="day">Daily</option></select></label>
        {quality&&<div className="mt-3"><p><b>Quality:</b> {quality.input_records} input; {quality.analyzed_records} retained; {quality.excluded_exact_duplicates} exact duplicates excluded.</p><ul>{quality.warnings.map((w,i)=><li key={i}>{w}</li>)}</ul>{quality.excluded_row_references.length>0&&<p>Excluded row references: {quality.excluded_row_references.join(', ')}</p>}</div>}
        <button className="mt-4" disabled={busy||!quality} onClick={analyze}>Run analysis</button>{!quality&&<p>Validate your changed settings before running analysis.</p>}
        {quality&&<><p>{quality.invalid_records} input records contain invalid numeric/date values; {quality.retained_invalid_records} remain in analysis with those fields excluded. Unknown outcomes: {quality.unmapped_status_count}. Invalid-field counts overlap; they are not additional excluded rows.</p><details><summary>Invalid fields, missing values and source references</summary><pre>{JSON.stringify({invalid_fields:quality.invalid_fields,missing_values:quality.missing_values,unmapped_status_values:quality.unmapped_status_values},null,2)}</pre></details></>}
        </fieldset>
      </section>
    </>}
    {report&&<>
      <section><h2>3. Results {report.synthetic&&'— SYNTHETIC'}</h2><div className="grid sm:grid-cols-4 gap-3">{[['Input records',report.summary.input_records],['Retained records',report.summary.analyzed_records],['Excluded duplicates',report.summary.excluded_exact_duplicates],['Retained records with invalid fields',report.summary.retained_invalid_records],['Mapped failures',report.summary.failure_count??'Unavailable'],['Successful outcomes',report.summary.success_count??'Unavailable'],['Unknown outcomes',report.summary.unknown_outcome_count],['Known outcome denominator',report.summary.known_outcome_denominator],['Failure rate',report.summary.failure_rate===null?'Unavailable':(report.summary.failure_rate*100).toFixed(1)+'%'],['Anomalous records',report.summary.anomalous_records??'Unavailable']].map(([label,value])=><div className="bg-slate-100 p-3 rounded" key={label}><p>{label}</p><b className="text-xl">{value}</b></div>)}</div>
        <p>Input = retained + excluded duplicates. Retained = failures + successes + unknown outcomes. Invalid fields and anomalies overlap these counts; do not add them. Failure rate uses known outcomes only.</p>
        <p>Summary and findings use the full retained dataset. Filters below affect the evidence table only. No pattern detected does not prove an absence of issues.</p>
        {report.summary.observed_period&&<p>Observed coverage: {report.summary.observed_period.start} to {report.summary.observed_period.end}</p>}
        <div className="h-52 mt-4"><ResponsiveContainer width="100%" height="100%"><BarChart data={chart}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey="outcome"/><YAxis allowDecimals={false}/><Tooltip/><Bar dataKey="count" fill="#2563eb"/></BarChart></ResponsiveContainer></div>
        <details><summary>Methods, thresholds and numeric exclusions</summary><pre>{JSON.stringify(report.methods,null,2)}</pre></details>
        <Overview report={report}/>
        <div className="flex gap-3 mt-3"><button onClick={()=>download('tangentcore-report.json',JSON.stringify(report,null,2),'application/json')}>Export full JSON report</button><button onClick={()=>download('tangentcore-findings.csv',findingsCsv(report),'text/csv;charset=utf-8')}>Export findings CSV</button></div>
      </section>
      <section><h2>Findings ({report.findings.length})</h2>{!report.findings.length&&<p>No patterns met the configured thresholds. Review data coverage and method availability.</p>}{report.findings.map(f=><details key={f.finding_id} className="border rounded p-3 my-2"><summary>{f.finding_id} · {f.title} · {f.record_count} records</summary><p><b>Observed:</b> {f.observation}</p><p><b>Routes:</b> {f.affected_routes.join(", ")||"Unavailable"}</p><p><b>Period:</b> {f.observed_period ? f.observed_period.start+" to "+f.observed_period.end : "Unavailable"}</p><p><b>Flagged because:</b> {f.reason_flagged}</p><p><b>Interpretation:</b> {f.interpretation}</p><p><b>Method:</b> {f.detection_method}</p><pre>{JSON.stringify(f.evidence,null,2)}</pre><b>Recommended investigation</b><ul>{f.recommendations.map(r=><li key={r}>{r}</li>)}</ul><b>Limitations</b><ul>{f.limitations.map(r=><li key={r}>{r}</li>)}</ul><button onClick={()=>{setFinding(f.finding_id);setSearch('');setFilters({route:'',outcome:'',category:'',start:'',end:''});setPage(0);document.getElementById('evidence').scrollIntoView({behavior:'smooth'});}}>Inspect source records</button></details>)}</section>
      <section id="evidence"><h2>Record evidence {selected&&'— '+selected.finding_id}</h2>{selected&&<button onClick={()=>{setFinding(null);setPage(0);}}>Show all records</button>}<div className="grid sm:grid-cols-5 gap-3 mt-3">{[['route','route'],['outcome','outcome'],['category','exception_category']].map(([key,field])=><label key={key}>{key}<select value={filters[key]} onChange={e=>filter(key,e.target.value)}><option value="">All</option>{[...new Set(report.records.map(r=>r[field]))].filter(Boolean).sort().map(v=><option key={v}>{v}</option>)}</select></label>)}{['start','end'].map(key=><label key={key}>{key} date (UTC)<input type="date" value={filters[key]} onChange={e=>filter(key,e.target.value)}/></label>)}</div>
        <div className="grid sm:grid-cols-3 gap-3 mt-3"><label>Search evidence and original values<input value={search} onChange={e=>{setSearch(e.target.value);setPage(0);}}/></label><label>Sort by<select value={sort} onChange={e=>{setSort(e.target.value);setPage(0);}}>{['row_reference','route','timestamp','outcome','exception_category','anomaly_score','failure_cluster'].map(k=><option key={k}>{k}</option>)}</select></label><label>Sort direction<select value={direction} onChange={e=>{setDirection(e.target.value);setPage(0);}}><option value="asc">Ascending</option><option value="desc">Descending</option></select></label></div><p>{rows.length} matching records. Original values are preserved under “original”.</p><Table records={rows.slice(page*20,page*20+20)}/><div className="flex gap-3 mt-3"><button disabled={page===0} onClick={()=>setPage(page-1)}>Previous</button><span>Page {page+1} of {Math.max(1,Math.ceil(rows.length/20))}</span><button disabled={(page+1)*20>=rows.length} onClick={()=>setPage(page+1)}>Next</button></div>
      </section>
    </>}
  </main>;
}
createRoot(document.getElementById('root')).render(<App/>);
