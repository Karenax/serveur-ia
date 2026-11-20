"""Select the Kiara 4 document layout before the browser receives any markup."""

import json
import re

DEVICE_SETTINGS = {
    'vocal': ('Conversation vocale', None),
    'dictee': ('Dictée', None),
    'connexion': ('Connexion au serveur', 'connection-pane-6'),
    'mises-a-jour': ('Mises à jour', 'updates-pane-4'),
    'api-locale': ('API locale et intégrations', 'android-local-api-pane-7'),
}

HELP_BUTTON = '''<button type="button" class="icon-button kiara-help-trigger" data-kiara-help
 aria-label="Aide" title="Aide sur cette page" aria-haspopup="dialog">
 <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.7"
  stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/>
  <path d="M9.1 9a3 3 0 0 1 5.8 1c0 1.5-1.5 2.2-2.2 2.8-.5.4-.7.8-.7 1.2M12 17h.01"/></svg></button>'''

CONVERSATION_HELP_TOPIC = '''() => {
  const view = historyView;
  if (view === 'chat' && document.body.dataset.projectConversation === 'true') return 'project-assistant';
  if (view === 'projects' && document.querySelector('#ws-project-detail:not([hidden])')) return 'local-project';
  if (view === 'device-preferences') {
    const section = document.querySelector('.device-settings [data-setting][aria-current="page"]')?.dataset.setting;
    return 'settings-' + ({apparence:'appearance', notifications:'notification-settings'}[section] || section);
  }
  return ({access:'settings-access', connection:'settings-connexion', updates:'settings-mises-a-jour',
           api:'settings-api-locale'}[view] || view);
}'''


def add_contextual_help(markup, read, nonce, topic):
    guide = json.dumps(read('help.html'), ensure_ascii=False).replace('<', '\\u003c')
    style = f'<style nonce="{nonce}">{read("help.css")}</style>'
    script = f'''<script type="module" nonce="{nonce}">{read('help.mjs')}
const trigger = document.querySelector('[data-kiara-help]');
const helpTopic = {topic};
trigger.addEventListener('click', () => openHelp(trigger, helpTopic(), () => {guide}));
</script>'''
    return markup.replace('</head>', style + '</head>', 1).replace('</body>', script + '</body>', 1)


def chat_contextual_help(markup, read):
    markup = markup.replace('<button id="connection"', HELP_BUTTON + '<button id="connection"', 1)
    return add_contextual_help(markup, read, '__NONCE__', CONVERSATION_HELP_TOPIC)


def setting_source(source, opening, closing):
    _, content = source.split(opening, 1)
    content, _ = content.split(closing, 1)
    return content


def device_settings(read, nonce, section, *, key, recovery=False):
    title, template = DEVICE_SETTINGS[section]
    markup = setting_source(read('chat.html'), f'<!-- kiara-slot:{template} -->',
                            f'<!-- /kiara-slot:{template} -->') if template else ''
    if markup:
        markup = markup.replace(' hidden><h2>', '><h2>', 1)
    else:
        markup = f'<section class="settings-view"><h2>{title}</h2></section>'
    config = json.dumps({'key': key, 'section': section}).replace('<', '\\u003c')
    helpers = {
        'vocal': ('conversation.js', '/* kiara-device:voice:start */', '/* kiara-device:voice:end */'),
        'dictee': ('voice.js', '/* kiara-device:dictation:start */', '/* kiara-device:dictation:end */'),
        'connexion': ('ui.js', '/* kiara-slot:desktop-connection-transfer-controls-32 */',
                      '/* /kiara-slot:desktop-connection-transfer-controls-32 */'),
        'api-locale': ('ui.js', '/* kiara-slot:desktop-integration-logic-26 */',
                       '/* /kiara-slot:desktop-integration-logic-26 */'),
    }
    shared = ''
    if section in helpers:
        name, start, end = helpers[section]
        shared = setting_source(read(name), start, end)
    content = read('device-settings.js')
    if section in ('connexion', 'api-locale'):
        marker = 'connection' if section == 'connexion' else 'api'
        content = content.replace(f'/* kiara-device:{marker} */', shared, 1)
        shared = ''
    layout_start, layout_end = '', ''
    if recovery:
        links = ''.join(f'<a href="/device-recovery?section={slug}"'
                        + (' aria-current="page"' if slug == section else '') + f'>{label}</a>'
                        for slug, (label, _) in DEVICE_SETTINGS.items())
        layout_start = ('<header class="device-recovery-header"><a class="secondary" href="/chat">Conversations</a>'
                        f'<h1>Réglages de cet appareil</h1>{HELP_BUTTON}</header><div class="device-recovery">'
                        f'<nav aria-label="Réglages de cet appareil">{links}</nav>')
        layout_end = '</div>'
    page = f'''<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · Kiara</title>
<style nonce="{nonce}">{read('device-settings.css')}</style></head>
<body>{layout_start}<main data-device-panel>
<p id="device-error" role="alert" hidden></p>
{markup}
</main>{layout_end}
<script nonce="{nonce}" type="application/json" id="settings-config">{config}</script>
<script nonce="{nonce}">{shared}\n{content}</script></body></html>'''
    if recovery:
        page = add_contextual_help(page, read, nonce, f'() => "settings-{section}"')
    return page.encode('utf-8')


