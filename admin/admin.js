const cfg = window.ARBOR_VISTA_CONFIG || { apiBaseUrl: '/api/v1', propertySlug: 'arbor-vista-retreat', requestTimeoutMs: 15000 };
const endpoint = (path) => `${cfg.apiBaseUrl}${path.startsWith('/') ? path : `/${path}`}`;
const api = async (path, opts = {}) => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), cfg.requestTimeoutMs || 15000);
  try {
    const r = await fetch(endpoint(path), {
      headers: {
        'Content-Type': 'application/json',
        'X-Property-Slug': cfg.propertySlug,
        ...(opts.headers || {})
      },
      ...opts,
      signal: controller.signal
    });
    const text = await r.text();
    const d = text ? JSON.parse(text) : {};
    if (!r.ok) throw new Error(d.error || 'Request failed');
    return d;
  } finally {
    clearTimeout(timer);
  }
};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function table(rows,cols){if(!rows.length)return '<p>No records found.</p>';return `<table><thead><tr>${cols.map(c=>`<th>${esc(c[0])}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${cols.map(c=>`<td>${c[1](r)}</td>`).join('')}</tr>`).join('')}</tbody></table>`}
async function status(){try{const h=await api('/health');apiStatus.textContent=`API connected · ${h.property?.name||cfg.propertySlug}`;apiStatus.className='status ok'}catch(e){apiStatus.textContent='API offline — start the local backend or configure the cloud API';apiStatus.className='status bad'}}status();
async function loadDashboard(){const [r,b,s]=await Promise.all([api('/reservations'),api('/blocks'),api('/calendar-sources')]);const today=new Date().toISOString().slice(0,10);mUpcoming.textContent=r.filter(x=>x.end_date>=today&&x.status!=='cancelled').length;mPending.textContent=r.filter(x=>x.status==='pending').length;mBlocks.textContent=b.length;mSources.textContent=s.filter(x=>x.enabled).length;upcomingTable.innerHTML=table(r.filter(x=>x.end_date>=today&&x.status!=='cancelled').slice(0,10),[['Dates',x=>`${esc(x.start_date)} → ${esc(x.end_date)}`],['Guest',x=>esc(x.guest_name||x.summary)],['Source',x=>esc(x.source_type)],['Status',x=>`<span class="pill">${esc(x.status)}</span>`]])}
async function loadReservations(){const r=await api('/reservations');reservationTable.innerHTML=table(r,[['Dates',x=>`${esc(x.start_date)} → ${esc(x.end_date)}`],['Guest / Summary',x=>esc(x.guest_name||x.summary)],['Contact',x=>`${esc(x.email||'—')}<br>${esc(x.phone||'')}`],['Guests',x=>x.adults?`${x.adults} adults · ${x.children} children`:'—'],['Source',x=>esc(x.source_type)],['Status',x=>`<span class="pill">${esc(x.status)}</span>`],['Action',x=>x.status==='pending'?`<button onclick="setStatus('${esc(x.id)}','confirmed')">Approve</button> <button class="danger" onclick="setStatus('${esc(x.id)}','cancelled')">Decline</button>`:x.status==='confirmed'?`<button class="danger" onclick="setStatus('${esc(x.id)}','cancelled')">Cancel</button>`:'—']])}
async function setStatus(id,status){await api('/reservations/'+id,{method:'PATCH',body:JSON.stringify({status})});loadReservations()}
async function setupCalendar(){const show=async()=>{const b=await api('/blocks');blockTable.innerHTML=table(b,[['Dates',x=>`${esc(x.start_date)} → ${esc(x.end_date)}`],['Reason',x=>esc(x.reason)]])};blockForm.onsubmit=async e=>{e.preventDefault();try{await api('/blocks',{method:'POST',body:JSON.stringify(Object.fromEntries(new FormData(e.target)))});blockMsg.textContent='Block created.';e.target.reset();show()}catch(x){blockMsg.textContent=x.message}};availabilityForm.onsubmit=async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target));try{const x=await api(`/availability?start=${encodeURIComponent(d.start)}&end=${encodeURIComponent(d.end)}`);availabilityMsg.textContent=x.available?'Available':'Unavailable — '+x.conflicts.length+' conflict(s)'}catch(x){availabilityMsg.textContent=x.message}};show()}
async function loadSources(){const s=await api('/calendar-sources');sourceCards.innerHTML=s.map(x=>`<div class="source-card"><strong>${esc(x.name)}</strong><label>iCal feed URL<input id="url-${esc(x.id)}" value="${esc(x.feed_url||'')}"></label><label>Enabled<select id="en-${esc(x.id)}"><option value="1" ${x.enabled?'selected':''}>Yes</option><option value="0" ${!x.enabled?'selected':''}>No</option></select></label><div><button onclick="saveSource('${esc(x.id)}')">Save</button> <button onclick="syncSource('${esc(x.id)}')">Sync now</button></div></div>`).join('')}
async function saveSource(id){await api('/calendar-sources/'+id,{method:'PATCH',body:JSON.stringify({feed_url:document.getElementById('url-'+id).value,enabled:document.getElementById('en-'+id).value==='1'})});alert('Saved')}
async function syncSource(id){try{const d=await api('/sync/'+id,{method:'POST',body:'{}'});alert('Sync complete: '+JSON.stringify(d));}catch(e){alert(e.message)}}
async function loadLogs(){const [s,a]=await Promise.all([api('/sync-runs'),api('/audit')]);syncTable.innerHTML=table(s,[['Started',x=>esc(x.started_at)],['Source',x=>esc(x.source_name)],['Status',x=>esc(x.status)],['Seen',x=>esc(x.events_seen)],['Changes',x=>`${x.events_inserted} inserted · ${x.events_updated} updated · ${x.events_cancelled} cancelled`],['Error',x=>esc(x.error_message||'—')]]);auditTable.innerHTML=table(a,[['Time',x=>esc(x.created_at)],['Action',x=>esc(x.action)],['Entity',x=>`${esc(x.entity_type)}<br>${esc(x.entity_id||'')}`],['Details',x=>esc(x.details_json||'—')]])}
