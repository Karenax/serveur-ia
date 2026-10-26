"""Back up and install the strict RAM profile and the server admission check."""
import ast
import difflib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SERVER = ROOT / 'dependances/strata-0.1.43.1/source/serve/server.py'
ANCHOR = '        self.known_ctx = self.max_context   # survives a failed restart: requests keep their limit and restart it\n'
GUARD = '''        # Kiara: enforce physical residency on every load, including automatic restarts.
        if (env or os.environ).get("KIARA_REQUIRE_LOCKED_RAM") == "1":
            try:
                from serve.ram_residency import verify_locked_ram
                verify_locked_ram(log, log_start, args)
            except (OSError, ValueError, IndexError, TypeError, ImportError) as error:
                self.max_context = 0
                self.proc.kill()
                try:
                    self.proc.wait(timeout=10)
                finally:
                    self.proc.stdin.close()
                    self.proc.stdout.close()
                    if log:
                        self.log.close()
                raise EngineDied("Chargement en RAM refusé : " + str(error) +
                                 " Libérez de la mémoire puis relancez le modèle.") from error
'''


def main():
    backup = OUT / 'avant'
    if backup.exists():
        raise RuntimeError('Sauvegarde déjà présente ; ne pas écraser les fichiers précédents.')
    names = ['lanceur/base-strata.json', 'strata-iq4-p100-hybride.json']
    for name in names + [str(SERVER.relative_to(ROOT)), 'lanceur/session.json']:
        target = backup / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    old = SERVER.read_text(encoding='utf-8')
    if old.count(ANCHOR) != 1 or 'KIARA_REQUIRE_LOCKED_RAM' in old:
        raise RuntimeError('Source serveur inattendue : installation interrompue.')
    new = old.replace(ANCHOR, GUARD + ANCHOR)
    ast.parse(new)
    (OUT / 'server.patch').write_text(''.join(difflib.unified_diff(
        old.splitlines(keepends=True), new.splitlines(keepends=True),
        fromfile='a/serve/server.py', tofile='b/serve/server.py')), encoding='utf-8')
    shutil.copy2(OUT / 'ram_residency.py', SERVER.with_name('ram_residency.py'))
    SERVER.write_text(new, encoding='utf-8')
    for name in names:
        path = ROOT / name
        cfg = json.loads(path.read_text(encoding='utf-8-sig'))
        args = cfg['args']
        args.insert(args.index('--resident-cpu-experts') + 1, '--resident-experts')
        # The user's target is about 70 GiB used: keep the 27 GiB PLE on C:.
        args[args.index('--ple-io') + 1] = 'direct'
        cfg['env'].update(STRATA_RESIDENT_PIN='1', STRATA_RESIDENT_HEADROOM_GIB='6',
                          KIARA_REQUIRE_LOCKED_RAM='1')
        path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('Profils RAM et contrôle de résidence installés ; redémarrage nécessaire.')


if __name__ == '__main__':
    main()
