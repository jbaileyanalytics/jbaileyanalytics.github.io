// Lightweight behavioral check using the real exported snapshot and a minimal DOM.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
class Element {
  constructor() { this.listeners = {}; this.children = []; this.value = ''; this.textContent = ''; this.innerHTML = ''; this.hidden = true; }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  replaceChildren(...children) { this.children = children; }
}
const elements = new Map();
const document = { getElementById(id) { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); }, createElement() { return new Element(); } };
document.getElementById('frequency').value = 'daily';
const fetch = async url => {
  const local = path.join(root, 'results/reporting-v1/website', url.replace('../results/reporting-v1/website/', ''));
  return { ok: fs.existsSync(local), status: fs.existsSync(local) ? 200 : 404,
    json: async () => JSON.parse(fs.readFileSync(local, 'utf8')) };
};
const context = {document, fetch, console, Intl, Date, Number, String, Math, Blob, URL};
(async () => {
  await vm.runInNewContext(fs.readFileSync(path.join(root, 'website/app.js'), 'utf8'), context);
  assert.equal(document.getElementById('ticker').textContent, 'AAPL');
  assert.equal(document.getElementById('dashboard').hidden, false);
  assert.match(document.getElementById('latest-close').textContent, /352\.78/);
  const select = document.getElementById('stock-select');
  const arxs = select.children.find(option => option.textContent === 'ARXS');
  await select.listeners.change({target: {value: arxs.value}});
  assert.equal(document.getElementById('ticker').textContent, 'ARXS');
  assert.match(document.getElementById('chart-note').textContent, /Less than 52 weeks/);
  assert.match(document.getElementById('performance-cards').innerHTML, /insufficient history/);
  document.getElementById('frequency').value = 'weekly';
  document.getElementById('frequency').listeners.change();
  assert.match(document.getElementById('page-info').textContent, /periods/);
  console.log('Website data loading, stock selection, coverage and history checks passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
