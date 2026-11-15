"""Read-only storage/retention review. No delete or move operation exists here."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
REVIEW_ROOTS = ('.ui-preview', 'logs', 'backups', '.models', 'v', '.pytest_work', 'tmp_tests_sessions')


def inventory(root=ROOT):
    root = Path(root).resolve()
    result = {'checked_at': datetime.now(timezone.utc).isoformat(), 'free_bytes': shutil.disk_usage(root).free,
              'mode': 'review-only', 'deletion_authorized': False, 'directories': {},
              'protected': ['context and Markdown files', 'active canonical data', 'human decisions',
                            'unique evidence', 'retained backups', 'external link targets']}
    for name in REVIEW_ROOTS:
        total = count = errors = 0
        def onerror(_error):
            nonlocal errors
            errors += 1
        for here, dirs, files in os.walk(root / name, onerror=onerror):
            dirs[:] = [directory for directory in dirs if not (Path(here) / directory).is_symlink()
                       and not getattr(os.path, 'isjunction', lambda path: False)(Path(here) / directory)]
            for filename in files:
                path = Path(here) / filename
                try:
                    if not path.is_symlink():
                        total += path.stat().st_size
                        count += 1
                except OSError:
                    errors += 1
        result['directories'][name] = {'accessible_bytes': total, 'files': count, 'access_errors': errors,
                                      'is_minimum': bool(errors), 'requires_human_review': True}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choisir un rapport neuf pour conserver les inventaires précédents')
    value = inventory()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(args.output), 'free_bytes': value['free_bytes'], 'mode': value['mode']}))


if __name__ == '__main__':
    main()
