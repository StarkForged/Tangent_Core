export function evidenceRows(records, filters, selected, search, sort, direction) {
  const refs = selected ? new Set(selected.source_record_references) : null;
  const query = search.trim().toLowerCase();
  const rows = records.filter(r =>
    (!filters.route || r.route === filters.route) &&
    (!filters.outcome || r.outcome === filters.outcome) &&
    (!filters.category || r.exception_category === filters.category) &&
    (!filters.start || (r.timestamp && Date.parse(r.timestamp) >= Date.parse(filters.start+'T00:00:00Z'))) &&
    (!filters.end || (r.timestamp && Date.parse(r.timestamp) <= Date.parse(filters.end+'T23:59:59.999Z'))) &&
    (!refs || refs.has(r.row_reference)) &&
    (!query || JSON.stringify(r).toLowerCase().includes(query)));
  return rows.sort((a,b)=>{
    if (a[sort] == null) return b[sort] == null ? a.row_reference-b.row_reference : 1;
    if (b[sort] == null) return -1;
    const cmp = sort === 'timestamp' ? Date.parse(a[sort])-Date.parse(b[sort]) : typeof a[sort] === 'number' ? a[sort]-b[sort] : String(a[sort]).localeCompare(String(b[sort]));
    return (direction === 'desc' ? -cmp : cmp) || a.row_reference-b.row_reference;
  });
}
