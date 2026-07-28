(() => {
  'use strict';

  const STORAGE_KEY = 'arbor-market-workspace-v421';
  const PROPERTY_KEY = 'arbor-market-property-v421';
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const xml = value => esc(value);
  const number = (value, fallback = 0) => {
    const parsed = Number(String(value ?? '').replace(/[$,%\s]/g, ''));
    return Number.isFinite(parsed) ? parsed : fallback;
  };
  const bool = value => ['true','1','yes','y','included','x'].includes(String(value ?? '').trim().toLowerCase());
  const avg = values => {
    const clean = values.map(Number).filter(value => Number.isFinite(value) && value > 0);
    return clean.length ? clean.reduce((sum, value) => sum + value, 0) / clean.length : 0;
  };
  const median = values => {
    const clean = values.map(Number).filter(value => Number.isFinite(value) && value > 0).sort((a,b) => a-b);
    if (!clean.length) return 0;
    const middle = Math.floor(clean.length / 2);
    return clean.length % 2 ? clean[middle] : (clean[middle - 1] + clean[middle]) / 2;
  };
  const money = value => new Intl.NumberFormat(undefined,{style:'currency',currency:'USD',maximumFractionDigits:0}).format(number(value));
  const pct = value => `${number(value).toFixed(1)}%`;
  const clone = value => JSON.parse(JSON.stringify(value));
  const slugify = value => String(value || 'comp').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,60) || 'comp';
  const storage = {
    get(key) { try { return window.localStorage.getItem(key); } catch (_) { return null; } },
    set(key, value) { try { window.localStorage.setItem(key, value); return true; } catch (_) { return false; } }
  };

  const download = (filename, content, type = 'application/octet-stream') => {
    const blob = content instanceof Blob ? content : new Blob([content], {type});
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  const app = {workspace:null, property:null, search:''};

  function message(text, isError = false) {
    const el = $('miMessage');
    if (!el) return;
    el.textContent = text;
    el.style.color = isError ? '#9d3b36' : '';
  }

  function normalizeMetric(metric, index = 0) {
    const month = monthName(metric.month ?? metric.month_start ?? index);
    const adr = number(metric.adr ?? metric.estimated_adr);
    const occupancy = Math.max(0, Math.min(100, number(metric.occupancy ?? metric.estimated_occupancy)));
    const revenue = number(metric.revenue ?? metric.estimated_revenue, adr * occupancy / 100 * 30.4);
    return {month, adr, occupancy, revenue};
  }

  function normalizeComp(comp, index = 0) {
    const metricsInput = Array.isArray(comp.metrics) ? comp.metrics : [];
    const metrics = metricsInput.map((item,index) => normalizeMetric(item,index)).filter(item => item.adr > 0 || item.occupancy > 0 || item.revenue > 0);
    return {
      id:String(comp.id || comp.listing_id || `${slugify(comp.name || comp.listing_name)}-${index+1}`),
      name:String(comp.name || comp.listing_name || `Comparable ${index+1}`),
      platform:String(comp.platform || comp.channel || comp.provider || 'Other'),
      listingUrl:String(comp.listingUrl || comp.listing_url || comp.url || ''),
      included:comp.included !== false,
      distanceMiles:(comp.distanceMiles ?? comp.distance_miles ?? comp.distance) === null || (comp.distanceMiles ?? comp.distance_miles ?? comp.distance) === undefined || (comp.distanceMiles ?? comp.distance_miles ?? comp.distance) === '' ? null : number(comp.distanceMiles ?? comp.distance_miles ?? comp.distance),
      locationName:String(comp.locationName || comp.location || ''), sourceObservedAt:String(comp.sourceObservedAt || comp.source_observed_at || ''),
      snapshotNotes:String(comp.snapshotNotes || comp.snapshot_notes || ''), observations:Array.isArray(comp.observations) ? comp.observations : [],
      bedrooms:number(comp.bedrooms), bathrooms:number(comp.bathrooms), guests:number(comp.guests ?? comp.accommodates), beds:number(comp.beds),
      rating:number(comp.rating), reviews:number(comp.reviews ?? comp.review_count),
      amenities:{
        hotTub:bool(comp.amenities?.hotTub ?? comp.hot_tub),
        arcade:bool(comp.amenities?.arcade ?? comp.arcade ?? comp.game_room),
        fireplace:bool(comp.amenities?.fireplace ?? comp.fireplace),
        resortAmenities:bool(comp.amenities?.resortAmenities ?? comp.resort_amenities),
        petFriendly:bool(comp.amenities?.petFriendly ?? comp.pet_friendly),
        evCharger:bool(comp.amenities?.evCharger ?? comp.ev_charger)
      },
      sourceLabel:String(comp.sourceLabel || comp.source_label || comp.data_source || 'Manual estimate'),
      metrics
    };
  }

  function normalizeProperty(property) {
    const actuals = MONTHS.map((month, index) => {
      const found = (property.actuals || []).find(item => monthName(item.month) === month) || {};
      return {
        month,
        adr:number(found.adr), occupancy:number(found.occupancy), revenue:number(found.revenue),
        sourceLabel:String(found.sourceLabel || 'Browser-entered actual')
      };
    });
    return {
      slug:String(property.slug || slugify(property.name)), code:String(property.code || 'PROPERTY'), name:String(property.name || 'Property'),
      address:String(property.address || ''), bedrooms:number(property.bedrooms), bathrooms:number(property.bathrooms),
      standardGuests:number(property.standardGuests ?? property.standard_guests, 6), expandedGuests:number(property.expandedGuests ?? property.expanded_guests, 8),
      amenities:Array.isArray(property.amenities) ? property.amenities : [],
      profile:{
        mode:String(property.profile?.mode || 'exact'), radiusMiles:number(property.profile?.radiusMiles, 5),
        bedroomsMin:number(property.profile?.bedroomsMin, 2), bedroomsMax:number(property.profile?.bedroomsMax, 2),
        bathroomsMin:number(property.profile?.bathroomsMin, 2), bathroomsMax:number(property.profile?.bathroomsMax, 3),
        guestsMin:number(property.profile?.guestsMin, 5), guestsMax:number(property.profile?.guestsMax, 7),
        requireHotTub:property.profile?.requireHotTub !== false, requireArcade:property.profile?.requireArcade === true
      },
      actuals,
      futureRates:Array.isArray(property.futureRates) ? property.futureRates.map(item => ({label:String(item.label || item.date || ''),ownRate:number(item.ownRate ?? item.property_rate),compMedian:number(item.compMedian ?? item.comp_median_rate)})) : [],
      comps:(property.comps || []).map(normalizeComp)
    };
  }

  function normalizeWorkspace(workspace) {
    if (!workspace || !Array.isArray(workspace.properties)) throw new Error('Workspace must contain a properties array.');
    return {version:'4.2-phase-a', properties:workspace.properties.map(normalizeProperty)};
  }

  function monthName(value) {
    const text = String(value ?? '').trim();
    if (!text) return MONTHS[0];
    const short = text.slice(0,3).toLowerCase();
    const byName = MONTHS.find(month => month.toLowerCase() === short);
    if (byName) return byName;
    const numeric = Number(text.match(/(?:^|[-/])(\d{1,2})(?:$|[-/])/)?.[1] ?? text);
    if (numeric >= 1 && numeric <= 12) return MONTHS[numeric - 1];
    const date = new Date(text);
    return Number.isNaN(date.getTime()) ? MONTHS[0] : MONTHS[date.getMonth()];
  }

  function save() {
    storage.set(STORAGE_KEY, JSON.stringify(app.workspace));
    if (app.property) storage.set(PROPERTY_KEY, app.property.slug);
  }

  function selectedComps() {
    return app.property.comps.filter(comp => comp.included);
  }

  function annual(comp) {
    return {
      adr:avg(comp.metrics.map(metric => metric.adr)),
      occupancy:avg(comp.metrics.map(metric => metric.occupancy)),
      revenue:avg(comp.metrics.map(metric => metric.revenue)),
      revpar:avg(comp.metrics.filter(metric=>metric.adr>0&&metric.occupancy>0).map(metric => metric.adr * metric.occupancy / 100)),
      observedRates:(comp.observations||[]).filter(item=>number(item.nightlyRate)>0).length
    };
  }

  function actualAnnual() {
    const actuals = app.property.actuals;
    return {
      adr:avg(actuals.map(item => item.adr)), occupancy:avg(actuals.map(item => item.occupancy)),
      revenue:avg(actuals.map(item => item.revenue)), revpar:avg(actuals.map(item => item.adr * item.occupancy / 100))
    };
  }

  function monthlyComp(metricKey) {
    const comps = selectedComps();
    return MONTHS.map((month, index) => median(comps.map(comp => {
      const metric = comp.metrics[index] || {};
      if (metricKey === 'revpar') return number(metric.adr) * number(metric.occupancy) / 100;
      return number(metric[metricKey]);
    })));
  }

  function similarity(comp) {
    const p = app.property;
    let score = 100;
    if (comp.distanceMiles !== null && comp.distanceMiles !== undefined) score -= Math.min(30, Math.abs(number(comp.distanceMiles)) * 5);
    score -= Math.min(22, Math.abs(number(comp.bedrooms) - number(p.bedrooms)) * 11);
    score -= Math.min(12, Math.abs(number(comp.bathrooms) - number(p.bathrooms)) * 6);
    score -= Math.min(20, Math.abs(number(comp.guests) - number(p.standardGuests)) * 5);
    if (p.amenities.includes('hotTub') && !comp.amenities.hotTub) score -= 8;
    if (p.amenities.includes('arcade') && !comp.amenities.arcade) score -= 4;
    if (p.amenities.includes('fireplace') && !comp.amenities.fireplace) score -= 3;
    if (p.amenities.includes('resortAmenities') && !comp.amenities.resortAmenities) score -= 3;
    return Math.max(0, Math.round(score));
  }

  function profileMatches(comp) {
    const profile = app.property.profile;
    return (comp.distanceMiles === null || comp.distanceMiles === undefined || number(comp.distanceMiles) <= profile.radiusMiles) &&
      number(comp.bedrooms) >= profile.bedroomsMin && number(comp.bedrooms) <= profile.bedroomsMax &&
      number(comp.bathrooms) >= profile.bathroomsMin && number(comp.bathrooms) <= profile.bathroomsMax &&
      number(comp.guests) >= profile.guestsMin && number(comp.guests) <= profile.guestsMax &&
      (!profile.requireHotTub || comp.amenities.hotTub) && (!profile.requireArcade || comp.amenities.arcade);
  }

  function syncProfileInputs() {
    const profile = app.property.profile;
    $('miAddress').value = app.property.address;
    $('miProfile').value = profile.mode;
    $('miRadius').value = profile.radiusMiles;
    $('miBedroomsMin').value = profile.bedroomsMin;
    $('miBedroomsMax').value = profile.bedroomsMax;
    $('miBathroomsMin').value = profile.bathroomsMin;
    $('miBathroomsMax').value = profile.bathroomsMax;
    $('miGuestsMin').value = profile.guestsMin;
    $('miGuestsMax').value = profile.guestsMax;
    $('miRequireHotTub').checked = profile.requireHotTub;
    $('miRequireArcade').checked = profile.requireArcade;
  }

  function readProfileInputs() {
    app.property.address = $('miAddress').value.trim();
    Object.assign(app.property.profile, {
      mode:$('miProfile').value, radiusMiles:number($('miRadius').value,5),
      bedroomsMin:number($('miBedroomsMin').value), bedroomsMax:number($('miBedroomsMax').value),
      bathroomsMin:number($('miBathroomsMin').value), bathroomsMax:number($('miBathroomsMax').value),
      guestsMin:number($('miGuestsMin').value), guestsMax:number($('miGuestsMax').value),
      requireHotTub:$('miRequireHotTub').checked, requireArcade:$('miRequireArcade').checked
    });
    save();
  }

  function applyPreset(mode) {
    const p = app.property;
    if (mode === 'exact') Object.assign(p.profile,{mode,radiusMiles:5,bedroomsMin:2,bedroomsMax:2,bathroomsMin:2,bathroomsMax:3,guestsMin:5,guestsMax:7,requireHotTub:true,requireArcade:false});
    if (mode === 'expanded') Object.assign(p.profile,{mode,radiusMiles:7,bedroomsMin:2,bedroomsMax:3,bathroomsMin:2,bathroomsMax:3.5,guestsMin:6,guestsMax:8,requireHotTub:true,requireArcade:false});
    if (mode === 'custom') p.profile.mode = 'custom';
    syncProfileInputs();
    save();
  }

  function deltaMarkup(actual, benchmark, format = value => String(value)) {
    const delta = actual - benchmark;
    const className = delta >= 0 ? 'positive' : 'negative';
    const sign = delta >= 0 ? '+' : '';
    return `<span class="metric-delta ${className}">${sign}${format(delta)} vs comp median</span>`;
  }

  function renderSummary() {
    const comps = selectedComps();
    const ratings = comps.map(item=>item.rating);
    const reviews = comps.map(item=>item.reviews);
    const observedRates = comps.flatMap(item=>item.observations||[]).filter(item=>number(item.nightlyRate)>0);
    const platforms = new Set(comps.map(item=>item.platform));
    const arcadeCount = comps.filter(item=>item.amenities.arcade).length;
    $('miSummaryMetrics').innerHTML = [
      ['Included public comps', comps.length, `<span class="metric-delta">${app.property.comps.length} records in snapshot</span>`],
      ['Platforms', platforms.size, `<span class="metric-delta">${[...platforms].join(' · ')}</span>`],
      ['Median rating', median(ratings) ? median(ratings).toFixed(2)+' ★' : '—', `<span class="metric-delta">${ratings.filter(Number.isFinite).length} rated listings</span>`],
      ['Median review count', median(reviews) ? Math.round(median(reviews)) : '—', `<span class="metric-delta">Public review counts</span>`],
      ['Game room / arcade', `${arcadeCount}/${comps.length}`, `<span class="metric-delta">${comps.length?Math.round(arcadeCount/comps.length*100):0}% of included comps</span>`],
      ['Rate observations', observedRates.length, `<span class="metric-delta">Consistent-date history grows over time</span>`]
    ].map(([label,value,delta]) => `<article><small>${esc(label)}</small><strong>${value}</strong>${delta}</article>`).join('');
    $('miCompCount').textContent = `${comps.length} included · ${app.property.comps.length - comps.length} excluded`;
    const snap=app.workspace.snapshot||{};
    const note=$('miSnapshotNote'); if(note) note.textContent=`${snap.name||'Real Comp Snapshot'} · observed ${snap.observedAt||'—'} · ${snap.limitations||''}`;
  }

  function lineChart(hostId, labels, series, options = {}) {
    const host = $(hostId);
    if (!host) return;
    const cleanSeries = series.filter(item => item.values.some(value => Number.isFinite(Number(value))));
    if (!cleanSeries.length || !labels.length) { host.innerHTML = '<div class="chart-empty">No chart data</div>'; return; }
    const width = 760, height = 300, margin = {left:58,right:22,top:18,bottom:44};
    const values = cleanSeries.flatMap(item => item.values.map(Number).filter(Number.isFinite));
    let min = options.min ?? Math.min(...values,0), max = options.max ?? Math.max(...values,1);
    if (max === min) max = min + 1;
    const x = index => margin.left + (labels.length === 1 ? 0 : index * (width - margin.left - margin.right) / (labels.length - 1));
    const y = value => margin.top + (max - value) * (height - margin.top - margin.bottom) / (max - min);
    const format = options.format || (value => Math.round(value));
    const ticks = 5;
    let svg = `<svg class="market-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${xml(options.ariaLabel || 'Comparison chart')}">`;
    for (let i=0;i<=ticks;i++) {
      const value = min + (max-min)*(ticks-i)/ticks;
      const yy = margin.top + i*(height-margin.top-margin.bottom)/ticks;
      svg += `<line class="chart-gridline" x1="${margin.left}" x2="${width-margin.right}" y1="${yy}" y2="${yy}"></line><text class="chart-label" x="${margin.left-8}" y="${yy+4}" text-anchor="end">${xml(format(value))}</text>`;
    }
    labels.forEach((label,index) => {
      if (labels.length > 14 && index % 2) return;
      svg += `<text class="chart-label" x="${x(index)}" y="${height-16}" text-anchor="middle">${xml(label)}</text>`;
    });
    cleanSeries.forEach(item => {
      const points = item.values.map((value,index) => `${x(index)},${y(number(value))}`).join(' ');
      svg += `<polyline class="${item.className || 'line-comp'}" points="${points}"></polyline>`;
      item.values.forEach((value,index) => svg += `<circle class="${item.pointClass || 'point-comp'}" cx="${x(index)}" cy="${y(number(value))}" r="3.5"><title>${xml(`${labels[index]} · ${item.name}: ${format(number(value))}`)}</title></circle>`);
    });
    svg += '</svg><div class="chart-legend">' + cleanSeries.map(item => `<span class="legend-item ${item.legendClass || ''}"><span class="legend-swatch"></span>${esc(item.name)}</span>`).join('') + '</div>';
    host.innerHTML = svg;
  }

  function scatterChart() {
    const host = $('miScatterChart');
    const comps = selectedComps();
    if (!comps.length) { host.innerHTML = '<div class="chart-empty">Select at least one comparable</div>'; return; }
    const observations = comps.map(comp => ({name:comp.name,...annual(comp),score:similarity(comp)}));
    const own = {name:app.property.name,...actualAnnual(),own:true};
    observations.push(own);
    const width=720,height=370,margin={left:60,right:20,top:20,bottom:50};
    const xMax=Math.max(100,...observations.map(item=>item.adr))*1.12;
    const yMax=Math.min(100,Math.max(50,...observations.map(item=>item.occupancy))*1.12);
    const x=value=>margin.left+number(value)*(width-margin.left-margin.right)/xMax;
    const y=value=>height-margin.bottom-number(value)*(height-margin.top-margin.bottom)/yMax;
    let svg=`<svg class="market-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="ADR versus occupancy scatter plot">`;
    for(let i=0;i<=5;i++){
      const xx=margin.left+i*(width-margin.left-margin.right)/5;
      const yy=margin.top+i*(height-margin.top-margin.bottom)/5;
      svg+=`<line class="chart-gridline" x1="${xx}" x2="${xx}" y1="${margin.top}" y2="${height-margin.bottom}"></line><text class="chart-label" x="${xx}" y="${height-25}" text-anchor="middle">${xml(money(xMax*i/5))}</text>`;
      svg+=`<line class="chart-gridline" x1="${margin.left}" x2="${width-margin.right}" y1="${yy}" y2="${yy}"></line><text class="chart-label" x="${margin.left-8}" y="${yy+4}" text-anchor="end">${Math.round(yMax*(5-i)/5)}%</text>`;
    }
    observations.forEach(item=>{
      const radius=item.own?8:Math.max(4,Math.min(9,4+Math.log10(Math.max(1,item.reviews||1))));
      svg+=`<circle class="${item.own?'point-own':'point-comp'}" cx="${x(item.adr)}" cy="${y(item.occupancy)}" r="${radius}" opacity="${item.own?1:.78}"><title>${xml(`${item.name}\nADR ${money(item.adr)}\nOccupancy ${pct(item.occupancy)}${item.score?`\nSimilarity ${item.score}%`:''}`)}</title></circle>`;
    });
    svg+=`<text class="chart-title-label" x="${(margin.left+width-margin.right)/2}" y="${height-5}" text-anchor="middle">Average daily rate</text><text class="chart-title-label" transform="translate(14 ${(margin.top+height-margin.bottom)/2}) rotate(-90)" text-anchor="middle">Occupancy</text></svg><div class="chart-legend"><span class="legend-item legend-own"><span class="legend-swatch"></span>${esc(app.property.name)}</span><span class="legend-item legend-comp"><span class="legend-swatch"></span>Comparable listings</span></div>`;
    host.innerHTML=svg;
  }

  function verticalBarChart(hostId, rows, options={}) {
    const host=$(hostId);
    if(!rows.length){host.innerHTML='<div class="chart-empty">Insufficient data</div>';return;}
    const width=720,height=310,margin={left:64,right:20,top:24,bottom:70};
    const max=Math.max(1,...rows.map(row=>number(row.value)))*1.15;
    const band=(width-margin.left-margin.right)/rows.length;
    const barWidth=Math.min(64,band*.62);
    const y=value=>height-margin.bottom-number(value)*(height-margin.top-margin.bottom)/max;
    const format=options.format||money;
    let svg=`<svg class="market-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${xml(options.ariaLabel||'Bar chart')}">`;
    for(let i=0;i<=4;i++){
      const value=max*(4-i)/4,yy=margin.top+i*(height-margin.top-margin.bottom)/4;
      svg+=`<line class="chart-gridline" x1="${margin.left}" x2="${width-margin.right}" y1="${yy}" y2="${yy}"></line><text class="chart-label" x="${margin.left-8}" y="${yy+4}" text-anchor="end">${xml(format(value))}</text>`;
    }
    rows.forEach((row,index)=>{
      const bx=margin.left+index*band+(band-barWidth)/2,by=y(row.value),bh=height-margin.bottom-by;
      svg+=`<rect class="${row.className||'bar-comp'}" x="${bx}" y="${by}" width="${barWidth}" height="${Math.max(0,bh)}" rx="5"><title>${xml(`${row.label}: ${format(row.value)}${row.note?`\n${row.note}`:''}`)}</title></rect><text class="chart-label" x="${bx+barWidth/2}" y="${height-45}" text-anchor="middle">${xml(row.label.length>14?row.label.slice(0,13)+'…':row.label)}</text><text class="chart-title-label" x="${bx+barWidth/2}" y="${Math.max(14,by-6)}" text-anchor="middle">${xml(format(row.value))}</text>`;
    });
    svg+='</svg>';
    host.innerHTML=svg+(options.footer?`<p class="data-note">${esc(options.footer)}</p>`:'');
  }

  function horizontalBarChart(hostId, rows, options={}) {
    const host=$(hostId);
    if(!rows.length){host.innerHTML='<div class="chart-empty">Insufficient data</div>';return;}
    const shown=rows.slice(0,10),width=720,rowHeight=34,height=35+shown.length*rowHeight+25,margin={left:190,right:55,top:20,bottom:25};
    const max=Math.max(1,...shown.map(row=>number(row.value)))*1.08;
    const format=options.format||Math.round;
    let svg=`<svg class="market-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${xml(options.ariaLabel||'Ranked bar chart')}">`;
    shown.forEach((row,index)=>{
      const y=margin.top+index*rowHeight,widthValue=number(row.value)*(width-margin.left-margin.right)/max;
      svg+=`<text class="chart-label" x="${margin.left-8}" y="${y+18}" text-anchor="end">${xml(row.label.length>25?row.label.slice(0,24)+'…':row.label)}</text><rect class="${row.className||'bar-comp'}" x="${margin.left}" y="${y+5}" width="${Math.max(1,widthValue)}" height="18" rx="4"><title>${xml(`${row.label}: ${format(row.value)}${row.note?`\n${row.note}`:''}`)}</title></rect><text class="chart-title-label" x="${Math.min(width-5,margin.left+widthValue+6)}" y="${y+19}">${xml(format(row.value))}</text>`;
    });
    svg+='</svg>';
    host.innerHTML=svg;
  }

  function divergingBarChart(hostId, rows) {
    const host=$(hostId);
    if(!rows.length){host.innerHTML='<div class="chart-empty">Insufficient data</div>';return;}
    const width=720,rowHeight=42,height=30+rows.length*rowHeight+20,center=360,max=Math.max(1,...rows.map(row=>Math.abs(number(row.value))))*1.15,usable=300;
    let svg=`<svg class="market-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Amenity RevPAR premium chart"><line class="chart-axis" x1="${center}" x2="${center}" y1="10" y2="${height-20}"></line>`;
    rows.forEach((row,index)=>{
      const y=20+index*rowHeight,bar=number(row.value)*usable/max;
      const x=bar>=0?center:center+bar;
      svg+=`<text class="chart-label" x="8" y="${y+18}">${xml(row.label)}</text><rect class="${bar>=0?'bar-own':'bar-comp'}" x="${x}" y="${y+5}" width="${Math.max(1,Math.abs(bar))}" height="18" rx="4"><title>${xml(`${row.label}: ${money(row.value)} RevPAR difference\nWith ${row.withCount} comps · Without ${row.withoutCount} comps`)}</title></rect><text class="chart-title-label" x="${bar>=0?center+bar+6:center+bar-6}" y="${y+19}" text-anchor="${bar>=0?'start':'end'}">${xml(`${row.value>=0?'+':''}${money(row.value)}`)}</text>`;
    });
    svg+=`<text class="chart-label" x="${center-8}" y="${height-4}" text-anchor="end">Lower RevPAR</text><text class="chart-label" x="${center+8}" y="${height-4}">Higher RevPAR</text></svg>`;
    host.innerHTML=svg;
  }

  function reviewChart() {
    const comps=selectedComps().filter(comp=>comp.rating>0);
    const host=$('miReviewChart');
    if(!comps.length){host.innerHTML='<div class="chart-empty">No rating data</div>';return;}
    const width=720,height=370,margin={left:60,right:20,top:20,bottom:50};
    const xMax=Math.max(10,...comps.map(comp=>comp.reviews));
    const x=value=>margin.left+Math.log10(1+number(value))/Math.log10(1+xMax)*(width-margin.left-margin.right);
    const y=value=>height-margin.bottom-(number(value)-3.5)/1.5*(height-margin.top-margin.bottom);
    let svg=`<svg class="market-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Rating versus review count">`;
    [3.5,4,4.5,5].forEach(value=>{const yy=y(value);svg+=`<line class="chart-gridline" x1="${margin.left}" x2="${width-margin.right}" y1="${yy}" y2="${yy}"></line><text class="chart-label" x="${margin.left-8}" y="${yy+4}" text-anchor="end">${value.toFixed(1)}</text>`;});
    [0,10,50,100,250,500].filter(v=>v<=xMax*1.15).forEach(value=>{const xx=x(value);svg+=`<line class="chart-gridline" x1="${xx}" x2="${xx}" y1="${margin.top}" y2="${height-margin.bottom}"></line><text class="chart-label" x="${xx}" y="${height-25}" text-anchor="middle">${value}</text>`;});
    comps.forEach(comp=>svg+=`<circle class="point-comp" cx="${x(comp.reviews)}" cy="${y(comp.rating)}" r="${4+similarity(comp)/35}" opacity=".8"><title>${xml(`${comp.name}\nRating ${comp.rating.toFixed(2)}\n${comp.reviews} reviews\nSimilarity ${similarity(comp)}%`)}</title></circle>`);
    svg+=`<text class="chart-title-label" x="${(margin.left+width-margin.right)/2}" y="${height-5}" text-anchor="middle">Review count (log scale)</text><text class="chart-title-label" transform="translate(14 ${(margin.top+height-margin.bottom)/2}) rotate(-90)" text-anchor="middle">Rating</text></svg>`;
    host.innerHTML=svg;
  }

  function renderCharts() {
    const comps=selectedComps();
    const platformCounts=[...new Set(comps.map(c=>c.platform))].map(platform=>({label:platform,value:comps.filter(c=>c.platform===platform).length,className:'bar-comp'}));
    verticalBarChart('miPlatformChart',platformCounts,{format:value=>Math.round(value),ariaLabel:'Public comp count by platform'});
    const buckets=[
      {label:'Sleeps 5–6',value:comps.filter(c=>c.guests>=5&&c.guests<=6).length,className:'bar-own'},
      {label:'Sleeps 7–8',value:comps.filter(c=>c.guests>=7&&c.guests<=8).length,className:'bar-comp'},
      {label:'Sleeps 9+',value:comps.filter(c=>c.guests>=9).length,className:'bar-comp'},
      {label:'Unknown',value:comps.filter(c=>!c.guests).length,className:'bar-comp'}
    ].filter(row=>row.value>0);
    verticalBarChart('miGuestCountChart',buckets,{format:value=>Math.round(value),ariaLabel:'Guest capacity distribution'});

    const metricComps=comps.filter(comp=>annual(comp).adr>0 || annual(comp).occupancy>0 || annual(comp).revenue>0);
    const noMetrics='<div class="chart-empty">No licensed or consistently observed monthly competitor performance data is bundled. Use the rate-observation template or a future provider import.</div>';
    if(metricComps.length){
      const actual=app.property.actuals;
      lineChart('miAdrChart',MONTHS,[{name:app.property.name,values:actual.map(i=>i.adr),className:'line-own',pointClass:'point-own',legendClass:'legend-own'},{name:'Comp median',values:monthlyComp('adr'),className:'line-comp',pointClass:'point-comp',legendClass:'legend-comp'}],{format:money});
      lineChart('miOccupancyChart',MONTHS,[{name:app.property.name,values:actual.map(i=>i.occupancy),className:'line-own',pointClass:'point-own',legendClass:'legend-own'},{name:'Comp median',values:monthlyComp('occupancy'),className:'line-comp',pointClass:'point-comp',legendClass:'legend-comp'}],{min:0,max:100,format:v=>`${Math.round(v)}%`});
      lineChart('miRevparChart',MONTHS,[{name:app.property.name,values:actual.map(i=>i.adr*i.occupancy/100),className:'line-own',pointClass:'point-own',legendClass:'legend-own'},{name:'Comp median',values:monthlyComp('revpar'),className:'line-comp',pointClass:'point-comp',legendClass:'legend-comp'}],{format:money});
      lineChart('miRevenueChart',MONTHS,[{name:app.property.name,values:actual.map(i=>i.revenue),className:'line-own',pointClass:'point-own',legendClass:'legend-own'},{name:'Comp median',values:monthlyComp('revenue'),className:'line-comp',pointClass:'point-comp',legendClass:'legend-comp'}],{format:money});
      scatterChart();
    } else ['miAdrChart','miOccupancyChart','miRevparChart','miRevenueChart','miScatterChart','miAmenityChart','miCapacityChart'].forEach(id=>$(id).innerHTML=noMetrics);

    const observed=comps.flatMap(comp=>(comp.observations||[]).map(item=>({label:item.checkIn||item.observedAt,ownRate:0,compMedian:number(item.nightlyRate)}))).filter(item=>item.compMedian>0);
    if(observed.length) lineChart('miFutureChart',observed.map(i=>i.label),[{name:'Observed public nightly rate',values:observed.map(i=>i.compMedian),className:'line-comp',pointClass:'point-comp',legendClass:'legend-comp'}],{format:money});
    else $('miFutureChart').innerHTML='<div class="chart-empty">No consistent-date public rate series yet. Download the observation queue and add repeated snapshots.</div>';

    const ranking=comps.map(comp=>({label:comp.name,value:similarity(comp),note:`${comp.platform} · ${comp.locationName||'location not published'}`})).sort((a,b)=>b.value-a.value);
    horizontalBarChart('miRankingChart',ranking,{format:value=>`${Math.round(value)}%`,ariaLabel:'Comparable similarity ranking'});
    reviewChart();
  }

  function renderObservationPlan(){
    const host=$('miObservationPlan'); if(!host)return;
    const rows=[
      ['Weekday · 30 days','Monthly','2 nights · 6 guests'],['Weekend · 30 days','Monthly','2 nights · 6 guests'],
      ['Weekday · 60 days','Monthly','2 nights · 6 guests'],['Weekend · 60 days','Monthly','2 nights · 6 guests'],
      ['Weekday · 90 days','Monthly','2 nights · 6 guests'],['Weekend · 90 days','Monthly','2 nights · 6 guests'],
      ['Holiday/event','Quarterly','3 nights · 6 guests'],['Sleeps-eight scenario','Quarterly','2 nights · 8 guests']
    ];
    host.innerHTML=`<div class="table-scroll"><table><thead><tr><th>Observation window</th><th>Cadence</th><th>Standard search</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join('')}</tbody></table></div><p class="data-note">Record exact check-in/out dates, guest count, total price, whether taxes/fees are included, availability status, source URL, and observation time. Do not infer occupancy from blocked dates.</p>`;
  }

  function renderCompTable() {
    const search=app.search.toLowerCase();
    const rows=app.property.comps.filter(comp=>!search || `${comp.name} ${comp.platform} ${comp.sourceLabel}`.toLowerCase().includes(search));
    if(!rows.length){$('miCompTable').innerHTML='<p class="muted">No comparable properties match the search.</p>';return;}
    $('miCompTable').innerHTML=`<div class="table-scroll"><table class="comp-table"><thead><tr><th>Use</th><th>Comparable</th><th>Match</th><th>Property facts</th><th>Performance</th><th>Reviews</th><th>Source</th><th>Action</th></tr></thead><tbody>${rows.map(comp=>{
      const a=annual(comp),score=similarity(comp);
      const amenities=Object.entries(comp.amenities).filter(([,enabled])=>enabled).map(([key])=>({hotTub:'Hot tub',arcade:'Arcade',fireplace:'Fireplace',resortAmenities:'Resort',petFriendly:'Pet friendly',evCharger:'EV charger'}[key])).join(', ')||'—';
      return `<tr class="${comp.included?'':'excluded'}"><td><input type="checkbox" data-mi-action="toggle" data-id="${esc(comp.id)}" ${comp.included?'checked':''} aria-label="Include ${esc(comp.name)}"></td><td><strong>${esc(comp.name)}</strong><br><span class="pill platform-pill">${esc(comp.platform)}</span>${comp.listingUrl?`<br><a href="${esc(comp.listingUrl)}" target="_blank" rel="noopener">Public listing</a>`:''}</td><td><div class="score-meter"><div class="score-bar"><span style="width:${score}%"></span></div><strong>${score}%</strong></div><span class="data-note">${comp.distanceMiles===null||comp.distanceMiles===undefined?'Distance not published':comp.distanceMiles.toFixed(1)+' mi'}</span></td><td>${comp.bedrooms} BR · ${comp.bathrooms} BA<br>Sleeps ${comp.guests} · ${comp.beds||'—'} beds<br><span class="data-note">${esc(amenities)}</span></td><td>${a.adr||a.occupancy||a.revenue?`ADR ${money(a.adr)}<br>Occ. ${pct(a.occupancy)}<br>RevPAR ${money(a.revpar)}<br>Revenue ${money(a.revenue)}/mo`:'No performance claim'}<br><span class="data-note">${(comp.observations||[]).length} rate observation(s)</span></td><td>${comp.rating?comp.rating.toFixed(2):'—'} ★<br>${Math.round(comp.reviews||0)} reviews</td><td><select data-mi-action="source" data-id="${esc(comp.id)}"><option ${comp.sourceLabel==='Public listing metadata'?'selected':''}>Public listing metadata</option><option ${comp.sourceLabel==='Manual estimate'?'selected':''}>Manual estimate</option><option ${comp.sourceLabel==='Observed public price'?'selected':''}>Observed public price</option><option ${comp.sourceLabel==='Provider estimate'?'selected':''}>Provider estimate</option></select></td><td><button class="danger small-button" data-mi-action="remove" data-id="${esc(comp.id)}">Remove</button></td></tr>`;
    }).join('')}</tbody></table></div>`;
    $('miCompTable').querySelectorAll('[data-mi-action]').forEach(el=>{
      const action=el.dataset.miAction,id=el.dataset.id;
      if(action==='toggle') el.addEventListener('change',()=>{const comp=app.property.comps.find(item=>item.id===id);comp.included=el.checked;save();renderAll();});
      if(action==='source') el.addEventListener('change',()=>{const comp=app.property.comps.find(item=>item.id===id);comp.sourceLabel=el.value;save();renderAll();});
      if(action==='remove') el.addEventListener('click',()=>{if(confirm('Remove this comparable from the browser workspace?')){app.property.comps=app.property.comps.filter(item=>item.id!==id);save();renderAll();}});
    });
  }

  function renderActuals() {
    $('miActualsTable').innerHTML=`<div class="table-scroll"><table><thead><tr><th>Month</th><th>ADR</th><th>Occupancy %</th><th>Revenue</th><th>Source</th></tr></thead><tbody>${app.property.actuals.map((item,index)=>`<tr><td>${item.month}</td><td><input class="actual-input" type="number" min="0" data-actual="adr" data-index="${index}" value="${item.adr}"></td><td><input class="actual-input" type="number" min="0" max="100" data-actual="occupancy" data-index="${index}" value="${item.occupancy}"></td><td><input class="actual-input" type="number" min="0" data-actual="revenue" data-index="${index}" value="${item.revenue}"></td><td><span class="source-label">${esc(item.sourceLabel)}</span></td></tr>`).join('')}</tbody></table></div>`;
    $('miActualsTable').querySelectorAll('[data-actual]').forEach(input=>input.addEventListener('change',()=>{
      const item=app.property.actuals[number(input.dataset.index)];
      item[input.dataset.actual]=number(input.value);
      item.sourceLabel='Browser-entered actual';save();renderSummary();renderCharts();
    }));
  }

  function renderAll() {
    renderSummary(); renderCharts(); renderCompTable(); renderActuals(); renderObservationPlan();
  }

  function parseCSV(text) {
    const rows=[];let row=[],field='',quoted=false;
    for(let i=0;i<text.length;i++){
      const char=text[i],next=text[i+1];
      if(char==='"'&&quoted&&next==='"'){field+='"';i++;continue;}
      if(char==='"'){quoted=!quoted;continue;}
      if(char===','&&!quoted){row.push(field);field='';continue;}
      if((char==='\n'||char==='\r')&&!quoted){if(char==='\r'&&next==='\n')i++;row.push(field);field='';if(row.some(cell=>cell.trim()!==''))rows.push(row);row=[];continue;}
      field+=char;
    }
    row.push(field);if(row.some(cell=>cell.trim()!==''))rows.push(row);
    if(rows.length<2) return [];
    const headers=rows[0].map(value=>value.trim().toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,''));
    return rows.slice(1).map(cells=>Object.fromEntries(headers.map((header,index)=>[header,cells[index]??''])));
  }

  const pick=(row,...keys)=>{for(const key of keys){if(row[key]!==undefined&&row[key]!=='')return row[key];}return '';};

  function compsFromCSV(rows) {
    const groups=new Map();
    rows.forEach((row,index)=>{
      const name=pick(row,'listing_name','name','title')||`Imported comparable ${index+1}`;
      const platform=pick(row,'platform','channel','provider')||'Other';
      const id=String(pick(row,'listing_id','provider_listing_id','id')||`${slugify(platform)}-${slugify(name)}`);
      if(!groups.has(id)) groups.set(id,{id,name,platform,listingUrl:pick(row,'listing_url','url'),included:true,distanceMiles:number(pick(row,'distance_miles','distance')),bedrooms:number(row.bedrooms),bathrooms:number(row.bathrooms),guests:number(pick(row,'guests','accommodates','capacity')),beds:number(row.beds),rating:number(row.rating),reviews:number(pick(row,'review_count','reviews')),amenities:{hotTub:bool(pick(row,'hot_tub','hottub')),arcade:bool(pick(row,'arcade','game_room')),fireplace:bool(row.fireplace),resortAmenities:bool(row.resort_amenities),petFriendly:bool(row.pet_friendly),evCharger:bool(row.ev_charger)},sourceLabel:pick(row,'data_source','source_label')||'Manual estimate',metrics:[]});
      const comp=groups.get(id);
      const month=monthName(pick(row,'month','month_start','date'));
      const adr=number(pick(row,'adr','estimated_adr','average_daily_rate'));
      const occupancy=number(pick(row,'occupancy','estimated_occupancy','occupancy_percent'));
      const revenue=number(pick(row,'revenue','estimated_revenue','monthly_revenue'),adr*occupancy/100*30.4);
      comp.metrics.push({month,adr,occupancy,revenue});
    });
    return [...groups.values()].map(normalizeComp);
  }

  function importComps(comps) {
    const existing=new Map(app.property.comps.map(comp=>[comp.id,comp]));
    comps.forEach(comp=>existing.set(comp.id,comp));
    app.property.comps=[...existing.values()];
    save();renderAll();message(`Imported ${comps.length} comparable listing(s).`);
  }

  function csvEscape(value) {
    const text=String(value??'');
    return /[",\n]/.test(text)?`"${text.replace(/"/g,'""')}"`:text;
  }

  function exportAnalysis() {
    const headers=['property_code','comparable_name','platform','included','similarity_percent','distance_miles','bedrooms','bathrooms','guests','rating','reviews','annual_adr','annual_occupancy','annual_revpar','average_monthly_revenue','source_label'];
    const rows=app.property.comps.map(comp=>{const a=annual(comp);return [app.property.code,comp.name,comp.platform,comp.included,similarity(comp),comp.distanceMiles,comp.bedrooms,comp.bathrooms,comp.guests,comp.rating,comp.reviews,a.adr.toFixed(2),a.occupancy.toFixed(2),a.revpar.toFixed(2),a.revenue.toFixed(2),comp.sourceLabel];});
    download(`${app.property.slug}-market-analysis.csv`,[headers,...rows].map(row=>row.map(csvEscape).join(',')).join('\n'),'text/csv;charset=utf-8');
  }

  function addManualComp(form) {
    const data=new FormData(form),adr=number(data.get('adr')),occupancy=number(data.get('occupancy')),revenue=number(data.get('revenue'),adr*occupancy/100*30.4);
    const name=String(data.get('name')||'Manual comparable');
    const comp=normalizeComp({id:`manual-${Date.now()}-${slugify(name)}`,name,platform:data.get('platform'),distanceMiles:data.get('distanceMiles'),bedrooms:data.get('bedrooms'),bathrooms:data.get('bathrooms'),guests:data.get('guests'),rating:data.get('rating'),reviews:data.get('reviews'),adr,occupancy,revenue,sourceLabel:data.get('sourceLabel'),amenities:{hotTub:data.has('hotTub'),arcade:data.has('arcade'),fireplace:data.has('fireplace'),resortAmenities:data.has('resortAmenities')}});
    app.property.comps.push(comp);save();renderAll();form.reset();message('Manual comparable added.');
  }

  function bindEvents(demoWorkspace) {
    $('miPropertySelector').addEventListener('change',()=>{app.property=app.workspace.properties.find(property=>property.slug===$('miPropertySelector').value);storage.set(PROPERTY_KEY,app.property.slug);syncProfileInputs();renderAll();});
    $('miProfile').addEventListener('change',()=>applyPreset($('miProfile').value));
    ['miAddress','miRadius','miBedroomsMin','miBedroomsMax','miBathroomsMin','miBathroomsMax','miGuestsMin','miGuestsMax','miRequireHotTub','miRequireArcade'].forEach(id=>$(id).addEventListener('change',readProfileInputs));
    $('miApplyProfile').addEventListener('click',()=>{readProfileInputs();app.property.comps.forEach(comp=>comp.included=profileMatches(comp));save();renderAll();message(`Profile applied: ${selectedComps().length} comparable(s) included.`);});
    $('miResetDemo').addEventListener('click',()=>{if(confirm('Replace the browser workspace with the bundled v4.2.1 real public snapshot?')){app.workspace=clone(demoWorkspace);app.property=app.workspace.properties.find(property=>property.slug==='arbor-vista-retreat')||app.workspace.properties[0];save();populatePropertySelector();syncProfileInputs();renderAll();message('Real public snapshot reloaded.');}});
    $('miCompSearch').addEventListener('input',()=>{app.search=$('miCompSearch').value;renderCompTable();});
    $('miIncludeAll').addEventListener('click',()=>{app.property.comps.forEach(comp=>comp.included=true);save();renderAll();});
    $('miExcludeAll').addEventListener('click',()=>{app.property.comps.forEach(comp=>comp.included=false);save();renderAll();});
    $('miAddCompForm').addEventListener('submit',event=>{event.preventDefault();addManualComp(event.currentTarget);});
    $('miCsvInput').addEventListener('change',async event=>{try{const file=event.target.files[0];if(!file)return;const rows=parseCSV(await file.text());const comps=compsFromCSV(rows);if(!comps.length)throw new Error('No usable rows found.');importComps(comps);}catch(error){message(error.message,true);}finally{event.target.value='';}});
    $('miJsonInput').addEventListener('change',async event=>{try{const file=event.target.files[0];if(!file)return;const workspace=normalizeWorkspace(JSON.parse(await file.text()));app.workspace=workspace;app.property=workspace.properties[0];save();populatePropertySelector();syncProfileInputs();renderAll();message('Workspace imported.');}catch(error){message(`Workspace import failed: ${error.message}`,true);}finally{event.target.value='';}});
    $('miExportWorkspace').addEventListener('click',()=>download(`${app.property.slug}-market-workspace.json`,JSON.stringify(app.workspace,null,2),'application/json'));
    $('miExportAnalysis').addEventListener('click',exportAnalysis);
  }

  function populatePropertySelector() {
    const selector=$('miPropertySelector');
    selector.innerHTML=app.workspace.properties.map(property=>`<option value="${esc(property.slug)}">${esc(property.code)} · ${esc(property.name)}</option>`).join('');
    selector.value=app.property.slug;
  }

  async function init() {
    try {
      let demoData = window.ARBOR_MARKET_REAL_SNAPSHOT || window.ARBOR_MARKET_DEMO_DATA;
      if (!demoData) {
        const response=await fetch('data/market-intelligence-real-snapshot.json',{cache:'no-store'});
        if(!response.ok) throw new Error('Real snapshot data file could not be loaded.');
        demoData=await response.json();
      }
      const demoWorkspace=normalizeWorkspace(demoData);
      let workspace=demoWorkspace;
      try {const stored=storage.get(STORAGE_KEY);if(stored)workspace=normalizeWorkspace(JSON.parse(stored));} catch(error){console.warn('Ignoring invalid saved workspace',error);}
      app.workspace=workspace;
      const requested=storage.get(PROPERTY_KEY);
      app.property=workspace.properties.find(property=>property.slug===requested)||workspace.properties[0];
      populatePropertySelector();syncProfileInputs();bindEvents(demoWorkspace);renderAll();
    } catch(error) {
      document.querySelector('.market-main').innerHTML=`<section class="notice warning"><strong>Market Intelligence could not start.</strong><br>${esc(error.message)}<br><br>Confirm that the complete package—including <code>admin/data/market-intelligence-real-snapshot.json</code>—was uploaded to GitHub.</section>`;
    }
  }

  init();
})();
