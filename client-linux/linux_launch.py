"""Run the unmodified shared UI and loopback API with Linux platform services."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys

CLIENT_MODULES = ('client','linux_support','linux_system_audio','fred_http','product','updater','history_store','wg_bridge',
                  'connection_settings','app_integrations','hermes_catalogue','file_lock','portal_origin_state',
                  'portal_origin_plan','portal_origin_session','portal_recovery_broker','portal_recovery_stdio',
                  'portal_migration_plan','portal_migration_job','portal_migration_windows','portal_migration_coordinator',
                  'portal_migration_state','relay_control_stream','draft_store','history_sync','history_migrations',
                  'chat_attachments','opencode_visibility','advanced_voice','max_installation','local_voice','conversation_service')
CLIENT_ASSETS = ('chat.html','kiara-shell.html','workspace.html','ui.css','ui.js','markdown.js','attachments.js','corrector.js',
                 'help.html','help.css','help.mjs',
                 'selection.js','thinking.js','voice.js','conversation.js','project-conversation.js','linux_features.js',
                 'fred-icon.png','LICENSE.txt','THIRD-PARTY.txt','portal_origin_inventory.js','portal_origin_recovery.js',
                 'portal_origin_scan.html','portal_origin_scan.js','portal_origin_transfer.html','portal_origin_transfer.js',
                 'portal_origin_sender.js','portal_origin_sender_result.js','portal_origin_receiver.js','portal_origin_window.js',
                 'portal_origin_snapshot.js','portal_conflict_archive.js','portal_conflict_review.js','portal_conflict_review.css',
                 'portal_conflict_library.js','portal_conflict_library.css','portal_audio_conflict_archive.js',
                 'portal_audio_conflict_review.js','portal_audio_conflict_library.js','portal_origin_manifest.js')
REQUIRED_FILES = frozenset({
    'kiara', 'kiara-relay', 'start-tauri.sh', 'start.sh', 'installer.py', 'linux_launch.py', 'requirements.txt', 'requirements.lock', 'README.md',
    'client/wireguard-bridge', 'client/screen_capture.py', 'client/recovery_init.js',
    'client/vendor/markdown-it.min.js', 'client/vendor/markdown-it-LICENSE.txt', 'client/vendor/README.txt',
    *(f'client/{name}.py' for name in CLIENT_MODULES), *(f'client/{name}' for name in CLIENT_ASSETS),
    *(f'client/voice/conversation-worker/{name}.py' for name in
      ('conversation_worker','aec_capture','linux_audio','recognition','turn_features','max_recognition','wakeword_recognition')),
    'client/voice/conversation-models.json',
    *(f'client/voice/wakeword/{name}' for name in
      ('manifest.json','encoder.onnx','decoder.onnx','joiner.onnx','tokens.txt','keywords.txt',
       'KOTLIN-APACHE-2.0.txt','ONNXRUNTIME-MIT.txt','SHERPA-APACHE-2.0.txt')),
    *(f'shared/kiara_shared/{name}.py' for name in
      ('__init__','agent_auth','agent_http','agent_workers','attachments','conversation_shell','file_lock','history_store','http','http_download',
       'profiles','releases','request_ids','thunderbird','thunderbird_package','version','voice_packs','voice_runtime')),
})


def verify_files(root):
    manifest = json.loads((root/'build-manifest.json').read_text(encoding='utf-8'))
    if (not isinstance(manifest, dict) or type(manifest.get('format')) is not int or manifest['format'] != 1
            or manifest.get('component') != 'linux' or manifest.get('shell') != 'tauri'
            or not isinstance(manifest.get('files'), dict) or not REQUIRED_FILES <= manifest['files'].keys()):
        raise ValueError('Manifeste du paquet Linux incomplet ou invalide.')
    for name, digest in manifest['files'].items():
        if not isinstance(name, str) or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('Manifeste du paquet Linux invalide.')
        relative = PurePosixPath(name)
        if not relative.parts or relative.as_posix() != name or relative.is_absolute() or '..' in relative.parts or '\\' in name:
            raise ValueError('Chemin de paquet invalide.')
        path = root/name
        current = root
        for part in relative.parts:
            current = current/part
            if current.is_symlink():
                raise ValueError('Lien inattendu dans le paquet Linux.')
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Lien inattendu dans le paquet Linux.')
        with path.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest() != digest:
                raise ValueError('Paquet Linux incomplet ou altéré : '+name)


def main():
    if not sys.platform.startswith('linux'):
        raise SystemExit('Ce lanceur est réservé à Linux.')
    if os.geteuid() == 0:
        raise SystemExit('Ouvrez Kiara depuis votre session habituelle, sans sudo.')
    root = Path(__file__).resolve().parent
    os.umask(0o077)
    verify_files(root)
    if '--verify-package' in sys.argv:
        print('Paquet Kiara vérifié.')
        return
    sys.path[:0] = [str(root/'client'),str(root/'shared'),str(root/'client/voice/conversation-worker')]
    if '--audio-self-test' in sys.argv:
        from linux_audio import audio_self_test
        print(json.dumps(audio_self_test()))
        return
    if not ({'--relay-stdio','--self-test','--sync-agent-capture'} & set(sys.argv[1:])):
        raise SystemExit('Ouvrez Kiara avec ./start-tauri.sh.')
    import client
    client.main()


if __name__ == '__main__':
    main()
