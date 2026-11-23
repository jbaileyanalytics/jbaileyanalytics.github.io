/* Market overview uses the latest common observed date, never a live quote. */
(async () => {
  const element = id => document.getElementById(id);
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const percentage = n => `${n > 0 ? '+' : ''}${n.toFixed(2)}%`;
  const displayDate = value => new Date(value+'T12:00:00Z').toLocaleDateString('en-US',{timeZone:'UTC',month:'long',day:'numeric',year:'numeric'});
  try {
    const response = await fetch('../results/reporting-v1/website/market-overview.json');
    if (!response.ok) throw new Error('Market overview data is unavailable.');
    const market = await response.json();
    const stocks = market.stocks.map(s=>({...s, change:Number(s.change_pct)})).filter(s=>Number.isFinite(s.change));
    element('market-date').textContent = `SESSION / ${displayDate(market.date).toUpperCase()}`;
    element('market-context').textContent = `${market.eligible_symbols} of ${market.total_symbols} symbols have valid prices for ${displayDate(market.date)}. This is not live data.`;
    const ranked = stocks.slice().sort((a,b)=>b.change-a.change||a.ticker.localeCompare(b.ticker));
    const tile = s => {const intensity=Math.min(Math.abs(s.change)/5,1), rgb=s.change>0?'18, 135, 105':s.change<0?'190, 58, 75':'80, 96, 105';return `<button type="button" class="heat-tile" data-stock="${s.stock_id}" style="background:rgba(${rgb},${(.30+.65*intensity).toFixed(2)})" aria-label="${escape(s.ticker)} ${percentage(s.change)} open to close"><strong>${escape(s.ticker)}</strong><span>${percentage(s.change)}</span></button>`;};
    element('heatmap').innerHTML = stocks.map(tile).join('');
    const list = (title, values) => `<h4>${title}</h4>${values.length?values.map(s=>`<button type="button" class="mover-row" data-stock="${s.stock_id}"><strong>${escape(s.ticker)}</strong><span>${Number(s.close).toFixed(2)}</span><b class="${s.change>=0?'positive':'negative'}">${percentage(s.change)}</b></button>`).join(''):'<p class="footnote">None in this session.</p>'}`;
    element('gainers').innerHTML = list('Top gainers',ranked.filter(s=>s.change>0).slice(0,5));
    element('losers').innerHTML = list('Top losers',ranked.filter(s=>s.change<0).slice(-5).reverse());
    element('market').addEventListener('click',e=>{const selected=e.target.closest('[data-stock]');if(!selected)return;const select=element('stock-select');select.value=selected.dataset.stock;select.dispatchEvent(new Event('change'));element('performance').scrollIntoView({behavior:'smooth',block:'start'});});
  } catch (error) { element('market-context').textContent = `${error.message} Generate the local market overview to use this view.`; }
})();
