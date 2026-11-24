/* Market comparisons use the latest recorded dataset date, never a live quote. */
(async () => {
  const element = id => document.getElementById(id);
  const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const percentage = n => `${n > 0 ? '+' : ''}${n.toFixed(2)}%`;
  const displayDate = value => new Date(value+'T12:00:00Z').toLocaleDateString('en-US',{timeZone:'UTC',month:'long',day:'numeric',year:'numeric'});
  try {
    const response = await fetch('../results/reporting-v1/website/market-overview.json');
    if (!response.ok) throw new Error('Market overview data is unavailable.');
    const market = await response.json();
    const controls = document.querySelectorAll('[data-market-basis]');
    let basis = 'previous';
    const change = s => {
      const value = basis === 'previous' ? s.previous_close_change_pct : s.change_pct;
      return value === null || value === undefined || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
    };
    const render = () => {
      const label = basis === 'previous' ? 'Previous close to close' : 'Open to close';
      const stocks = market.stocks.map(s => ({...s, change:change(s)}));
      const eligible = stocks.filter(s => s.change !== null);
      const ranked = eligible.slice().sort((a,b)=>b.change-a.change||a.ticker.localeCompare(b.ticker));
      element('market-date').textContent = `SESSION / ${displayDate(market.date).toUpperCase()}`;
      element('market-context').textContent = `${eligible.length} of ${market.total_symbols} symbols have valid prices for this comparison on ${displayDate(market.date)}. This is not live data.`;
      element('market-measure').textContent = `${label} · equal-sized tiles`;
      element('movers-measure').textContent = `Ranked by ${label.toLowerCase()} change`;
      element('movers-note').textContent = basis === 'previous'
        ? 'Uses the previous valid recorded close, which may not be the previous trading day. Only symbols with valid prices are ranked.'
        : 'Uses the same session’s valid open and close. Only symbols with valid prices are ranked.';
      controls.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.marketBasis === basis)));
      const tile = s => {
        if (s.change === null) return `<button type="button" class="heat-tile heat-tile-unavailable" data-stock="${s.stock_id}" aria-label="${escape(s.ticker)} ${label}: unavailable"><strong>${escape(s.ticker)}</strong><span>N/A</span></button>`;
        const intensity=Math.min(Math.abs(s.change)/5,1), rgb=s.change>0?'18, 135, 105':s.change<0?'190, 58, 75':'80, 96, 105';
        const previousDate = basis === 'previous' && s.previous_close_date ? `; previous close ${displayDate(s.previous_close_date)}` : '';
        return `<button type="button" class="heat-tile" data-stock="${s.stock_id}" style="background:rgba(${rgb},${(.30+.65*intensity).toFixed(2)})" aria-label="${escape(s.ticker)} ${percentage(s.change)} ${label.toLowerCase()}${previousDate}"><strong>${escape(s.ticker)}</strong><span>${percentage(s.change)}</span></button>`;
      };
      element('heatmap').innerHTML = stocks.map(tile).join('');
      const list = (title, values) => `<h4>${title}</h4>${values.length?values.map(s=>`<button type="button" class="mover-row" data-stock="${s.stock_id}"><strong>${escape(s.ticker)}</strong><span>${Number(s.close).toFixed(2)}</span><b class="${s.change>=0?'positive':'negative'}">${percentage(s.change)}</b></button>`).join(''):'<p class="footnote">None for this comparison.</p>'}`;
      element('gainers').innerHTML = list('Top gainers',ranked.filter(s=>s.change>0).slice(0,5));
      element('losers').innerHTML = list('Top losers',ranked.filter(s=>s.change<0).slice(-5).reverse());
    };
    controls.forEach(button => button.addEventListener('click', () => { basis=button.dataset.marketBasis; render(); }));
    render();
    element('market').addEventListener('click',e=>{const selected=e.target.closest('[data-stock]');if(!selected)return;const select=element('stock-select');select.value=selected.dataset.stock;select.dispatchEvent(new Event('change'));element('performance').scrollIntoView({behavior:'smooth',block:'start'});});
  } catch (error) { element('market-context').textContent = `${error.message} Generate the local market overview to use this view.`; }
})();
