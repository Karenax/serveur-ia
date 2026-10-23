/* Exercise the exact registered stdio MCP server against a disposable local UI. */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const http = require('node:http');
const readline = require('node:readline');
const {spawn, execFileSync} = require('node:child_process');
const {pathToFileURL} = require('node:url');
const root = path.resolve(__dirname, '../..');
const python = process.env.PYTHON_EXE || path.join(root, 'toolchain/eg2-python/Scripts/python.exe');
const configFile = path.join(process.env.CODEX_HOME || path.join(os.homedir(), '.codex'), 'config.toml');
const config = JSON.parse(execFileSync(python, ['-X', 'utf8', '-c', 'import json,sys,tomllib; print(json.dumps(tomllib.load(open(sys.argv[1],"rb"))["mcp_servers"]["playwright"]))', configFile], {encoding: 'utf8'}));
assert(config.enabled !== false, 'Playwright MCP is disabled');
const output = path.join(__dirname, 'validation/mcp');
fs.mkdirSync(output, {recursive: true});
const fixture = `<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Validation UX locale</title>
<style>body{font:16px/1.5 system-ui;margin:32px;max-width:600px;color:#242423;background:white}label,input,button{display:block;margin:12px 0}input,button{font:inherit;padding:8px;max-width:100%;box-sizing:border-box}button:focus-visible,input:focus-visible{outline:3px solid #327854;outline-offset:3px}</style>
<main><h1>Nouveau projet</h1><form><label for="name">Nom du projet</label><input id="name" required autocomplete="off"><button type="submit">Créer le projet</button></form><p role="status">Aucun projet</p></main>
<script>document.querySelector('form').onsubmit=event=>{event.preventDefault();document.querySelector('[role=status]').textContent='Projet créé : '+document.querySelector('input').value}</script></html>`;
const server = http.createServer((req, res) => {res.writeHead(200, {'content-type': 'text/html; charset=utf-8'}); res.end(fixture);});
let child, reader, serial = 0, log = [], pending = new Map();
function send(message) {child.stdin.write(JSON.stringify(message) + '\n');}
function request(method, params = {}) {
  const id = ++serial;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {pending.delete(id); reject(Error('MCP timeout: ' + method));}, 60000);
    pending.set(id, {resolve: value => {clearTimeout(timer); resolve(value);}, reject: error => {clearTimeout(timer); reject(error);}});
    send({jsonrpc: '2.0', id, method, params});
  });
}
async function tool(name, args) {
  const result = await request('tools/call', {name, arguments: args});
  let text = (result.content || []).filter(c => c.type === 'text').map(c => c.text).join('\n');
  // Recent MCP versions return snapshots as files instead of inline YAML.
  const snapshot = text.match(/\[Snapshot\]\(([^)]+)\)/);
  if (snapshot) text += '\n' + fs.readFileSync(snapshot[1], 'utf8');
  log.push({tool: name, arguments: args, text});
  assert(!result.isError, text);
  return text;
}
function ref(snapshot, role, label) {
  const line = snapshot.split('\n').find(line => line.includes(role + ' "' + label + '"') && /\[ref=/.test(line));
  assert(line, 'Accessible element not found: ' + role + ' ' + label + '\n' + snapshot);
  return line.match(/\[ref=([^\]]+)\]/)[1];
}
(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  child = spawn(config.command, config.args || [], {cwd: root, env: {...process.env, ...(config.env || {})}, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true});
  child.stderr.on('data', data => fs.appendFileSync(path.join(output, 'server-stderr.txt'), data));
  child.on('error', error => {for (const item of pending.values()) item.reject(error); pending.clear();});
  child.on('exit', code => {for (const item of pending.values()) item.reject(Error('MCP exited: ' + code)); pending.clear();});
  reader = readline.createInterface({input: child.stdout});
  reader.on('line', line => {
    let message;
    try {message = JSON.parse(line);} catch {return;}
    if (message.method && message.id !== undefined) {
      send({jsonrpc: '2.0', id: message.id, result: message.method === 'roots/list' ? {roots: [{uri: pathToFileURL(root + path.sep).href, name: 'Fred'}]} : {}});
    } else if (message.id !== undefined && pending.has(message.id)) {
      const item = pending.get(message.id); pending.delete(message.id);
      if (message.error) item.reject(Error(JSON.stringify(message.error))); else item.resolve(message.result);
    }
  });
  try {
    const initialized = await request('initialize', {protocolVersion: '2024-11-05', capabilities: {roots: {listChanged: false}}, clientInfo: {name: 'fred-ux-install-validation', version: '1.0.0'}});
    send({jsonrpc: '2.0', method: 'notifications/initialized'});
    const listed = await request('tools/list');
    fs.writeFileSync(path.join(output, 'tools.json'), JSON.stringify(listed.tools.map(t => ({name: t.name, inputSchema: t.inputSchema})), null, 2));
    const needed = ['browser_navigate', 'browser_snapshot', 'browser_type', 'browser_click', 'browser_resize', 'browser_take_screenshot', 'browser_evaluate', 'browser_press_key'];
    for (const name of needed) assert(listed.tools.some(t => t.name === name), 'Missing tool ' + name);
    await tool('browser_resize', {width: 1440, height: 900});
    let snapshot = await tool('browser_navigate', {url: 'http://127.0.0.1:' + server.address().port});
    assert(snapshot.includes('Aucun projet'));
    await tool('browser_type', {target: ref(snapshot, 'textbox', 'Nom du projet'), text: 'Projet de validation'});
    await tool('browser_press_key', {key: 'Tab'});
    const focused = await tool('browser_evaluate', {function: '() => document.activeElement.textContent'});
    assert(focused.includes('Créer le projet'));
    snapshot = await tool('browser_snapshot', {});
    await tool('browser_click', {target: ref(snapshot, 'button', 'Créer le projet')});
    snapshot = await tool('browser_snapshot', {});
    assert(snapshot.includes('Projet créé : Projet de validation'));
    await tool('browser_take_screenshot', {type: 'png', scale: 'css', filename: path.join(output, 'desktop.png'), fullPage: true});
    await tool('browser_resize', {width: 390, height: 844});
    const overflow = await tool('browser_evaluate', {function: '() => ({overflow: document.documentElement.scrollWidth > innerWidth})'});
    assert(/"overflow"\s*:\s*false/.test(overflow));
    await tool('browser_take_screenshot', {type: 'png', scale: 'css', filename: path.join(output, 'phone.png'), fullPage: true});
    const result = {passed: true, server: initialized.serverInfo, tools: listed.tools.length, transport: 'registered stdio config', checks: ['initialize', 'tools/list', 'accessible snapshot', 'type', 'Tab focus', 'click', 'success state', 'desktop and phone screenshots', 'phone overflow'], scope: 'Disposable localhost fixture; application coverage is provided separately by existing UI suites'};
    fs.writeFileSync(path.join(output, 'result.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result, null, 2));
  } finally {
    fs.writeFileSync(path.join(output, 'transcript.json'), JSON.stringify(log, null, 2));
    try {await tool('browser_close', {});} catch {}
    reader.close();
    await new Promise(resolve => {child.once('exit', resolve); child.stdin.end(); const timer = setTimeout(() => {child.kill(); resolve();}, 3000); timer.unref();});
    server.closeAllConnections(); server.close();
  }
})().catch(error => {console.error(error); if (child) child.kill(); server.closeAllConnections(); server.close(); process.exitCode = 1;});
