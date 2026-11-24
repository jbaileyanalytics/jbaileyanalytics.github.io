const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
class Element {
  constructor(basis) { this.dataset = basis ? {marketBasis:basis} : {}; this.listeners = {}; this.attributes = {}; this.innerHTML = ''; this.textContent = ''; }
  addEventListener(name, handler) { this.listeners[name] = handler; }
  setAttribute(name, value) { this.attributes[name] = value; }
}
const elements = new Map();
const buttons = [new Element('previous'),new Element('session')];
const document = {getElementById(id) { if (!elements.has(id)) elements.set(id,new Element()); return elements.get(id); }, querySelectorAll() { return buttons; }};
const market = {date:'2024-01-03',total_symbols:2,stocks:[
  {stock_id:1,ticker:'ABC',close:'110',change_pct:'-8.333',previous_close_change_pct:'10',previous_close_date:'2024-01-02'},
  {stock_id:2,ticker:'NEW',close:'11',change_pct:'10',previous_close_change_pct:null}
]};
(async () => {
  await vm.runInNewContext(fs.readFileSync(path.join(root,'website/market-overview.js'),'utf8'), {document,fetch:async()=>({ok:true,json:async()=>market}),Intl,Date,Number,String,Math,console});
  assert.match(elements.get('heatmap').innerHTML,/ABC[^]*\+10\.00%/);
  assert.match(elements.get('heatmap').innerHTML,/NEW[^]*N\/A/);
  assert.match(elements.get('gainers').innerHTML,/ABC/);
  buttons[1].listeners.click();
  assert.equal(buttons[1].attributes['aria-pressed'],'true');
  assert.match(elements.get('heatmap').innerHTML,/ABC[^]*-8\.33%/);
  assert.match(elements.get('gainers').innerHTML,/NEW/);
  assert.match(elements.get('losers').innerHTML,/ABC/);
  console.log('Both market comparisons, unavailable values, and rankings passed.');
})().catch(error => {console.error(error);process.exitCode=1;});
