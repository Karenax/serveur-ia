import assert from 'node:assert/strict';
import { test } from 'node:test';
import { analyzeSource } from './ux-quality-check.mjs';

test('visible JSX and labels are checked with useful locations', () => {
  const result = analyzeSource('export const X = () => <><p>Backend HTTP 500</p>\n<input placeholder="Cliquez ici pour saisir" /></>');
  assert.ok(result.some(f => f.rule === 'technical-copy' && f.line === 1));
  assert.ok(result.some(f => f.rule === 'verbose-copy' && f.line === 2));
  assert.ok(result.some(f => f.rule === 'input-name'));
});
test('logs, comments, imports, test files and explicit diagnostics are excluded', () => {
  assert.deepEqual(analyzeSource('// backend HTTP 500\nconsole.log("backend HTTP 500"); import x from "backend";'), []);
  assert.deepEqual(analyzeSource('logger.warn({ message: "backend HTTP 500" }); console.log({ label: "backend HTTP 500" });'), []);
  assert.deepEqual(analyzeSource('<p>backend HTTP 500</p>', 'view.test.tsx'), []);
  assert.deepEqual(analyzeSource('<section data-ux-scope="diagnostic"><p>backend HTTP 500</p><img /></section>'), []);
  assert.deepEqual(analyzeSource('function DebugPanel(){return <p>backend HTTP 500</p>}'), []);
});
test('accessible controls and business references remain valid', () => {
  assert.deepEqual(analyzeSource('<><label>Projet<input /></label><button aria-label="Fermer"><Icon /></button><img alt="" /><p>AIRB25LTH0806-A</p></>'), []);
});
test('accessibility warnings identify non-native clicks and unnamed controls', () => {
  const rules = analyzeSource('<><div onClick={go}>Ouvrir</div><button><Icon /></button><img /></>').map(f => f.rule);
  assert.deepEqual(rules.sort(), ['button-name', 'image-alt', 'keyboard-click']);
});
test('reviewed exceptions need a reason; JSX syntax and strings are untouched', () => {
  assert.deepEqual(analyzeSource('{/* ux-ignore: diagnostic réservé aux administrateurs */}\n<p>backend HTTP 500</p>'), []);
  assert.ok(analyzeSource('{/* ux-ignore: */}\n<p>backend HTTP 500</p>').length > 0);
});
test('visible object labels and conditional strings are checked', () => {
  assert.ok(analyzeSource('const x = { label: "backend HTTP 500" };').some(f => f.rule === 'technical-copy'));
  assert.ok(analyzeSource('<p>{ok ? "Enregistré" : "backend HTTP 500"}</p>').some(f => f.rule === 'technical-copy'));
  assert.ok(analyzeSource(`<p>${'texte '.repeat(30)}</p>`).some(f => f.rule === 'long-copy'));
});
