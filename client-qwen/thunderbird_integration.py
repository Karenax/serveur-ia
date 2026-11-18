"""Install Kiara's paired MailExtension for the current Windows account."""

import configparser
import json
import os
from pathlib import Path
import re
import secrets
import winreg
import psutil

from kiara_shared.thunderbird_package import package

EXTENSION_ID = 'agent-bridge@agent.local'
POLICY_PATH = r'Software\Policies\Mozilla\Thunderbird'


def policy(hive):
    try:
        with winreg.OpenKey(hive, POLICY_PATH, 0, winreg.KEY_QUERY_VALUE) as key:
            raw, kind = winreg.QueryValueEx(key, 'ExtensionSettings')
    except FileNotFoundError:
        return {}
    except PermissionError as error:
        raise ValueError('Windows refuse la lecture des stratégies Thunderbird pour ce compte.') from error
    if kind == winreg.REG_MULTI_SZ:
        raw = '\n'.join(raw)
    try:
        result = json.loads(raw)
    except (TypeError, ValueError) as error:
        raise ValueError('La stratégie Thunderbird est illisible. Contactez votre administrateur.') from error
    if not isinstance(result, dict):
        raise ValueError('La stratégie Thunderbird est invalide.')
    return result


def write_user_policy(policies):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, POLICY_PATH, 0, winreg.KEY_SET_VALUE)
    except FileNotFoundError:
        key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, POLICY_PATH, 0, winreg.KEY_SET_VALUE)
    with key:
        winreg.SetValueEx(key, 'ExtensionSettings', 0, winreg.REG_MULTI_SZ,
                         json.dumps(policies, indent=2).splitlines())


def distribution_policy():
    folders = [Path(process.info['exe']).parent
               for process in psutil.process_iter(['name', 'exe'])
               if (process.info['name'] or '').casefold() == 'thunderbird.exe' and process.info['exe']]
    if not folders and os.environ.get('APPDATA'):
        thunderbird = Path(os.environ['APPDATA']) / 'Thunderbird'
        configs = configparser.ConfigParser(interpolation=None)
        try:
            configs.read(thunderbird / 'profiles.ini', encoding='utf-8-sig')
            for name in configs.sections():
                if name.startswith('Install') and configs.has_option(name, 'Default'):
                    compatibility = configparser.ConfigParser(interpolation=None)
                    compatibility.read(thunderbird / configs[name]['Default'] / 'compatibility.ini',
                                       encoding='utf-8-sig')
                    app_dir = Path(compatibility.get('Compatibility', 'LastAppDir', fallback=''))
                    if app_dir.is_absolute():
                        folders.append(app_dir)
        except (configparser.Error, OSError, ValueError):
            pass
    if not folders:
        folders = [Path(os.environ[name]) / 'Mozilla Thunderbird'
                   for name in ('ProgramFiles', 'ProgramFiles(x86)') if os.environ.get(name)]
    for folder in dict.fromkeys(folders):
        if not (folder / 'thunderbird.exe').is_file():
            continue
        path = folder / 'distribution' / 'policies.json'
        try:
            addon = json.loads(path.read_text(encoding='utf-8-sig'))['policies']['ExtensionSettings'][EXTENSION_ID]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if isinstance(addon, dict) and addon.get('installation_mode') in ('force_installed', 'normal_installed', 'blocked'):
            return path
    return None


def manage(profile, source, *, enable=False, inspect=False):
    from client import read_settings_for_update, protect, settings_path
    from kiara_shared.file_lock import locked
    from kiara_shared.history_store import atomic

    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    version = manifest['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+', version) or manifest['browser_specific_settings']['gecko']['id'] != EXTENSION_ID:
        raise ValueError('Extension Thunderbird Kiara invalide.')
    if (enable or inspect) and (old_policy := distribution_policy()):
        raise ValueError(f'Une stratégie Thunderbird contrôle déjà l’extension. Fichier : {old_policy}')
    settings = settings_path(profile)
    folder = settings.parent / f'thunderbird-{settings.stem}'
    output = folder / f'agent-thunderbird-{version}.xpi'
    with locked(settings.parent / 'thunderbird-policy'), locked(settings):
        values = read_settings_for_update(profile)
        policies = policy(winreg.HKEY_CURRENT_USER)
        registered = policies.get(EXTENSION_ID)
        current = registered.get('install_url', '') if isinstance(registered, dict) else ''
        owned = isinstance(current, str) and current.startswith(folder.as_uri() + '/')
        if inspect:
            if registered is None and values.get('thunderbird_token') and output.is_file():
                return {'version': version, 'managed': False, 'manual_path': str(output)}
            return {'version': version, 'managed': bool(owned and values.get('thunderbird_token')),
                    'update_available': bool(owned and current != output.as_uri())}
        if not enable and not (owned and values.get('thunderbird_token')):
            return {'version': version, 'managed': False}
        if registered is not None and not owned:
            raise ValueError('Une autre liaison Thunderbird est déjà configurée pour ce compte Windows.')
        if EXTENSION_ID in policy(winreg.HKEY_LOCAL_MACHINE):
            raise ValueError('La liaison Thunderbird est gérée par votre organisation.')
        previous = re.search(r'/agent-thunderbird-(\d+\.\d+\.\d+)\.xpi$', current)
        if previous and tuple(map(int, previous[1].split('.'))) > tuple(map(int, version.split('.'))):
            return {'version': previous[1], 'managed': True}
        token = values.get('thunderbird_token') or secrets.token_urlsafe(32)
        if not output.is_file() or not values.get('thunderbird_token'):
            try:
                package(source, output, token, kiara=True)
            except PermissionError as error:
                raise ValueError('Windows refuse l’écriture du fichier Thunderbird dans le dossier local de Kiara.') from error
        if not values.get('thunderbird_token'):
            values['thunderbird_token'] = token
            try:
                atomic(settings, protect(json.dumps(values)))
            except PermissionError as error:
                raise ValueError('Windows refuse l’enregistrement de la liaison Thunderbird dans le profil Kiara.') from error
        if current != output.as_uri():
            policies[EXTENSION_ID] = {'installation_mode': 'normal_installed', 'install_url': output.as_uri()}
            try:
                write_user_policy(policies)
            except PermissionError:
                return {'version': version, 'managed': owned, 'manual_path': str(output)}
    return {'version': version, 'managed': True, 'restart_required': current != output.as_uri()}
