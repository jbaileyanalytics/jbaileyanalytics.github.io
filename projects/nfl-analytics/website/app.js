'use strict';
const $ = id => document.getElementById(id);
const state = {seasons: [], rows: [], scoped: [], players: [], focus: 'Receiving', request: 0, from: 1, to: 1};
const settings = {
  Receiving: {op: 'targets', yards: 'receiving_yards', td: 'receiving_tds', label: 'Targets', rate: 'Yards / target'},
  Rushing: {op: 'carries', yards: 'rushing_yards', td: 'rushing_tds', label: 'Carries', rate: 'Yards / carry'},
  Passing: {op: 'attempts', yards: 'passing_yards', td: 'passing_tds', label: 'Pass attempts', rate: 'Yards / attempt'}
};
const nf = new Intl.NumberFormat('en-US');
const safe = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function options(el, values, label = x => x, selected) {
  el.replaceChildren(...values.map(v => { const o=document.createElement('option'); o.value=String(v); o.textContent=label(v); return o; }));
  if (selected !== undefined && values.some(v => String(v) === String(selected))) el.value=String(selected);
}
async function readJson(url) { const response=await fetch(url); if(!response.ok) throw new Error(`Could not load ${url} (${response.status}).`); return response.json(); }
async function loadSeason() {
  const season=Number($('season').value), meta=state.seasons.find(x=>x.season===season);
  const request=++state.request;
  $('error').hidden=true; $('scope').textContent='Loading snapshot…';
  try {
    const data=await readJson(`data/${season}.json`);
    if(request!==state.request)return;
    if (!Array.isArray(data.fields) || !data.fields.includes('passing_interceptions') || !Array.isArray(data.records) || data.records.length!==meta.records) throw new Error('The snapshot is incomplete or needs to be regenerated.');
    state.rows=data.records.map(row=>Object.fromEntries(data.fields.map((field,i)=>[field,row[i]])));
    $('hero-season').textContent=`${season} SEASON`;
    $('hero-players').textContent=nf.format(meta.players);
    $('hero-records').textContent=nf.format(meta.records);
    $('hero-weeks').textContent=String(meta.weeks.length);
    options($('team'),['all',...new Set(state.rows.map(r=>r.team))].sort((a,b)=>a==='all'?-1:b==='all'?1:a.localeCompare(b)),x=>x==='all'?'All teams':x);
    options($('week-from'),meta.weeks,x=>`Week ${x}`,meta.weeks[0]);
    options($('week-to'),meta.weeks,x=>`Week ${x}`,meta.weeks.at(-1));
    $('position').value='all';
    render();
  } catch(error) { if(request!==state.request)return; $('results').hidden=true; $('error').hidden=false; $('error').textContent=`Snapshot could not be loaded: ${error.message} Run export_website.py to prepare the local data.`; }
}
function aggregate(rows, config, minimum) {
  const byId=new Map();
  rows.forEach(r=>{
    let p=byId.get(r.player_id);
    if(!p){p={id:r.player_id,name:r.player_display_name,position:r.position,teams:new Set(),weeks:0,op:0,yards:0,td:0,completions:0,receptions:0,interceptions:0};byId.set(r.player_id,p);}
    p.teams.add(r.team); p.weeks++; p.op+=r[config.op]; p.yards+=r[config.yards]; p.td+=r[config.td];
    p.completions+=r.completions; p.receptions+=r.receptions; p.interceptions+=r.passing_interceptions;
    if(!p.latest || r.week>=p.latest){p.latest=r.week;p.name=r.player_display_name;p.position=r.position;}
  });
  return [...byId.values()].filter(p=>p.op>=minimum && p.op>0).map(p=>({...p,rate:p.yards/p.op,teams:[...p.teams].sort().join(', ')})).sort((a,b)=>b.yards-a.yards||a.id.localeCompare(b.id));
}
function render() {
  const meta=state.seasons.find(x=>x.season===Number($('season').value)), config=settings[$('focus').value];
  const from=Number($('week-from').value), to=Number($('week-to').value), team=$('team').value, position=$('position').value;
  const minimum=Math.max(1,Math.min(1000,Number($('minimum').value)||1));
  if(from>to){$('results').hidden=true;$('error').hidden=false;$('error').textContent='Choose a starting week that is not after the ending week.';return;}
  $('error').hidden=true; $('results').hidden=false;
  const rows=state.rows.filter(r=>r.week>=from&&r.week<=to&&(team==='all'||r.team===team)&&(position==='all'||r.position===position));
  const players=aggregate(rows,config,minimum); state.players=players; state.scoped=rows; state.focus=$('focus').value; state.from=from; state.to=to;
  const totalOp=players.reduce((a,p)=>a+p.op,0), totalYards=players.reduce((a,p)=>a+p.yards,0);
  const now=new Date(),year=now.getUTCFullYear(), month=now.getUTCMonth()+1;
  const currentSeason=meta.season===year&&month>=7 || meta.season===year-1&&month<3;
  const period=currentSeason?'IN-PROGRESS SNAPSHOT · MAY BE INCOMPLETE':'HISTORICAL SNAPSHOT';
  $('scope').innerHTML=`<strong>${safe(meta.season)} ${period}</strong> &nbsp; / &nbsp; WEEKS ${from}–${to} &nbsp; / &nbsp; ${safe(team==='all'?'ALL TEAMS':team)} &nbsp; / &nbsp; ${safe(position==='all'?'ALL POSITIONS':position)} &nbsp; / &nbsp; SNAPSHOT RETRIEVED ${safe(meta.retrieved_at_utc.slice(0,10))} UTC`;
  $('k-players').textContent=nf.format(players.length);$('k-volume').textContent=nf.format(totalOp);$('k-yards').textContent=nf.format(totalYards);$('k-eff').textContent=totalOp?(totalYards/totalOp).toFixed(2):'—';
  $('k-volume-label').textContent=config.label.toUpperCase();$('k-yards-label').textContent=`${state.focus.toUpperCase()} YARDS`;$('k-eff-label').textContent=config.rate.toUpperCase();
  if(!players.length){$('leaders').innerHTML='<p class="empty">No qualifying players. Try a lower minimum or broader filters.</p>';$('weekly-chart').innerHTML='';$('comparison').innerHTML='<p class="muted">No players available to compare.</p>';$('profile-name').textContent='No qualifying player';$('profile-context').textContent='Adjust the filters or minimum opportunity threshold.';$('profile-stats').replaceChildren();$('profile-chart').replaceChildren();$('profile-weekly-table').replaceChildren();$('profile-summary').textContent='';options($('profile-player'),[]);options($('player-a'),[]);options($('player-b'),[]);return;}
  const top=players.slice(0,8), max=Math.max(...top.map(p=>p.yards),1);
  $('leaders').innerHTML=top.map((p,i)=>`<div class="leader-row"><span class="leader-rank">${String(i+1).padStart(2,'0')}</span><div><div class="leader-name">${safe(p.name)}</div><div class="leader-sub">${safe(p.position)} &nbsp; / &nbsp; ${safe(p.teams)} &nbsp; / &nbsp; ${nf.format(p.op)} ${safe(config.label.toLowerCase())}</div></div><div class="leader-bar" aria-hidden="true"><i style="width:${Math.max(0,p.yards/max*100)}%"></i></div><div class="leader-yards">${nf.format(p.yards)}<small>YARDS</small></div></div>`).join('');
  const ids=new Set(players.map(p=>p.id)), weeks=[];
  for(let week=from;week<=to;week++){const wr=rows.filter(r=>r.week===week&&ids.has(r.player_id));const op=wr.reduce((a,r)=>a+r[config.op],0), yards=wr.reduce((a,r)=>a+r[config.yards],0);weeks.push({week,op,yards,rate:op?yards/op:null});}
  const signed=weeks.some(w=>w.rate!==null&&w.rate<0), maxRate=Math.max(0,...weeks.map(w=>Math.abs(w.rate??0)));
  $('weekly-chart').innerHTML=weeks.map(w=>{
    const height=w.rate===null?0:Math.max(1,maxRate?Math.abs(w.rate)/maxRate*(signed?50:100):0);
    const style=signed?`position:absolute;${w.rate<0?'top':'bottom'}:50%;height:${height}%`:`height:${height}%`;
    const label=signed||w.rate===null?'':`<span class="week-bar-value" style="--bar-height:${height}%">${w.rate.toFixed(1)}</span>`;
    return `<div class="week-col"><div class="week-bar-wrap">${signed?'<span class="zero-line" aria-hidden="true"></span>':''}${w.rate===null?'':`${label}<div class="week-bar ${w.rate<0?'negative':''}" style="${style}" title="Week ${w.week}: ${w.rate.toFixed(2)} ${safe(config.rate.toLowerCase())} · ${nf.format(w.op)} ${safe(config.label.toLowerCase())}" aria-label="Week ${w.week}: ${w.rate.toFixed(2)} ${safe(config.rate.toLowerCase())}"></div>`}</div><small>${w.week}</small></div>`;
  }).join('');
  $('trend-label').textContent=`${config.rate.toUpperCase()} · WEEKS ${from}–${to}`;
  const prevA=$('player-a').value,prevB=$('player-b').value,prevProfile=$('profile-player').value,idsList=players.map(p=>p.id),labels=new Map(players.map(p=>[p.id,`${p.name} · ${p.teams} · ${p.id}`]));
  options($('profile-player'),idsList,x=>labels.get(x),idsList.includes(prevProfile)?prevProfile:idsList[0]);
  options($('player-a'),idsList,x=>labels.get(x),idsList.includes(prevA)?prevA:idsList[0]);
  options($('player-b'),idsList,x=>labels.get(x),idsList.includes(prevB)?prevB:(idsList[1]||idsList[0]));
  compare(); profile();
}
function profile(){
  const p=state.players.find(player=>player.id===$('profile-player').value);
  if(!p)return;
  const config=settings[state.focus], rows=state.scoped.filter(r=>r.player_id===p.id).sort((a,b)=>a.week-b.week);
  $('profile-name').textContent=p.name;
  $('profile-context').textContent=`${p.position}  /  ${p.teams}  /  ${state.focus.toUpperCase()}  /  ${p.weeks} OBSERVED PLAYER-WEEKS`;
  const stats=state.focus==='Passing'
    ? [['PASS ATTEMPTS',nf.format(p.op)],['COMPLETIONS',nf.format(p.completions)],['COMPLETION RATE',`${(p.completions/p.op*100).toFixed(1)}%`],['PASSING YARDS',nf.format(p.yards)],['PASSING TDS',nf.format(p.td)],['INTERCEPTIONS',nf.format(p.interceptions)]]
    : state.focus==='Receiving'
      ? [['TARGETS',nf.format(p.op)],['RECEPTIONS',nf.format(p.receptions)],['CATCH RATE',`${(p.receptions/p.op*100).toFixed(1)}%`],['RECEIVING YARDS',nf.format(p.yards)],['RECEIVING TDS',nf.format(p.td)],['YARDS / TARGET',p.rate.toFixed(2)]]
      : [['CARRIES',nf.format(p.op)],['RUSHING YARDS',nf.format(p.yards)],['RUSHING TDS',nf.format(p.td)],['YARDS / CARRY',p.rate.toFixed(2)],['OBSERVED WEEKS',nf.format(p.weeks)]];
  $('profile-stats').innerHTML=stats.map(([label,value])=>`<div class="profile-stat"><span>${safe(label)}</span><strong>${safe(value)}</strong></div>`).join('');
  const values=rows.map(r=>r[config.yards]), high=Math.max(...values), low=Math.min(...values), avg=values.reduce((a,b)=>a+b,0)/values.length;
  const highWeeks=rows.filter(r=>r[config.yards]===high).map(r=>r.week).join(', '), lowWeeks=rows.filter(r=>r[config.yards]===low).map(r=>r.week).join(', ');
  $('profile-summary').textContent=`${avg.toFixed(1)} yards per observed week · high ${nf.format(high)} (week${highWeeks.includes(',')?'s':''} ${highWeeks}) · low ${nf.format(low)} (week${lowWeeks.includes(',')?'s':''} ${lowWeeks})`;
  $('profile-chart-unit').textContent=`${state.focus.toUpperCase()} YARDS`;
  const byWeek=new Map(rows.map(r=>[r.week,r])), maxAbs=Math.max(1,...values.map(Math.abs)), signed=values.some(v=>v<0);
  let chart='';
  for(let week=state.from;week<=state.to;week++){
    const r=byWeek.get(week);
    if(!r){chart+=`<div class="profile-week is-missing"><div class="profile-week-value">—</div><div class="profile-bar-area"><span class="profile-missing">No record</span></div><span class="profile-week-label">${week}</span></div>`;continue;}
    const yards=r[config.yards], height=Math.abs(yards)/maxAbs*(signed?50:100), style=signed?`${yards<0?'top':'bottom'}:50%;height:${height}%`:`bottom:0;height:${height}%`;
    chart+=`<div class="profile-week"><div class="profile-week-value">${nf.format(yards)}</div><div class="profile-bar-area">${signed?'<span class="profile-zero" aria-hidden="true"></span>':''}<span class="profile-bar ${yards<0?'is-negative':''}" style="${style}" title="Week ${week}: ${nf.format(yards)} yards, ${nf.format(r[config.op])} ${safe(config.label.toLowerCase())}" aria-label="Week ${week}: ${nf.format(yards)} yards, ${nf.format(r[config.op])} ${safe(config.label.toLowerCase())}"></span></div><span class="profile-week-label">${week}</span></div>`;
  }
  $('profile-chart').innerHTML=chart;
  $('profile-op-header').textContent=config.label;
  $('profile-weekly-table').innerHTML=Array.from({length:state.to-state.from+1},(_,i)=>state.from+i).map(week=>{
    const r=byWeek.get(week);return r?`<tr><th scope="row">${week}</th><td>${safe(r.team)}</td><td>${safe(r.opponent_team)}</td><td>${nf.format(r[config.op])}</td><td>${nf.format(r[config.yards])}</td><td>${nf.format(r[config.td])}</td></tr>`:`<tr><th scope="row">${week}</th><td colspan="5" class="missing-cell">No included record</td></tr>`;
  }).join('');
}
function compare(){
  const a=state.players.find(p=>p.id===$('player-a').value),b=state.players.find(p=>p.id===$('player-b').value); if(!a||!b)return;
  const config=settings[state.focus];
  const lines=[['Team(s)',a.teams,b.teams],['Observed weeks',a.weeks,b.weeks],[config.label,a.op,b.op],['Yards',a.yards,b.yards],['Touchdowns',a.td,b.td],[config.rate,a.rate.toFixed(2),b.rate.toFixed(2)]];
  if(state.focus==='Passing') lines.push(['Completions',a.completions,b.completions],['Completion rate',`${(a.completions/a.op*100).toFixed(1)}%`,`${(b.completions/b.op*100).toFixed(1)}%`],['Interceptions',a.interceptions,b.interceptions]);
  if(state.focus==='Receiving') lines.push(['Receptions',a.receptions,b.receptions],['Catch rate',`${(a.receptions/a.op*100).toFixed(1)}%`,`${(b.receptions/b.op*100).toFixed(1)}%`]);
  $('comparison').innerHTML=`<div class="compare-header"><span>${safe(a.name)}</span><span>SELECTED SCOPE</span><span>${safe(b.name)}</span></div>`+lines.map(([label,left,right])=>`<div class="compare-row"><span>${safe(typeof left==='number'?nf.format(left):left)}</span><span>${safe(label.toUpperCase())}</span><span>${safe(typeof right==='number'?nf.format(right):right)}</span></div>`).join('');
}
for(const id of ['focus','team','position','week-from','week-to','minimum']) $(id).addEventListener('change',render);
$('season').addEventListener('change',loadSeason);$('player-a').addEventListener('change',compare);$('player-b').addEventListener('change',compare);$('profile-player').addEventListener('change',profile);
$('reset').addEventListener('click',()=>{$('focus').value='Receiving';$('minimum').value=30;loadSeason();});
(async()=>{try{state.seasons=(await readJson('data/seasons.json')).sort((a,b)=>b.season-a.season);if(!state.seasons.length)throw new Error('No snapshots available');options($('season'),state.seasons.map(s=>s.season));await loadSeason();}catch(e){$('error').hidden=false;$('results').hidden=true;$('error').textContent=`Data unavailable: ${e.message} Run export_website.py to prepare the local snapshots.`;}})();
