const DATA = '../results/reporting-v1/website/';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = value => value === null || value === undefined || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
const price = value => {const n = number(value); return n === null ? '—' : new Intl.NumberFormat('en-US', {minimumFractionDigits:2, maximumFractionDigits:4}).format(n);};
const chartPrice = value => new Intl.NumberFormat('en-US', {minimumFractionDigits:2, maximumFractionDigits:2}).format(value);
const dateLabel = value => value ? new Date(value + 'T12:00:00Z').toLocaleDateString('en-US', {timeZone:'UTC', month:'short', day:'numeric', year:'numeric'}) : '—';
const pct = value => {const n = number(value); return n === null ? '—' : `${n > 0 ? '+' : ''}${n.toFixed(2)}%`;};
const tone = value => {const n = number(value); return n === null || n === 0 ? 'neutral' : n > 0 ? 'positive' : 'negative';};
let active, index = [], page = 0, loadCounter = 0, chartRange = "1Y", chartRows = [], chartIndex = 0;
const pageSize = 15;

async function json(url) {const response = await fetch(url); if (!response.ok) throw new Error(`Unable to load ${url} (${response.status}).`); return response.json();}
function returnRow(label, result) {return `<tr><td>${esc(label)}</td><td class="${tone(result.percent)}">${pct(result.percent)}${result.reason ? `<small>${esc(result.reason)}</small>` : ''}</td><td>${dateLabel(result.baseline_date)}</td></tr>`;}
function chart(rows) {
  const points = rows.map((r,i) => ({i, v:number(r.close)})).filter(p => p.v !== null);
  if (!points.length) return '<p class="muted">No valid closes available for this period.</p>';
  const w=900,h=230,pad=20,min=Math.min(...points.map(p=>p.v)),max=Math.max(...points.map(p=>p.v));
  const x=i=>pad+(w-2*pad)*(rows.length>1?i/(rows.length-1):.5), y=v=>pad+(h-2*pad)*(max===min?.5:(max-v)/(max-min));
  let path='', drawing=false; rows.forEach((r,i)=>{const v=number(r.close);if(v===null){drawing=false;return;}path+=`${drawing?'L':'M'}${x(i).toFixed(1)},${y(v).toFixed(1)} `;drawing=true;});
  const last=points[points.length-1];
  const dots=rows.length<=35 ? points.map(p=>`<circle cx="${x(p.i)}" cy="${y(p.v)}" r="3" fill="#31d6a2" vector-effect="non-scaling-stroke"/>`).join('') : '';
  return `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#2bd4a0" stop-opacity=".12"/><stop offset="1" stop-color="#2bd4a0" stop-opacity="0"/></linearGradient></defs><line x1="20" y1="${pad}" x2="880" y2="${pad}" stroke="#283a40" stroke-dasharray="4 6"/><line x1="20" y1="${h-pad}" x2="880" y2="${h-pad}" stroke="#283a40" stroke-dasharray="4 6"/><path d="${path}" fill="none" stroke="#31d6a2" stroke-width="2.5" vector-effect="non-scaling-stroke"/>${dots}<circle cx="${x(last.i)}" cy="${y(last.v)}" r="4" fill="#31d6a2"/><line id="chart-guide" x1="0" x2="0" y1="20" y2="210" stroke="#8ebbb0" stroke-dasharray="4 5" visibility="hidden"/><circle id="chart-marker" r="5" fill="#c9fff0" stroke="#14785f" stroke-width="2" visibility="hidden"/></svg><span class="chart-bound chart-bound-high">High ${chartPrice(max)}</span><span class="chart-bound chart-bound-low">Low ${chartPrice(min)}</span>`;
}
function renderPriceChart() {
  if (!active) return;
  const rows = active.daily.map(r => ({date:r[0], close:r[4]}));
  const end = rows.length ? rows[rows.length-1].date : null;
  if (!end) { chartRows=[]; $('chart').innerHTML=chart([]); return; }
  let start = null;
  if (chartRange === 'YTD') start = end.slice(0,4)+'-01-01';
  else if (chartRange !== 'ALL' && chartRange !== '5D') {
    const months = {'1M':1,'6M':6,'1Y':12,'5Y':60}[chartRange];
    const [year,month,day] = end.split('-').map(Number);
    const target = new Date(Date.UTC(year,month-1-months,1));
    const last = new Date(Date.UTC(target.getUTCFullYear(),target.getUTCMonth()+1,0)).getUTCDate();
    target.setUTCDate(Math.min(day,last)); start=target.toISOString().slice(0,10);
  }
  chartRows=chartRange==='5D' ? rows.slice(-5) : rows.filter(r=>!start||r.date>=start);
  $('chart').innerHTML=chart(chartRows);
  $('chart-start').textContent=chartRows.length?dateLabel(chartRows[0].date):'—';
  $('chart-end').textContent=chartRows.length?dateLabel(chartRows[chartRows.length-1].date):'—';
  $('chart-note').textContent=chartRange==='1Y' && active.overview.range_52_weeks.starts_within_window ? 'Less than 52 weeks of source history is available.' : 'Daily observations in the selected period; missing trading days and price adjustments are not independently verified.';
  chartIndex=Math.max(0,chartRows.length-1);
  showChartValue();
}
function showChartValue() {
  const row=chartRows[chartIndex]; $('chart-value').textContent=row?`${dateLabel(row.date)} · Close ${price(row.close)}`:'No observations';
  const svg=$('chart').querySelector?.('svg'), guide=svg?.querySelector('#chart-guide'), marker=svg?.querySelector('#chart-marker');
  if (!guide || !marker || !row) return;
  const valid=chartRows.map(r=>number(r.close)).filter(v=>v!==null), value=number(row.close);
  if (!valid.length || value===null) {guide.setAttribute('visibility','hidden');marker.setAttribute('visibility','hidden');return;}
  const min=Math.min(...valid), max=Math.max(...valid), x=20+860*(chartRows.length>1?chartIndex/(chartRows.length-1):.5), y=20+190*(max===min?.5:(max-value)/(max-min));
  guide.setAttribute('x1',x);guide.setAttribute('x2',x);guide.setAttribute('visibility','visible');marker.setAttribute('cx',x);marker.setAttribute('cy',y);marker.setAttribute('visibility','visible');
}
$('chart').addEventListener('pointermove',event=>{if(!chartRows.length)return;const rect=$('chart').getBoundingClientRect();const fraction=Math.max(0,Math.min(1,((event.clientX-rect.left)/rect.width*900-20)/860));chartIndex=Math.round(fraction*(chartRows.length-1));showChartValue();});
$('chart').addEventListener('keydown',event=>{if(!chartRows.length||!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();chartIndex=event.key==='Home'?0:event.key==='End'?chartRows.length-1:Math.max(0,Math.min(chartRows.length-1,chartIndex+(event.key==='ArrowLeft'?-1:1)));showChartValue();});
$('chart-controls').addEventListener('click',event=>{const button=event.target.closest('button[data-range]');if(!button)return;chartRange=button.dataset.range;for(const item of $('chart-controls').querySelectorAll('button')){const selected=item===button;item.classList.toggle('active',selected);item.setAttribute('aria-pressed',String(selected));}renderPriceChart();});

function range(label, low, high, current) {
  const l=number(low), h=number(high), c=number(current), position=l!==null&&h!==null&&c!==null&&h>l?Math.max(0,Math.min(100,(c-l)/(h-l)*100)):null;
  return `<div class="range"><div class="range-label"><span>${label}</span><span>LOW / HIGH</span></div><div class="range-values"><span>${price(low)}</span><span>${price(high)}</span></div><div class="range-track">${position===null?'':`<i style="left:${position}%"></i>`}</div></div>`;
}
function selectedHistory(){ if ($('frequency').value==='daily') return active.daily.map(r=>({period_start:r[0],open:r[1],high:r[2],low:r[3],close:r[4],observations:1})).reverse(); return active[$('frequency').value].slice().reverse(); }
function renderHistory(){const rows=selectedHistory(), pages=Math.max(1,Math.ceil(rows.length/pageSize));page=Math.max(0,Math.min(page,pages-1));$('price-rows').innerHTML=rows.slice(page*pageSize,(page+1)*pageSize).map(r=>`<tr><td>${dateLabel(r.period_start)}${r.period_ends_after_latest_observation?' *':''}</td><td>${price(r.open)}</td><td>${price(r.high)}</td><td>${price(r.low)}</td><td>${price(r.close)}</td><td>${r.observations}</td></tr>`).join('');$('page-info').textContent=`Page ${page+1} of ${pages} · ${rows.length.toLocaleString()} periods`;$('prev').disabled=page===0;$('next').disabled=page>=pages-1;}
function render(data){active=data;page=0;const o=data.overview,r=o.range_52_weeks;$('ticker').textContent=o.ticker;$('asof').textContent=`Last observation ${dateLabel(o.latest_observation_date)}`;$('snapshot-date').textContent=`${o.ticker} DATA THROUGH ${dateLabel(o.latest_observation_date).toUpperCase()}`;$('latest-close').textContent=price(o.latest_close);
  const previous=number(o.previous_close), latest=number(o.latest_close), change=previous&&latest!==null?(latest/previous-1)*100:null;$('day-change').textContent=change===null?'Previous close unavailable':`${pct(change)} from previous close · ${dateLabel(o.previous_close_date)}`;$('day-change').className=tone(change);
  $('performance-cards').innerHTML=['YTD','1 year','3 years','5 years'].map(k=>{const v=o.returns[k];return `<div class="kpi"><span>${esc(k.toUpperCase())}</span><strong class="${tone(v.percent)}">${pct(v.percent)}</strong><span>${v.reason?esc(v.reason):`From ${dateLabel(v.baseline_date)}`}</span></div>`;}).join('');
  renderPriceChart();
  $('ranges').innerHTML=range('DAY RANGE',o.latest_low,o.latest_high,o.latest_close)+range(r.starts_within_window?'AVAILABLE HISTORY RANGE':'52-WEEK RANGE',r.low,r.high,o.latest_close);$('stats').innerHTML=[['Previous close',o.previous_close],['Open',o.latest_open],['Day high',o.latest_high],['Day low',o.latest_low]].map(([k,v])=>`<div><span>${k}</span><strong>${price(v)}</strong></div>`).join('');
  $('annual-rows').innerHTML=o.annual_price_returns.slice().reverse().map(v=>returnRow(`${v.year}${v.partial?' (partial)':''}`,v)).join('');$('trailing-rows').innerHTML=Object.entries(o.returns).map(([k,v])=>returnRow(k,v)).join('');const items=Object.entries(data.quality_summary);$('quality-count').textContent=items.reduce((s,[,n])=>s+n,0).toLocaleString();$('quality-detail').textContent=items.length?items.map(([k,n])=>`${k.replaceAll('_',' ')}: ${n.toLocaleString()}`).join(' · '):'No field-level issues identified by the current checks.';renderHistory();$('dashboard').hidden=false;
}
async function loadStock(id){const selected=index.find(s=>String(s.stock_id)===String(id));if(!selected)return;const request=++loadCounter;$('status').className='notice';$('status').textContent=`Loading ${selected.ticker}…`;try{const data=await json(DATA+selected.data_file);if(request!==loadCounter)return;render(data);$('status').textContent='NASDAQ stocks in this dataset · Historical data only · Currency and adjustment treatment are unverified · Closing-price changes; dividend and split adjustments unverified';}catch(e){if(request!==loadCounter)return;$('dashboard').hidden=true;$('status').className='notice error';$('status').textContent=e.message;}}
$('stock-select').addEventListener('change',e=>loadStock(e.target.value));$('frequency').addEventListener('change',()=>{page=0;renderHistory();});$('prev').addEventListener('click',()=>{page--;renderHistory();});$('next').addEventListener('click',()=>{page++;renderHistory();});$('download').addEventListener('click',()=>{const rows=selectedHistory(),fields=['period_start','open','high','low','close','observations'];const body=[fields.join(','),...rows.map(r=>fields.map(f=>r[f]??'').join(','))].join('\n');const blob=new Blob([body],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`${active.overview.ticker}-${$('frequency').value}-prices.csv`;a.click();URL.revokeObjectURL(url);});
(async()=>{try{index=await json(DATA+'stocks.json');if(!index.length)throw new Error('The reporting package contains no stocks.');const select=$('stock-select');select.replaceChildren(...index.map(s=>{const option=document.createElement('option');option.value=s.stock_id;option.textContent=s.ticker;return option;}));select.disabled=false;const initial=index.find(s=>s.ticker==='AAPL')||index[0];select.value=initial.stock_id;await loadStock(initial.stock_id);}catch(e){$('status').className='notice error';$('status').textContent=`${e.message} Serve the portfolio folder locally and ensure the reporting export exists.`;}})();
