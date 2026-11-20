"""Assemble the private-browser variant of the shared Kiara Conversations UI."""

import hashlib
import json
import re
from pathlib import Path


from kiara_shared.conversation_shell import chat_contextual_help, modern_chat, notification_settings


SOURCE = Path(__file__).resolve().parent.parent / 'client-qwen'
SCRIPTS = ('ui.js', 'attachments.js', 'corrector.js', 'selection.js', 'thinking.js',
           'voice.js', 'conversation.js', 'project-conversation.js')
ROUTES = {
    'GET': frozenset(('/v1/models', '/v1/status', '/v1/history', '/v1/workspace',
                      '/v1/notifications', '/v1/agent/state', '/v1/voice/status')),
    'POST': frozenset(('/v1/chat/completions', '/v1/context', '/v1/cancel', '/v1/history',
                       '/v1/workspace/action', '/v1/notifications/action', '/v1/agent/action',
                       '/v1/voice/speech', '/v1/voice/cancel')),
}


def render(owner, prefix, nonce, *, settings_panel=False, notifications=False):
    def read(name):
        return (SOURCE / name).read_text(encoding='utf-8')

    if notifications:
        return notification_settings(read, nonce, prefix=prefix, web=True)

    def script(name):
        code = read(name).replace('</script', r'<\/script')
        return f'<script nonce="__NONCE__">{code}</script>'

    def slot(markup, name, replacement, *, html=False):
        opening, closing = ('<!--', '-->') if html else ('/\u002a', '\u002a/')
        pattern = (re.escape(opening) + ' kiara-slot:' + name + ' ' + re.escape(closing)
                   + '.*?' + re.escape(opening) + ' /kiara-slot:' + name + ' ' + re.escape(closing))
        result, count = re.subn(pattern, lambda _: replacement, markup, flags=re.S)
        if count != 1:
            raise ValueError(f'Marqueur Conversations absent ou dupliqué : {name}')
        return result

    config = json.dumps({'key': '', 'storage': hashlib.sha256(owner.encode()).hexdigest()[:20],
                         'web_prefix': prefix, 'platform': 'web'})
    heading = script('web_conversations.js') + script('vendor/markdown-it.min.js') + script('markdown.js')
    presentation = read('workspace.html') + ''.join(map(script, SCRIPTS))
    chat = slot(read('chat.html'), 'android-state-13', """async function clientState(){
      try{const state=await api('/client/state');loggedIn=true;uiApplyPreferences(state.preferences);}
      catch(e){error(e);}
    }""")
    for name in ('desktop-endpoint-update-events-14', 'desktop-updater-timer-16'):
        chat = slot(chat, name, '')
    chat = slot(chat, 'access-pane-5', f"""
      <section class="settings-view" data-view="access" hidden><h2>Mon accès personnel</h2>
        <div class="settings-card">
          <form method="post" action="{prefix}/deconnexion"><button class="secondary">Se déconnecter</button></form>
        </div><div class="settings-card"><h3>Vos conversations</h3>
          <p>L’historique personnel est enregistré sur le serveur. Les brouillons enregistrés restent dans ce navigateur.</p>
          <!-- shell:access-tools -->
        </div>
      </section>""", html=True)
    chat = chat.replace('Historique sur le serveur · copie locale chiffrée', 'Historique du serveur')
    if settings_panel:
        chat = chat.replace('<form method="post" action=', '<form target="_top" method="post" action=', 1)
    chat = modern_chat(chat, read('kiara-shell.html'), settings_panel=settings_panel, web=True)
    if not settings_panel:
        chat = chat_contextual_help(chat, read)
    return (chat.replace('</head>', heading + '</head>')
            .replace('</body>', presentation + '</body>')
            .replace('__UI_CSS__', read('ui.css'))
            .replace('__CONFIG__', config).replace('__NONCE__', nonce)).encode('utf-8')
