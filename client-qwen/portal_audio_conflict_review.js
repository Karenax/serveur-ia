/* Experimental comparison of two verified audio fragments. The caller owns
 * the profile lock and remains responsible for checking persistent copies. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.kiaraPortalAudioConflictReview = api;
})(globalThis, function () {
  'use strict';
  function node(document, tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  }
  function validate(value) {
    if (!value || !(value.bytes instanceof Uint8Array) || !value.meta || typeof value.mime !== 'string'
        || !value.mime || !Number.isSafeInteger(value.meta.duration_ms) || value.meta.duration_ms < 0)
      throw new TypeError('Comparaison audio indisponible.');
  }
  function duration(milliseconds) {
    const seconds = Math.round(milliseconds / 1000);
    return `${Math.floor(seconds / 60)} min ${String(seconds % 60).padStart(2, '0')} s`;
  }
  function show({document, container, current, incoming, archive, urls, restartRequired = false}) {
    if (!document || !container || typeof archive !== 'function' || typeof restartRequired !== 'boolean'
        || !urls || typeof urls.createObjectURL !== 'function' || typeof urls.revokeObjectURL !== 'function')
      throw new TypeError('Comparaison audio indisponible.');
    validate(current);validate(incoming);
    const view = node(document, 'main', undefined, 'recovery-review');
    view.setAttribute('aria-labelledby', 'recovery-audio-title');
    const title = node(document, 'h1', 'Deux versions audio à conserver');title.id = 'recovery-audio-title';
    const intro = node(document, 'p', 'Écoutez les fragments si vous le souhaitez. La version actuelle restera utilisée ; l’autre sera conservée.'
      + (restartRequired ? ' Kiara se fermera ensuite : relancez-le pour vérifier les copies.' : ''));
    const versions = node(document, 'div', undefined, 'recovery-versions');
    const created = [];
    const revoke = () => {for (const url of created.splice(0)) urls.revokeObjectURL(url);};
    try {
      for (const [label, value] of [['Version actuelle', current], ['Autre version', incoming]]) {
        const section = node(document, 'section', undefined, 'recovery-version');
        section.append(node(document, 'h2', label));
        section.append(node(document, 'p', `Durée du fragment : ${duration(value.meta.duration_ms)}.`));
        const player = document.createElement('audio');player.controls = true;player.preload = 'none';
        player.setAttribute('aria-label', label);
        const url = urls.createObjectURL(new Blob([value.bytes], {type:value.mime}));
        created.push(url);player.src = url;section.append(player);versions.append(section);
      }
    } catch (error) {revoke();throw error;}
    const status = node(document, 'p', '', 'recovery-review-status');
    status.setAttribute('role', 'status');status.setAttribute('aria-live', 'polite');
    const actions = node(document, 'div', undefined, 'recovery-review-actions');
    const cancel = node(document, 'button', 'Interrompre', 'recovery-secondary');
    const keep = node(document, 'button', 'Conserver les deux', 'recovery-primary');
    cancel.type = keep.type = 'button';actions.append(cancel, keep);
    view.append(title, intro, versions, status, actions);container.replaceChildren(view);

    return new Promise(resolve => {
      let busy = false, finished = false;
      const finish = result => {
        if (finished) return;
        finished = true;document.removeEventListener('keydown', onKey);revoke();resolve(result);
      };
      const onKey = event => {
        if (event.key === 'Escape' && !busy) {event.preventDefault();finish({status:'cancel'});}
      };
      document.addEventListener('keydown', onKey);
      cancel.addEventListener('click', () => {if (!busy) finish({status:'cancel'});});
      keep.addEventListener('click', async () => {
        if (busy || finished) return;
        busy = true;cancel.disabled = true;keep.disabled = true;status.textContent = 'Conservation en cours…';
        try {
          const id = await archive();
          if (typeof id !== 'string' || !/^[0-9a-f]{64}$/.test(id)) throw new Error();
          finish({status:'archived', id});
        } catch {
          status.textContent = 'Impossible de conserver les deux versions. Interrompez et relancez Kiara, ou libérez de l’espace puis réessayez.';
          busy = false;cancel.disabled = false;keep.disabled = false;cancel.focus();
        }
      });
      cancel.focus();
    });
  }
  return {show};
});