def modern_chat(chat, shell, *, settings_panel=False, web=False, native_settings=False):
    sidebar = re.search(r'<aside class="sidebar".*?</aside>', chat, flags=re.S)
    if sidebar is None:
        raise ValueError('Navigation Conversations introuvable')
    parts = dict(re.findall(r'<!-- shell:(\w+) -->(.*?)<!-- /shell:\1 -->', sidebar[0], flags=re.S))
    if set(parts) != {'new', 'history', 'account', 'tools', 'local'}:
        raise ValueError('Éléments de navigation Conversations incomplets')
    fragments = {
        'new_button': parts['new'],
        'history': parts['history'],
        'account': parts['account'],
        'tools': parts['tools'],
        'local_settings': parts['local'],
        'location': 'Espace de travail' if web else 'Serveur Kiara',
    }
    sidebar_markup, toolbar = shell.split('<!-- conversation-toolbar -->', 1)
    sidebar_markup = re.sub(r'\{(\w+)\}', lambda match: fragments[match[1]], sidebar_markup)
    toolbar = re.sub(r'\{(\w+)\}', lambda match: fragments[match[1]], toolbar)
    chat = chat[:sidebar.start()] + sidebar_markup.strip() + chat[sidebar.end():]
    chat = chat.replace('<div class="conversation-top">', toolbar.strip() + '<div class="conversation-top">', 1)
    chat = chat.replace('<!-- shell:access-tools -->', fragments['tools'], 1)
    chat = chat.replace('<!-- shell:access-account -->', '' if web else fragments['account'], 1)
    chat = chat.replace('<button id="connection"',
                        '<button type="button" class="nav-button notifications-shortcut" '
                        'data-view-button="notifications">Notifications</button><button id="connection"', 1)
    mode = ' data-kiara-settings-panel="true"' if settings_panel else ''
    if native_settings:
        mode += ' data-kiara-native-settings="true"'
    return chat.replace('<body>', f'<body data-kiara-unified-navigation="true"{mode}>', 1)


def notification_settings(read, nonce, *, prefix='', key='', web=False):
    config = json.dumps({'prefix': prefix, 'key': key}).replace('<', '\\u003c')
    workspace = read('workspace.html')
    _, preferences = workspace.split('/* notification-preferences:start */', 1)
    preferences, _ = preferences.split('/* notification-preferences:end */', 1)
    panel = read('notification-settings-panel.js')
    scripts = f'<script nonce="{nonce}">{preferences}\n{panel}</script>'
    conversations = f'{prefix}/app/conversations' if web else '/chat'
    return f'''<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Notifications · Kiara</title>
<style nonce="{nonce}">
  :root {{color-scheme:light;--border:#c7ced8}} :root[data-theme="dark"] {{color-scheme:dark;--border:#616971}}
  body {{margin:0;padding:2px;background:Canvas;color:CanvasText;font:15px/1.5 "Segoe UI",system-ui,sans-serif}}
  h2 {{margin:0 0 12px;font-size:22px}} p {{margin:0}} [role="status"]:empty {{display:none}}
  main,form,#fred-inbox-types {{display:grid;gap:12px;justify-items:start}} [hidden] {{display:none!important}}
  button,a {{display:inline-block;color:inherit;font:inherit;border:1px solid var(--border);border-radius:7px;padding:7px 12px;background:transparent}}
  :is(button,a):focus-visible {{outline:2px solid Highlight}} button:disabled {{opacity:.6}}
</style></head><body><main><h2>Notifications</h2>
<a target="_top" href="{conversations}#notifications">Notifications reçues</a>
<p id="notification-load" role="status"></p><button type="button" id="notification-retry" hidden>Réessayer</button>
</main><script nonce="{nonce}" type="application/json" id="settings-config">{config}</script>{scripts}</body></html>'''.encode('utf-8')
