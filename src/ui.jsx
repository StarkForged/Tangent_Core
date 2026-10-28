export function Icon({name, size=20, ...props}) {
  const paths={
    overview:<><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></>,
    database:<><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/></>,
    findings:<><path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5m0 3v.01"/></>,
    evidence:<><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16m6-10v10"/></>,
    methods:<><path d="m8 5-6 7 6 7m8-14 6 7-6 7m-3-16-2 18"/></>,
    upload:<><path d="M12 16V3m-5 5 5-5 5 5M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5"/></>,
    arrow:<><path d="M4 12h16m-6-6 6 6-6 6"/></>,
    download:<><path d="M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4"/></>,
    shield:<><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="m8 12 3 3 5-6"/></>,
    check:<path d="m5 12 4 4L19 6"/>,
    chevron:<path d="m9 5 7 7-7 7"/>,
    search:<><circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/></>,
    close:<path d="m6 6 12 12M6 18 18 6"/>,
    pulse:<path d="M2 12h4l3-8 6 16 3-8h4"/>,
    route:<><circle cx="5" cy="5" r="2"/><circle cx="19" cy="19" r="2"/><path d="M7 5h9a4 4 0 0 1 0 8H8a3 3 0 0 0 0 6h9"/></>,
    file:<><path d="M14 2H5v20h14V7l-5-5Zm0 0v5h5M8 12h8m-8 4h6"/></>,
    spark:<><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/></>,
    info:<><circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.01"/></>,
    clock:<><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    plus:<path d="M12 5v14M5 12h14"/>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name]||paths.file}</svg>;
}
export function Badge({children,tone='neutral'}) {return <span className={`badge badge-${tone}`}>{children}</span>;}
export function Empty({icon='database',title,description,action}) {return <div className="empty-state"><span className="empty-icon"><Icon name={icon} size={28}/></span><h3>{title}</h3><p>{description}</p>{action}</div>;}
export function PageHeading({eyebrow,title,description,children}) {return <div className="page-heading"><div>{eyebrow&&<div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1><p>{description}</p></div>{children&&<div className="heading-actions">{children}</div>}</div>;}
export function Table({records}) {
  if (!records.length) return <Empty icon="search" title="No matching records" description="Try a different search or adjust your filters."/>;
  const keys=[...new Set(records.flatMap(Object.keys))].sort((a,b)=>(a==='original')-(b==='original'));
  return <div className="table-scroll" tabIndex="0" aria-label="Scrollable records table"><table><thead><tr>{keys.map(k=><th key={k}>{k.replaceAll('_',' ')}</th>)}</tr></thead><tbody>{records.map((row,i)=><tr key={row.row_reference??i}>{keys.map(k=><td key={k}>{row[k]!==null&&typeof row[k]==='object'?<details className="cell-detail"><summary>{k==='original'?'Original record':'View values'}</summary><pre>{JSON.stringify(row[k],null,2)}</pre></details>:k==='outcome'?<Badge tone={row[k]==='failure'?'danger':row[k]==='success'?'green':'amber'}>{row[k]}</Badge>:String(row[k]??'—')}</td>)}</tr>)}</tbody></table></div>;
}
export function formatDate(value) {return value?new Date(value).toLocaleString('en-GB',{timeZone:'UTC',day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hour12:false})+' UTC':'Unavailable';}
