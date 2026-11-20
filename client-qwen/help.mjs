const dialogs = new WeakMap();

function createDialog(trigger) {
  const dialog = document.createElement('dialog');
  dialog.className = 'kiara-help';
  dialog.setAttribute('aria-labelledby', 'kiara-help-title');
  dialog.innerHTML = `
    <div class="kiara-help-header">
      <h2 id="kiara-help-title">Aide Kiara</h2>
      <button type="button" aria-label="Fermer l’aide" title="Fermer l’aide" autofocus>
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.7"
          stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>
      </button>
      <label hidden>Rubrique <select></select></label>
    </div>
    <div class="kiara-help-content" tabindex="0"></div>`;
  trigger.after(dialog);

  const close = dialog.querySelector('button');
  const select = dialog.querySelector('select');
  const content = dialog.querySelector('.kiara-help-content');
  const topics = new Map();
  let guide;

  function showTopic(id) {
    const topic = topics.get(id) ?? topics.get('accueil');
    select.value = topic.id;
    content.replaceChildren(topic.cloneNode(true));
    content.scrollTop = 0;
  }

  function buildIndex(html) {
    const source = new DOMParser().parseFromString(html, 'text/html');
    const groups = [];
    for (const section of source.querySelectorAll('main > section')) {
      const group = document.createElement('optgroup');
      group.label = section.querySelector('h2').textContent;
      for (const topic of section.querySelectorAll('article[id]')) {
        topics.set(topic.id, topic);
        group.append(new Option(topic.querySelector('h3').textContent, topic.id));
      }
      groups.push(group);
    }
    if (!topics.has('accueil')) throw new Error('Sommaire indisponible');
    select.replaceChildren(...groups);
    select.closest('label').hidden = false;
  }

  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('keydown', event => event.stopPropagation());
  dialog.addEventListener('close', () => trigger.focus({preventScroll: true}));
  select.addEventListener('change', () => showTopic(select.value));

  return async (id, loadGuide) => {
    if (!dialog.open) dialog.showModal();
    if (!guide) {
      const status = document.createElement('p');
      status.setAttribute('role', 'status');
      status.textContent = 'Chargement de l’aide…';
      content.replaceChildren(status);
      guide = Promise.resolve().then(loadGuide).then(buildIndex);
    }
    try {
      await guide;
      showTopic(id);
    } catch {
      guide = undefined;
      const message = document.createElement('p');
      message.setAttribute('role', 'alert');
      message.textContent = 'L’aide est indisponible. Rechargez la page pour réessayer.';
      content.replaceChildren(message);
    }
  };
}

export function openHelp(trigger, topic, loadGuide) {
  if (!dialogs.has(trigger)) dialogs.set(trigger, createDialog(trigger));
  return dialogs.get(trigger)(topic, loadGuide);
}
