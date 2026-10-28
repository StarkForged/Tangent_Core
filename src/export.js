export function csvCell(value) {
  let text = typeof value === 'object' ? JSON.stringify(value) : String(value ?? '');
  if (/^[\s]*[=+@-]/.test(text) || /^[\t\r\n]/.test(text)) text="'"+text;
  return '"'+text.replaceAll('"','""')+'"';
}

export function findingsCsv(report) {
  const keys=['analysis_version','synthetic','config','finding_id','finding_type','title','observation','affected_routes','observed_period','reason_flagged','interpretation','record_count','source_record_references','evidence','detection_method','recommendations','limitations'];
  return [keys.map(csvCell).join(','),...report.findings.map(f=>{
    const row={...f,analysis_version:report.analysis_version,synthetic:report.synthetic,config:report.config};
    return keys.map(k=>csvCell(row[k])).join(',');
  })].join('\r\n');
}
