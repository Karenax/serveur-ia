/* Experimental local recovery screen. The caller owns the profile lock and
 * must keep both source origins until the full migration has been verified. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.kiaraPortalConflictReview = api;
})(globalThis, function () {
  'use strict';

  function element(document, tag, text, className) {
    const value = document.createElement(tag);
    if (text !== undefined) value.textContent = text;
    if (className) value.className = className;
    return value;
  }

  // The stored value is never converted for writing. A preview may omit
  // formatting or operational metadata, so the exact value remains available.
  function preview(key, raw) {
    if (typeof key !== 'string' || typeof raw !== 'string' || raw.length > 4_500_000) return null;
    let value;
    try {value = JSON.parse(raw);} catch {return null;}
    if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
    if (key.startsWith('agent.notes.markdown.v1.') && value.format === 1 && typeof value.text === 'string')
      return value.text;
    if (key.startsWith('agent.meeting-publication.v1.') && value.summary) {
      const summary=value.summary;
      if (typeof summary.overview !== 'string' || !['decisions','actions','open_points'].every(name=>Array.isArray(summary[name]))) return null;
      const lines = ['Synthèse', summary.overview];
      for (const [name, label] of [['decisions','Décisions'], ['actions','Actions'], ['open_points','Points ouverts']]) {
        if (!summary[name].every(item=>item && typeof item.text === 'string')) return null;
        lines.push('', label, ...summary[name].map(item=>'- '+item.text));
      }
      if (value.fields && typeof value.fields.text === 'string' && value.fields.text)
        lines.push('', 'Élément en préparation', value.fields.text);
      return lines.join('\n');
    }
    if (!key.startsWith('agent.notes.v1.') && !key.startsWith('agent.meeting-note.v1.')) return null;
    if (typeof value.title !== 'string' || value.content?.version !== 1 || !Array.isArray(value.content.blocks)) return null;
    const runs = entries => {
      if (!Array.isArray(entries) || entries.some(run=>!run || typeof run.text !== 'string')) throw new Error();
      return entries.map(run=>run.text).join('');
    };
    try {
      const lines = value.content.blocks.map(block=>{
        if (!block || typeof block !== 'object') throw new Error();
        if (block.type === 'paragraph' || block.type === 'heading') return runs(block.runs);
        if (block.type === 'image' && typeof block.caption === 'string') return '[Image]'+(block.caption ? ' '+block.caption : '');
        if (block.type === 'list' && ['bullet','ordered','checklist'].includes(block.kind) && Array.isArray(block.items)) return block.items.map(item=>{
          if (!item || typeof item !== 'object' || (block.kind === 'checklist' && typeof item.checked !== 'boolean')) throw new Error();
          return (block.kind === 'checklist' ? (item.checked ? '[x] ' : '[ ] ') : '• ')+runs(item.runs);
        }).join('\n');
        if (block.type === 'table' && Array.isArray(block.rows)) return block.rows.map(row=>{
          if (!Array.isArray(row)) throw new Error();
          return row.map(runs).join(' | ');
        }).join('\n');
        throw new Error();
      });
      return [value.title, ...lines].join('\n\n');
    } catch {return null;}
  }

  function show({document, container, storage, key, incoming, archive, restartRequired=false}) {
    if (!document || !container || !storage || typeof key !== 'string' || typeof incoming !== 'string'
        || typeof archive !== 'function' || typeof restartRequired !== 'boolean') throw new TypeError('Comparaison indisponible.');
    const current = storage.getItem(key);
    if (typeof current !== 'string' || current === incoming) throw new Error('Comparaison indisponible.');

    const view = element(document, 'main', undefined, 'recovery-review');
    view.setAttribute('aria-labelledby', 'recovery-review-title');
    const title = element(document, 'h1', 'Deux versions à conserver');
    title.id = 'recovery-review-title';
    const intro = element(document, 'p', 'Comparez les versions. La version actuelle restera utilisée ; l’autre sera conservée.'
      + (restartRequired ? ' Kiara se fermera ensuite : relancez-le pour vérifier les copies.' : ''));
    const versions = element(document, 'div', undefined, 'recovery-versions');
    const previews = [preview(key, current), preview(key, incoming)];
    const guidance = previews.some(value => value !== null)
      ? element(document, 'p', 'Les aperçus peuvent omettre des détails. Ouvrez « Voir le contenu complet » pour les consulter.', 'recovery-review-guidance')
      : null;
    let index = 0;
    for (const [label, value] of [['Version actuelle', current], ['Autre version', incoming]]) {
      const section = element(document, 'section', undefined, 'recovery-version');
      const heading = element(document, 'h2', label);
      const field = document.createElement('textarea');
      field.readOnly = true;
      field.setAttribute('aria-label', label);
      field.spellcheck = false;
      const summary = previews[index++];
      field.value = summary === null ? value : summary;
      section.append(heading, field);
      if (summary !== null) {
        const detail = document.createElement('details');
        const detailLabel = element(document, 'summary', 'Voir le contenu complet');
        const explanation = element(document, 'p', 'L’aperçu peut omettre la mise en forme et certains détails.');
        const raw = document.createElement('textarea');
        raw.readOnly = true; raw.spellcheck = false; raw.value = value;
        raw.setAttribute('aria-label', `${label} : contenu complet`);
        detail.append(detailLabel, explanation, raw); section.append(detail);
      }
      versions.append(section);
    }
    const status = element(document, 'p', '', 'recovery-review-status');
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    const actions = element(document, 'div', undefined, 'recovery-review-actions');
    const cancel = element(document, 'button', 'Interrompre', 'recovery-secondary');
    const keep = element(document, 'button', 'Conserver les deux', 'recovery-primary');
    cancel.type = keep.type = 'button';
    actions.append(cancel, keep); view.append(title, intro);
    if (guidance) view.append(guidance);
    view.append(versions, status, actions);
    container.replaceChildren(view);

    return new Promise(resolve => {
      let busy = false, finished = false;
      const finish = result => {
        if (finished) return;
        finished = true;
        document.removeEventListener('keydown', onKey);
        resolve(result);
      };
      const onKey = event => {
        if (event.key === 'Escape' && !busy) {event.preventDefault();finish({status:'cancel'});}
      };
      document.addEventListener('keydown', onKey);
      cancel.addEventListener('click', () => {if (!busy) finish({status:'cancel'});});
      keep.addEventListener('click', async () => {
        if (busy || finished) return;
        busy = true; cancel.disabled = true; keep.disabled = true;
        status.textContent = 'Conservation en cours…';
        try {
          if (storage.getItem(key) !== current) throw new Error();
          const id = await archive(storage, key, incoming);
          if (typeof id !== 'string' || !/^[0-9a-f]{64}$/.test(id) || storage.getItem(key) !== current)
            throw new Error();
          finish({status:'archived', id});
        } catch {
          status.textContent = 'Impossible de conserver les deux versions. Si les données ont changé, interrompez et relancez Kiara ; sinon, libérez de l’espace puis réessayez.';
          busy = false; cancel.disabled = false; keep.disabled = false;
          cancel.focus();
        }
      });
      cancel.focus();
    });
  }

  return {show, preview};
});
