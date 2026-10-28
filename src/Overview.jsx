import {ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid} from 'recharts';

function Chart({data, label, value, percent=false}) {
  return <div className="h-64"><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{bottom:50,left:5,right:15}}><CartesianGrid strokeDasharray="3 3"/><XAxis dataKey={label} angle={-20} textAnchor="end" tick={{fontSize:10}} interval={0}/><YAxis domain={percent?[0,100]:[0,'auto']} allowDecimals={percent}/><Tooltip content={({active,payload})=>active&&payload?.length?<div className="bg-white border p-3 text-xs"><b>{payload[0].payload[label]}</b><pre>{JSON.stringify(payload[0].payload,null,2)}</pre></div>:null}/><Bar dataKey={value} fill="#2563eb"/></BarChart></ResponsiveContainer></div>;
}

export default function Overview({report}) {
  const d=report.distributions, s=report.summary;
  return <div className="space-y-4">
    <p><b>Anomaly / clustering summary:</b> {s.anomalous_records??'Unavailable'} anomalous records; {s.cluster_count??'Unavailable'} failure clusters; {s.clustering_noise_records??'Unavailable'} noise records. These counts overlap outcomes and must not be added to them.</p>
    <details><summary>Failure rate over time ({d.trend_interval}, UTC)</summary>
      <p>{d.trend_note} {d.trend_excluded_records} records excluded for unavailable timestamps. Hover over a bar for counts and denominator; a table below includes unknown-only buckets.</p>
      {d.trend.length>=2?<Chart data={d.trend.map(x=>({...x,bucket:x.timestamp.slice(0,16).replace('T',' ')}))} label="bucket" value="failure_rate_percent" percent/>:<p>At least two observed time buckets are needed for a trend. No time series has been invented.</p>}
      <details><summary>Time bucket counts</summary><pre>{JSON.stringify(d.trend,null,2)}</pre></details>
    </details>
    <details><summary>Route comparisons</summary><p>Overall route failure rates use known outcomes only. Compare the counts and observed coverage, not percentages alone. Chart shows up to 20 routes; the complete table is below.</p>
      {d.routes.length?<><Chart data={d.routes.slice(0,20)} label="route" value="failure_rate_percent" percent/><div className="overflow-x-auto"><table><thead><tr><th>Route</th><th>Failures / known</th><th>Unknown</th><th>Failure rate</th><th>Observed coverage</th></tr></thead><tbody>{d.routes.map(r=><tr key={r.route}><td>{r.route}</td><td>{r.failure_count} / {r.known_outcome_denominator}</td><td>{r.unknown_count}</td><td>{r.failure_rate_percent===null?'Unavailable':r.failure_rate_percent.toFixed(1)+'%'}</td><td>{r.observed_start??'Unavailable'} – {r.observed_end??'Unavailable'}</td></tr>)}</tbody></table></div></>:<p>No route data is available.</p>}
    </details>
    <details><summary>Exception category distribution</summary><p>Includes all outcomes, including Unknown / Unclassified; a category does not confirm a failure. Chart shows up to 20 groups; all groups are listed below.</p><Chart data={d.categories.slice(0,20).map(r=>({...r,label:`${r.category} (${r.source})`}))} label="label" value="records"/><pre>{JSON.stringify(d.categories,null,2)}</pre></details>
  </div>;
}
