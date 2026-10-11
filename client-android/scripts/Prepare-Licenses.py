#!/usr/bin/env python3
"""Package full, local license texts for the Android UI, Go runtime and bridge."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

ANDROID = Path(__file__).resolve().parents[1]
ROOT = ANDROID.parent


def run_go(go: Path, arguments: list[str], cwd: Path, environment: dict) -> str:
    result = subprocess.run([str(go), *arguments], cwd=cwd, env=environment,
                            capture_output=True, text=True, encoding='utf-8',
                            timeout=180, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise ValueError('Les informations Go locales sont indisponibles ; compiler le bridge d’abord.')
    return result.stdout


def go_components(root: Path) -> tuple[list[dict], Path]:
    source = root / 'client-qwen' / 'wireguard-bridge'
    go = root / 'client-qwen' / 'wireguard-tools' / 'go' / 'bin' / 'go.exe'
    environment = {**os.environ, 'GOPATH': str(root / 'client-qwen' / 'wireguard-tools' / 'workspace'),
                   'GOTOOLCHAIN': 'local', 'GOPROXY': 'off'}
    # Module metadata is read locally, never from a remote service.
    listed = run_go(go, ['list', '-m', '-f', '{{.Path}}|{{.Version}}|{{.Dir}}', 'all'], source, environment)
    modules = []
    for line in listed.splitlines():
        name, version, directory = line.split('|', 2)
        if not version:  # The bridge itself is covered by the application license.
            continue
        if directory:
            modules.append({'name': name, 'version': version, 'directory': Path(directory)})
    binaries = [root / 'client-android' / 'app/src/main/jniLibs' / abi / 'libfredwireguard.so'
                for abi in ('arm64-v8a', 'x86_64')]
    if any(not binary.is_file() for binary in binaries):
        raise ValueError('Compiler les deux bridges Android avant de préparer leurs licences.')
    required = binary_dependencies(run_go(go, ['version', '-m', *(str(binary) for binary in binaries)], source, environment))
    available = {module['name']: module for module in modules}
    for name, version in required.items():
        if name not in available or available[name]['version'] != version:
            raise ValueError('La licence locale d’une dépendance embarquée dans Android est indisponible.')
    for module in modules:
        module['android_binary_dependency'] = module['name'] in required
    goroot = Path(run_go(go, ['env', 'GOROOT'], source, environment).strip())
    return sorted(modules, key=lambda module: module['name']), goroot


def binary_dependencies(metadata: str) -> dict[str, str]:
    dependencies = {}
    for line in metadata.splitlines():
        values = line.split()
        if values and values[0] == 'dep':
            if len(values) < 3:
                raise ValueError('Les métadonnées du bridge Android sont invalides.')
            name, version = values[1:3]
            if name in dependencies and dependencies[name] != version:
                raise ValueError('Les deux bridges Android utilisent des dépendances différentes.')
            dependencies[name] = version
    if not dependencies:
        raise ValueError('Les métadonnées des dépendances Android sont absentes.')
    return dependencies


def license_files(directory: Path) -> list[Path]:
    """Copy only license/notice names; neither module code nor user data is copied."""
    found = []
    for folder, children, filenames in os.walk(directory, followlinks=False):
        children[:] = sorted(name for name in children if name not in {'.git', '.hg', '.svn'}
                             and not (Path(folder) / name).is_symlink())
        for name in sorted(filenames):
            if re.match(r'^(?:licen[sc]e|copying|notice)(?:$|[._-])', name, re.IGNORECASE):
                candidate = Path(folder) / name
                if not candidate.is_symlink():
                    found.append(candidate)
    return sorted(found, key=lambda path: path.relative_to(directory).as_posix())


def prepare(root: Path, modules: list[dict], goroot: Path) -> dict[str, bytes]:
    packaged = {}
    components = []
    def add(target: str, source: Path):
        relative = PurePosixPath(target)
        if relative.is_absolute() or '..' in relative.parts or not relative.parts:
            raise ValueError('Chemin de licence invalide.')
        data = source.read_bytes()
        if not data or len(data) > 4 * 1024 * 1024:
            raise ValueError('Une licence locale est vide ou trop volumineuse.')
        packaged[relative.as_posix()] = data

    add('application/LICENSE.txt', root / 'client-qwen' / 'LICENSE.txt')
    components.append({'name': 'Accès serveur Fred', 'license_files': ['application/LICENSE.txt']})
    add('go/LICENSE', goroot / 'LICENSE')
    version = (goroot / 'VERSION').read_text(encoding='utf-8').splitlines()[0]
    components.append({'name': 'Go runtime', 'version': version, 'license_files': ['go/LICENSE']})
    add('markdown-it/LICENSE.txt', root / 'client-qwen' / 'vendor' / 'markdown-it-LICENSE.txt')
    vendor_metadata = (root / 'client-qwen' / 'vendor' / 'README.txt').read_text(encoding='utf-8-sig')
    markdown_version = re.search(r'^markdown-it\s+(\S+)', vendor_metadata)
    components.append({'name': 'markdown-it', 'version': markdown_version.group(1) if markdown_version else 'local',
                       'license_files': ['markdown-it/LICENSE.txt']})
    if (root / 'client-voice' / 'model.json').is_file():
        for filename in ('whisper.cpp-LICENSE.txt','ggml-LICENSE.txt','whisper-model-LICENSE.txt','llamafile-LICENSE.txt'):
            target='whisper/'+filename
            add(target,root / 'client-voice' / 'licenses' / filename)
            components.append({'name':filename.split('-LICENSE')[0], 'version':'1.9.5' if filename!='whisper-model-LICENSE.txt' else 'small', 'license_files':[target]})
    for module in modules:
        directory = Path(module['directory'])
        licenses = license_files(directory)
        if not licenses:
            raise ValueError('Un module Go compilé ne contient aucun fichier de licence local.')
        targets = []
        for source in licenses:
            target = 'modules/' + module['name'] + '/' + source.relative_to(directory).as_posix()
            add(target, source)
            targets.append(target)
        components.append({'name': module['name'], 'version': module['version'], 'license_files': targets,
                           'android_binary_dependency': module.get('android_binary_dependency', True)})
    index = {'format': 1, 'components': components,
             'files': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                       for name, data in sorted(packaged.items())}}
    packaged['manifest.json'] = (json.dumps(index, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    headings = ['Accès serveur Fred Android — licences incluses', '',
                'Le code applicatif est sous licence MIT. Chaque composant conserve sa licence.',
                'Les textes originaux complets sont fournis dans ce dossier, sans modification.',
                'Les modules Go téléchargés du bridge sont inclus ; des licences supplémentaires',
                'peuvent concerner uniquement la variante Windows de ce même bridge.', '']
    for component in components:
        headings.append(component['name'] + (' ' + component['version'] if component.get('version') else ''))
        headings.extend('  ' + target for target in component['license_files'])
        headings.append('')
    packaged['NOTICE.txt'] = ('\n'.join(headings) + '\n').encode('utf-8')
    return packaged


def write_package(output: Path, packaged: dict[str, bytes], *, check=False):
    if check:
        for name, data in packaged.items():
            target = output / name
            if not target.is_file() or target.read_bytes() != data:
                raise ValueError('Le paquet de licences Android est absent ou périmé.')
        return
    for name, data in packaged.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, default=ANDROID / 'app/src/main/assets/third-party')
    parser.add_argument('--check', action='store_true')
    arguments = parser.parse_args()
    root = arguments.project_root.resolve()
    modules, goroot = go_components(root)
    packaged = prepare(root, modules, goroot)
    write_package(arguments.output.resolve(), packaged, check=arguments.check)
    print(f'Licences Android {"vérifiées" if arguments.check else "préparées"} : {len(packaged)} fichiers, {len(modules)} modules Go.')


if __name__ == '__main__':
    main()
