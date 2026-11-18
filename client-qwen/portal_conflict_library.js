/* Read-only access to the copies retained during local recovery. */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else api.install(root).catch(() => {});
})(globalThis, function () {
  'use strict';

  function node(document, tag, text, className) {
    const result = document.createElement(tag);
    if (text !== undefined) result.textContent = text;
    if (className) result.className = className;
    return result;
  }

  function hasCopies(storage, prefix) {
    const count = storage.length;
    if (!Number.isSafeInteger(count) || count < 0) throw new Error('Stockage indisponible.');
    for (let index = 0; index < count; index++) {
      const key = storage.key(index);
      if (typeof key !== 'string') throw new Error('Stockage indisponible.');
      if (key.startsWith(prefix)) return true;
    }
    if (storage.length !== count) throw new Error('Stockage indisponible.');
    return false;
  }

  function describe(item, review, index) {
    const summary = review.preview(item.key, item.incoming);
    const first = (summary || '').split('\n').find(line => line.trim()) || '';
    return `Copie ${index + 1}` + (first ? ` : ${first.slice(0, 80)}` : '');
  }

  function version(document, review, key, label, value) {
    const section = node(document, 'section', undefined, 'kiara-conflict-version');
    section.append(node(document, 'h3', label));
    const summary = review.preview(key, value);
    const field = document.createElement('textarea');
    field.readOnly = true; field.spellcheck = false; field.value = summary === null ? value : summary;
    field.setAttribute('aria-label', label); section.append(field);
    if (summary !== null) {
      const details = document.createElement('details');
      details.append(node(document, 'summary', 'Voir le contenu complet'));
      const full = document.createElement('textarea');
      full.readOnly = true; full.spellcheck = false; full.value = value;
      full.setAttribute('aria-label', `${label} : contenu complet`);
      details.append(full); section.append(details);
    }
    return section;
  }

  async function install(root) {
    const {document, localStorage:storage, kiaraPortalConflictArchive:archive, kiaraPortalConflictReview:review} = root;
    if (!document || !archive || !review || !storage) throw new Error('Copies indisponibles.');
    const host = document.querySelector('.chat-view');
    if (!host) return false;
    let available;
    try {available = hasCopies(storage, archive.PREFIX);} catch {available = true;}
    if (!available) return false;

    const banner = node(document, 'div', undefined, 'kiara-conflict-banner');
    const bannerText = node(document, 'span', 'Des versions locales ont été conservées.');
    bannerText.setAttribute('role', 'status'); banner.append(bannerText);
    const trigger = node(document, 'button', 'Consulter', 'secondary');
    trigger.type = 'button'; banner.append(trigger); host.prepend(banner);
    const dialog = node(document, 'dialog', undefined, 'kiara-conflict-dialog');
    dialog.setAttribute('aria-labelledby', 'kiara-conflict-title');
    const header = node(document, 'div', undefined, 'kiara-conflict-heading');
    const title = node(document, 'h2', 'Versions conservées'); title.id = 'kiara-conflict-title';
    const close = node(document, 'button', 'Fermer', 'secondary'); close.type = 'button';
    header.append(title, close);
    const info = node(document, 'p', 'Ces copies datent de la récupération. Elles ne remplacent pas votre travail en cours. Vous pouvez copier le texte dont vous avez besoin.');
    const status = node(document, 'p', '', 'kiara-conflict-status'); status.setAttribute('role', 'status');
    const content = node(document, 'div', undefined, 'kiara-conflict-content');
    dialog.append(header, info, status, content); document.body.append(dialog);

    let generation = 0;
    close.addEventListener('click', () => dialog.close());
    dialog.addEventListener('close', () => {
      generation++; content.replaceChildren(); status.textContent = ''; trigger.focus();
    });
    trigger.addEventListener('click', async () => {
      if (dialog.open) return;
      const current = ++generation;
      content.replaceChildren(); status.textContent = 'Chargement des copies…';
      try {dialog.showModal();} catch {bannerText.textContent = 'Impossible d’ouvrir les copies conservées.';return;}
      bannerText.textContent = 'Des versions locales ont été conservées.';
      close.focus();
      try {
        const copies = await archive.list(storage);
        if (current !== generation || !dialog.open) return;
        if (!copies.length) {status.textContent = 'Aucune copie conservée sur cet appareil.';return;}
        status.textContent = '';
        const label = node(document, 'label', 'Copie à consulter', 'kiara-conflict-label');
        const select = document.createElement('select'); select.setAttribute('aria-label', 'Copie à consulter');
        copies.forEach((item, index) => {
          const option = document.createElement('option'); option.value = String(index);
          option.textContent = describe(item, review, index); select.append(option);
        });
        label.append(select);
        const guidance = node(document, 'p', 'Les aperçus peuvent omettre des détails. Ouvrez « Voir le contenu complet » pour les consulter.');
        const versions = node(document, 'div', undefined, 'kiara-conflict-versions');
        function render() {
          const item = copies[Number(select.value)];
          if (!item) throw new Error('Copie indisponible.');
          const sections = [version(document, review, item.key, 'Version présente à la récupération', item.current),
                            version(document, review, item.key, 'Autre version conservée', item.incoming)];
          const live = storage.getItem(item.key);
          if (typeof live === 'string' && live !== item.current && live !== item.incoming)
            sections.unshift(version(document, review, item.key, 'Version en cours sur cet appareil', live));
          versions.replaceChildren(...sections);
        }
        select.addEventListener('change', () => {
          try {render();} catch {versions.replaceChildren();status.textContent = 'Impossible de lire cette copie. Elle reste conservée sur cet appareil.';}
        });
        content.append(label, guidance, versions); render();
      } catch {
        if (current !== generation || !dialog.open) return;
        content.replaceChildren();
        status.textContent = 'Impossible de lire les copies. Elles restent conservées sur cet appareil.';
      }
    });
    return true;
  }

  return {install, hasCopies};
});
