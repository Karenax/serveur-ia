import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const project = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const requireWeb = createRequire(path.join(project, 'web/package.json'));
const ts = requireWeb('typescript');
const excluded = /(?:^|[/\\])(?:node_modules|dist|coverage|__tests__|__fixtures__|fixtures|generated|admin|diagnostics?)(?:[/\\]|$)|\.(?:test|spec|stories|generated)\./i;
const technical = /\b(?:backend|stack\s?trace|HTTP\s+[1-5]\d\d|SYNC_[A-Z_]+|SQLITE_[A-Z_]+|localhost:\d+|127\.0\.0\.1:\d+|API\s*(?:key|endpoint))\b/i;
const visibleKeys = new Set(['title', 'label', 'description', 'detail', 'message', 'placeholder', 'tooltip', 'emptyMessage', 'successMessage', 'errorMessage']);
const visibleAttrs = new Set(['title', 'placeholder', 'aria-label', 'alt', 'label']);

export function analyzeSource(source, filename = 'screen.tsx') {
  if (excluded.test(filename)) return [];
  const sf = ts.createSourceFile(filename, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const lines = source.split(/\r?\n/);
  const findings = [];
  const seen = new Set();
  function warn(node, rule, message) {
    const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
    // A reviewed exception needs a reason on the same or immediately preceding line.
    if ([lines[line - 2], lines[line - 1]].some(x => /ux-ignore:\s*[\p{L}\p{N}]/u.test(x ?? ''))) return;
    const key = `${line}:${rule}`;
    if (!seen.has(key)) findings.push({ file: filename, line, rule, message });
    seen.add(key);
  }
  function text(node, value) {
    const clean = value.replace(/\s+/g, ' ').trim();
    if (!clean) return;
    if (technical.test(clean)) warn(node, 'technical-copy', 'Texte technique potentiellement visible : vérifier le contexte métier.');
    if (clean.length > 140) warn(node, 'long-copy', `Texte de ${clean.length} caractères : vérifier son utilité et sa concision.`);
    if (/^(?:Cliquez ici|Veuillez cliquer|Le processus de sauvegarde)/i.test(clean)) warn(node, 'verbose-copy', 'Préférer un libellé direct et orienté action.');
    if (/^(?:Cockpit|BOM|Analyse des connaissances)$/.test(clean)) warn(node, 'terminology', 'Comparer au vocabulaire métier du projet (Vue d’ensemble, Nomenclature, Informations à vérifier).');
  }
  function attrMap(node) {
    return new Map(node.attributes.properties.filter(ts.isJsxAttribute).map(a => [a.name.getText(sf), a]));
  }
  function value(attr) {
    if (!attr?.initializer) return '';
    return ts.isStringLiteral(attr.initializer) ? attr.initializer.text : attr.initializer.getText(sf);
  }
  function visit(node) {
    if (ts.isCallExpression(node) && /^(?:console|logger|log)\.(?:log|debug|info|warn|error|trace)$/.test(node.expression.getText(sf))) return;
    if (ts.isFunctionDeclaration(node) && /(?:admin|diagnostic|debug)/i.test(node.name?.text ?? '')) return;
    if (ts.isVariableDeclaration(node) && /(?:admin|diagnostic|debug)/i.test(node.name.getText(sf))) return;
    if (ts.isJsxElement(node) || ts.isJsxSelfClosingElement(node)) {
      const opening = ts.isJsxElement(node) ? node.openingElement : node;
      const attrs = attrMap(opening);
      if (/\b(?:admin|diagnostic|debug|technical)\b/i.test(value(attrs.get('data-ux-scope')))) return;
      const tag = opening.tagName.getText(sf);
      const spread = opening.attributes.properties.some(ts.isJsxSpreadAttribute);
      if (tag === 'img' && !attrs.has('alt') && !spread) warn(opening, 'image-alt', 'Image sans attribut alt : fournir un nom utile ou alt="" si décorative.');
      if (attrs.has('onClick') && ['div', 'span'].includes(tag) && !attrs.has('onKeyDown') && !attrs.has('onKeyUp') && !spread) warn(opening, 'keyboard-click', 'Contrôle cliquable non natif : vérifier accès clavier, rôle et focus.');
      if (tag === 'input' && value(attrs.get('type')) !== 'hidden' && !spread && !['aria-label', 'aria-labelledby', 'id'].some(k => attrs.has(k))) {
        let parent = node.parent;
        let wrapped = false;
        while (parent && !ts.isFunctionLike(parent)) {
          if (ts.isJsxElement(parent) && parent.openingElement.tagName.getText(sf) === 'label') wrapped = true;
          parent = parent.parent;
        }
        if (!wrapped) warn(opening, 'input-name', 'Champ sans association de label repérée : vérifier son nom accessible.');
      }
      if (tag === 'button' && ts.isJsxElement(node) && !spread && !attrs.has('aria-label') && !attrs.has('aria-labelledby') && !attrs.has('title')) {
        const hasContent = node.children.some(c => ts.isJsxText(c) ? c.text.trim() : ts.isJsxExpression(c) && c.expression);
        if (!hasContent) warn(opening, 'button-name', 'Bouton sans texte ou nom accessible repéré (vérifier les composants enfants).');
      }
    }
    if (ts.isJsxText(node)) text(node, node.text);
    if (ts.isStringLiteralLike(node)) {
      const parent = node.parent;
      if (ts.isJsxAttribute(parent) && visibleAttrs.has(parent.name.getText(sf))) text(node, node.text);
      if (ts.isJsxExpression(parent)) text(node, node.text);
      if (ts.isPropertyAssignment(parent) && visibleKeys.has(parent.name.getText(sf).replace(/['"]/g, ''))) text(node, node.text);
      if (ts.isConditionalExpression(parent) && ts.isJsxExpression(parent.parent)) text(node, node.text);
    }
    ts.forEachChild(node, visit);
  }
  visit(sf);
  return findings;
}

function collect(target) {
  if (excluded.test(target)) return [];
  const stat = fs.statSync(target);
  if (stat.isDirectory()) return fs.readdirSync(target).flatMap(name => collect(path.join(target, name)));
  return /\.[jt]sx?$/.test(target) ? [target] : [];
}

export function checkFiles(files) {
  const findings = [];
  const components = new Map();
  for (const file of [...new Set(files)].sort()) {
    if (excluded.test(file)) continue;
    const source = fs.readFileSync(file, 'utf8');
    const filename = path.relative(project, file).replaceAll('\\', '/');
    findings.push(...analyzeSource(source, filename));
    const sf = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
    function find(node) {
      if (ts.isReturnStatement(node) && node.expression) {
        const body = node.expression.getText(sf);
        if ((body.match(/<[A-Za-z]/g) ?? []).length >= 8 && body.length >= 200 && !/ux-ignore:|data-ux-scope/.test(body)) {
          const signature = body.replace(/\s+/g, ' ').trim();
          const previous = components.get(signature);
          const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
          if (previous && previous.file !== filename) findings.push({ file: filename, line, rule: 'duplicate-view', message: `Vue identique à ${previous.file}:${previous.line} : envisager un composant partagé.` });
          else components.set(signature, { file: filename, line });
        }
      }
      ts.forEachChild(node, find);
    }
    find(sf);
  }
  return findings;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const json = args.includes('--json');
  const inputs = args.filter(a => a !== '--json' && a !== '--');
  // npm --prefix changes cwd to web; accept paths relative to cwd or the repo.
  const files = (inputs.length ? inputs.map(p => fs.existsSync(path.resolve(p)) ? path.resolve(p) : path.resolve(project, p)) : [path.join(project, 'web/src')]).flatMap(collect);
  const findings = checkFiles(files);
  if (json) console.log(JSON.stringify(findings, null, 2));
  else {
    for (const f of findings) console.log(`${f.file}:${f.line}: warning [${f.rule}] ${f.message}`);
    console.log(`UX : ${files.length} fichiers examinés, ${findings.length} avertissements à relire. Aucune modification; aucun blocage sur suspicion.`);
  }
  // Findings never fail a build; missing inputs/dependencies still fail visibly.
}
