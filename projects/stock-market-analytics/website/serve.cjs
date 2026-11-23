// Local-only preview server. Serves the dashboard and its exported website data.
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const {execFile} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const port = Number(process.env.MARKETSCOPE_PORT || 8765);
const candidate = process.argv.includes('--candidate');
const candidateRoot = path.join(root, 'results', 'kaggle-refresh-v841', 'site');
const mime = {'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8',
  '.js':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8'};
http.createServer((req, res) => {
  try {
    let pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    if (candidate && (pathname === '/' || pathname === '/website/')) pathname = '/index.html';
    else if (!candidate && (pathname === '/' || pathname === '/website/')) pathname = '/website/index.html';
    const target = path.resolve(candidate ? candidateRoot : root, '.' + pathname);
    const allowed = candidate ? [candidateRoot + path.sep] : [path.join(root, 'website') + path.sep, path.join(root, 'results', 'reporting-v1', 'website') + path.sep];
    if (!allowed.some(prefix => target.startsWith(prefix)) || !mime[path.extname(target)]) {
      res.writeHead(404).end('Not found'); return;
    }
    const file = fs.createReadStream(target);
    file.on('error', () => { if (!res.headersSent) res.writeHead(404); res.end('Not found'); });
    res.setHeader('Content-Type', mime[path.extname(target)]);
    res.setHeader('Cache-Control', 'no-store');
    file.pipe(res);
  } catch { res.writeHead(400).end('Invalid request'); }
}).on('error', error => {
  console.error(`Could not start the dashboard server: ${error.message}`);
  process.exitCode = 1;
}).listen(port, '127.0.0.1', () => {
  const url = `http://127.0.0.1:${port}${candidate ? '/' : '/website/'}`;
  console.log(`MarketScope local preview: ${url}`);
  if (process.argv.includes('--open') && process.platform === 'win32') {
    execFile('rundll32.exe', ['url.dll,FileProtocolHandler', url], error => {
      if (error) console.error(`Open this address in your browser: ${url}`);
    });
  }
});
