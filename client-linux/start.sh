#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ ! -x "$base/.venv/bin/python" ]; then
    printf '%s\n' 'Exécutez d’abord : python3 installer.py' >&2
    exit 1
fi
export PYTHONNOUSERSITE=1
umask 077
case " $* " in
    *" --self-test "*|*" --audio-self-test "*) exec "$base/.venv/bin/python" "$base/linux_launch.py" "$@" ;;
    *) exec "$base/start-tauri.sh" "$@" ;;
esac
