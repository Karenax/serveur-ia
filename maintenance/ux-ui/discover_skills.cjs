/* Read-only validation through Codex's actual app-server skill discovery API. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const readline = require('node:readline');
const {spawn} = require('node:child_process');
const root = path.resolve(__dirname, '../..');
const child = spawn(process.env.CODEX_CLI_PATH || 'codex', ['app-server'], {cwd: root, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true});
const reader = readline.createInterface({input: child.stdout});
let id = 0;
const pending = new Map();
let stderr = '';
child.stderr.on('data', data => {stderr += data;});
function request(method, params) {
  return new Promise((resolve, reject) => {
    const requestId = ++id;
    const timer = setTimeout(() => {pending.delete(requestId); reject(Error(method + ': timeout\n' + stderr.slice(-1500)));}, 30000);
    pending.set(requestId, {resolve: value => {clearTimeout(timer); resolve(value);}, reject: value => {clearTimeout(timer); reject(value);}});
    child.stdin.write(JSON.stringify({jsonrpc: '2.0', id: requestId, method, params}) + '\n');
  });
}
reader.on('line', line => {
  let message;
  try {message = JSON.parse(line);} catch {return;}
  const item = pending.get(message.id);
  if (!item) return;
  pending.delete(message.id);
  if (message.error) item.reject(Error(JSON.stringify(message.error))); else item.resolve(message.result);
});
child.on('error', error => {for (const item of pending.values()) item.reject(error); pending.clear();});
child.on('exit', code => {for (const item of pending.values()) item.reject(Error('app-server exited: ' + code)); pending.clear();});
(async () => {
  try {
    await request('initialize', {clientInfo: {name: 'fred-ux-skill-discovery', version: '1.0.0'}, capabilities: {experimentalApi: true}});
    child.stdin.write(JSON.stringify({jsonrpc: '2.0', method: 'initialized'}) + '\n');
    const result = await request('skills/list', {cwds: [root], forceReload: true});
    const expected = fs.readdirSync(path.join(root, '.agents/skills')).filter(name => fs.existsSync(path.join(root, '.agents/skills', name, 'SKILL.md')));
    const skills = (result.data || []).flatMap(entry => entry.skills || []);
    const local = skills.filter(skill => expected.includes(skill.name));
    const missing = expected.filter(name => !local.some(skill => skill.name === name && skill.enabled !== false));
    const report = {passed: missing.length === 0, expected, detected: local.map(({name, path, scope, enabled}) => ({name, path, scope, enabled})), missing, errors: (result.data || []).flatMap(entry => entry.errors || [])};
    const output = path.join(__dirname, 'validation/skills-discovery.json');
    fs.mkdirSync(path.dirname(output), {recursive: true});
    fs.writeFileSync(output, JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
    if (!report.passed) process.exitCode = 1;
  } finally {
    reader.close(); child.stdin.end();
    const timer = setTimeout(() => child.kill(), 2000); timer.unref();
  }
})().catch(error => {console.error(error); child.kill(); process.exitCode = 1;});
