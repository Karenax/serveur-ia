// Uses the configured MCP transport itself; no application dependency is added.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import http from 'node:http';
import readline from 'node:readline';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const project = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.join(project, 'logs/ux-quality');
fs.mkdirSync(output, { recursive: true });
const configPath = path.join(process.env.CODEX_HOME || path.join(os.homedir(), '.codex'), 'config.toml');
const config = spawnSync('python', ['-c', 'import tomllib,json,sys; c=tomllib.load(open(sys.argv[1],"rb")); print(json.dumps(c["mcp_servers"]["playwright"]))', configPath], { encoding: 'utf8', windowsHide: true });
if (config.status !== 0) throw new Error(`Configuration Playwright indisponible: ${config.stderr}`);
const serverConfig = JSON.parse(config.stdout);
if (serverConfig.enabled === false) throw new Error('Serveur Playwright désactivé.');
const appIndex = process.argv.indexOf('--app');
const appUrl = appIndex < 0 ? null : process.argv[appIndex + 1];
if (appIndex >= 0 && (!appUrl || !/^http:\/\/(?:127\.0\.0\.1|localhost):8001\/app(?:[/?#]|$)/.test(appUrl))) throw new Error('--app attend une URL de consultation Agent sur 8001/app.');
const runId = new Date().toISOString().replaceAll(/[:.]/g, '-');
const report = { timestamp: new Date().toISOString(), transport: 'configured stdio MCP', package: '@playwright/mcp@0.0.83', steps: [], scope: appUrl ? 'fixture + read-only Agent page' : 'fictitious fixture only', currentChatMcpLoaded: false };
const fixture = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
  res.end(`<!doctype html><html lang="fr"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Recette UX fictive</title><style>body{font:16px system-ui;max-width:42rem;margin:2rem;padding:1rem}button,input{font:inherit;padding:.6rem}label{display:block;margin:1rem 0}button:focus-visible,input:focus-visible{outline:3px solid #164bad;outline-offset:3px}</style><main><h1>Projet fictif</h1><form><label>Nom du projet <input name="project" required></label><button>Enregistrer</button><p role="status"></p></form></main><script>document.querySelector('form').onsubmit=e=>{e.preventDefault();document.querySelector('[role=status]').textContent='Enregistré'}</script></html>`);
});
await new Promise(resolve => fixture.listen(0, '127.0.0.1', resolve));
const child = spawn(serverConfig.command, serverConfig.args ?? [], { cwd: serverConfig.cwd || project, env: { ...process.env, ...(serverConfig.env ?? {}) }, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
let stderr = '';
child.stderr.on('data', data => { stderr = (stderr + data).slice(-8000); });
const pending = new Map();
let nextId = 0;
function send(payload) { child.stdin.write(JSON.stringify(payload) + '\n'); }
const reader = readline.createInterface({ input: child.stdout });
reader.on('line', line => {
  let message;
  try { message = JSON.parse(line); } catch { return; }
  if (message.method === 'roots/list' && message.id !== undefined) {
    send({ jsonrpc: '2.0', id: message.id, result: { roots: [{ uri: new URL(`file:///${project.replaceAll('\\', '/')}`).href, name: 'Agent' }] } });
  } else if (pending.has(message.id)) {
    const item = pending.get(message.id);
    clearTimeout(item.timer);
    pending.delete(message.id);
    if (message.error) item.reject(new Error(JSON.stringify(message.error)));
    else item.resolve(message.result);
  }
});
child.on('error', error => { for (const item of pending.values()) { clearTimeout(item.timer); item.reject(error); } pending.clear(); });
child.on('exit', code => { for (const item of pending.values()) { clearTimeout(item.timer); item.reject(new Error(`MCP exited ${code}: ${stderr}`)); } pending.clear(); });
function rpc(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++nextId;
    const timer = setTimeout(() => { pending.delete(id); reject(new Error(`Timeout MCP: ${method}`)); }, 60000);
    pending.set(id, { resolve, reject, timer });
    send({ jsonrpc: '2.0', id, method, params });
  });
}
async function call(name, args = {}) {
  const result = await rpc('tools/call', { name, arguments: args });
  if (result.isError) throw new Error(JSON.stringify(result.content));
  report.steps.push({ tool: name, passed: true });
  return result;
}
function saveText(result, suffix) {
  fs.writeFileSync(path.join(output, `${runId}-${suffix}.txt`), result.content?.filter(c => c.type === 'text').map(c => c.text).join('\n') ?? '');
}
try {
  const init = await rpc('initialize', { protocolVersion: '2024-11-05', capabilities: { roots: { listChanged: false } }, clientInfo: { name: 'agent-ux-install-validation', version: '1.0.0' } });
  report.server = init.serverInfo;
  send({ jsonrpc: '2.0', method: 'notifications/initialized' });
  const catalog = await rpc('tools/list');
  report.toolCount = catalog.tools.length;
  report.tools = catalog.tools.map(t => t.name);
  for (const name of ['browser_navigate', 'browser_snapshot', 'browser_fill_form', 'browser_press_key', 'browser_take_screenshot', 'browser_close']) {
    if (!catalog.tools.some(t => t.name === name)) throw new Error(`Outil absent: ${name}`);
  }
  await call('browser_navigate', { url: `http://127.0.0.1:${fixture.address().port}` });
  const snapshot = await call('browser_snapshot');
  saveText(snapshot, 'fixture-snapshot');
  const snapshotText = snapshot.content.filter(c => c.type === 'text').map(c => c.text).join('\n');
  const ref = snapshotText.match(/textbox "Nom du projet"[^\n]*\[ref=([^\]]+)\]/)?.[1];
  if (!ref) throw new Error('Champ fictif absent du snapshot accessible.');
  await call('browser_fill_form', { fields: [{ name: 'Nom du projet', type: 'textbox', target: ref, value: 'Affaire fictive UX' }] });
  await call('browser_press_key', { key: 'Tab' });
  const focus = await call('browser_snapshot');
  if (!focus.content.some(c => c.type === 'text' && /button "Enregistrer"[^\n]*\[active\]/.test(c.text))) throw new Error('Focus clavier incorrect.');
  await call('browser_press_key', { key: 'Enter' });
  const saved = await call('browser_snapshot');
  if (!saved.content.some(c => c.type === 'text' && /Enregistré/.test(c.text))) throw new Error('Enregistrement fictif non confirmé.');
  saveText(saved, 'fixture-saved');
  report.fixtureInteraction = true;
  await call('browser_take_screenshot', { filename: `logs/ux-quality/${runId}-fixture.png`, fullPage: true });
  if (appUrl) {
    await call('browser_navigate', { url: appUrl });
    await call('browser_wait_for', { text: 'Projets' });
    saveText(await call('browser_snapshot'), 'agent-snapshot');
    for (const [width, height] of [[1440, 900], [390, 844]]) {
      await call('browser_resize', { width, height });
      await call('browser_take_screenshot', { filename: `logs/ux-quality/${runId}-agent-${width}.png`, fullPage: true });
    }
    report.agentReadOnlyAccess = true;
  }
  report.passed = true;
} catch (error) {
  report.passed = false;
  report.error = error.message;
  process.exitCode = 1;
} finally {
  try { await call('browser_close'); } catch { /* Keep original failure. */ }
  reader.close();
  child.stdin.end();
  child.kill();
  fixture.closeAllConnections();
  await new Promise(resolve => fixture.close(resolve));
  const reportPath = path.join(output, `${runId}-mcp-report.json`);
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ passed: report.passed, steps: report.steps.length, report: reportPath, error: report.error }));
}
