#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ ! -x "$base/.venv/bin/python" ]; then
    printf '%s\n' 'Exécutez d’abord : python3 installer.py' >&2
    exit 1
fi
if [ ! -x "$base/kiara" ] || [ ! -x "$base/kiara-relay" ]; then
    printf '%s\n' 'Le client Tauri est incomplet. Réinstallez le paquet complet.' >&2
    exit 1
fi
export PYTHONNOUSERSITE=1
umask 077
"$base/.venv/bin/python" "$base/linux_launch.py" --verify-package
exec "$base/kiara" "$@"
