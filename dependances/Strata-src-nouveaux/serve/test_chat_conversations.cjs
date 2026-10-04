// Exercise the chat controller with two independently delayed SSE streams, without a GPU.
// Run: node serve/test_chat_conversations.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {webcrypto} = require('node:crypto');

class Element {
  constructor() { this.children = []; this.dataset = {}; this.style = {}; this.value = ''; this.hidden = false; this.parts = new Map(); }
  appendChild(child) { this.children.push(child); child.parent = this; return child; }
  append() {}
  replaceChildren() { this.children = []; }
  addEventListener() {}
  remove() { if (this.parent) this.parent.children = this.parent.children.filter((c) => c !== this); }
  querySelector(selector) {
    if (selector.startsWith('[data-i=')) return this.children.find((c) => String(c.dataset.i) === selector.match(/"(\d+)"/)[1]);
    if (!this.parts.has(selector)) this.parts.set(selector, new Element());
    return this.parts.get(selector);
  }
  querySelectorAll() { return this.children.filter((c) => c.className?.startsWith('st-msg')); }
  get classList() { return {add() {}, remove() {}}; }
}

function setup(storage = new Map()) {
  const elements = new Map();
  const pending = [];
  const context = vm.createContext({
    crypto: webcrypto, Date, Map, AbortController, TextDecoder, performance,
    document: {createElement: () => new Element()}, innerHeight: 800,
    $: (id) => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); },
    store: {get: (key, fallback) => storage.has(key) ? JSON.parse(storage.get(key)) : fallback,
            set: (key, value) => storage.set(key, JSON.stringify(value))},
    fmt: String, icon: () => '', markdown: String, toast() {},
    renderAttachments() {}, userText: (m) => m.text, headers: () => ({}),
    health: {model: 'test'}, mcpInfo: {tools: 0}, projectionLoaded: () => false,
    requestAnimationFrame: (fn) => { fn(); return 0; }, cancelAnimationFrame() {},
    fetch: async (url, init) => {
      const stream = {body: JSON.parse(init.body), signal: init.signal};
      pending.push(stream);
      return {ok: true, body: {getReader: () => ({read: () => new Promise((resolve, reject) => {
        stream.resolve = resolve;
        if (stream.signal.aborted) reject(Object.assign(new Error('stopped'), {name: 'AbortError'}));
        else stream.signal.addEventListener('abort', () => reject(Object.assign(new Error('stopped'), {name: 'AbortError'})), {once: true});
      })})}};
    },
  });
  const source = fs.readFileSync(require('node:path').join(__dirname, 'web/app.js'), 'utf8');
  vm.runInContext(source.slice(source.indexOf('const DEFAULTS ='), source.indexOf('$("export-btn").onclick')), context);
  const run = (code) => vm.runInContext(code, context);
  return {run, elements, pending, storage};
}
const tick = () => new Promise((resolve) => setImmediate(resolve));
async function chunk(stream, text) {
  stream.resolve({done: false, value: Buffer.from('data: ' + JSON.stringify({choices: [{delta: {content: text}}]}) + '\n\n')});
  await tick();
}
async function main() {
  const app = setup(new Map([['chat', JSON.stringify([{role: 'user', text: 'Legacy', time: 0}])]]));
  assert.equal(app.run('messages[0].text'), 'Legacy');
  app.elements.get('input').value = 'Alpha';
  const first = app.run('send()');
  await tick();
  app.run('$("new-btn").onclick()');
  assert.equal(app.run('busy'), null);
  assert.equal(app.run('messages.length'), 0);
  app.elements.get('input').value = 'Beta';
  const second = app.run('send()');
  await tick();
  assert.equal(app.pending.length, 2);
  assert.deepEqual(app.pending[1].body.messages, [{role: 'user', content: 'Beta'}]);
  await chunk(app.pending[0], 'Answer Alpha');
  assert.equal(app.run('messages[1].text'), ''); // background stream cannot write to Beta
  app.run('selectConversation(conversations[0])');
  assert.equal(app.run('messages.at(-1).text'), 'Answer Alpha');
  assert.equal(app.run('busy.msg === messages.at(-1)'), true);
  app.elements.get('input').value = 'draft Alpha';
  app.run('selectConversation(conversations[1])');
  assert.equal(app.run('busy.msg === messages.at(-1)'), true);
  app.pending[0].resolve({done: true});
  await first;
  assert.equal(app.run('busy.msg === messages.at(-1)'), true); // Alpha completion cannot unlock Beta
  await chunk(app.pending[1], 'Answer Beta');
  app.pending[1].resolve({done: true});
  await second;
  assert.equal(app.run('busy'), null);
  app.run('selectConversation(conversations[0])');
  assert.equal(app.elements.get('input').value, 'draft Alpha');
  assert.equal(app.run('messages.at(-1).text'), 'Answer Alpha');
  const reloaded = setup(app.storage);
  assert.equal(reloaded.run('conversations.length'), 2);
  assert.equal(reloaded.run('conversations[1].messages[1].text'), 'Answer Beta');
  // A different tab creates a chat; saving this tab must preserve that chat too.
  reloaded.run('$("new-btn").onclick()');
  app.run('saveChat()');
  assert.equal(JSON.parse(app.storage.get('conversations')).length, 3);
  app.run('$("new-btn").onclick()');
  app.elements.get('input').value = 'Cancelled';
  const third = app.run('send()');
  await tick();
  app.run('$("stop-btn").onclick()');
  await third;
  assert.equal(app.run('messages.at(-1).stopped'), true);
  assert.equal(app.run('requests.size'), 0);
  console.log('PASS: legacy migration, concurrent streams, history isolation, switching, draft, persistence, tab merge, cancellation');
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
