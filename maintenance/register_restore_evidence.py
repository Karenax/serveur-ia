"""Register the report of a completed isolated restore against the backup catalogue."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'lanceur'))
from restore_evidence import record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--backup-home', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.resolve(strict=True).read_text(encoding='utf-8-sig'))
    record(args.backup_home.resolve(strict=True), report)
    print('Preuve de restauration isolée enregistrée pour la paire du catalogue.')


if __name__ == '__main__':
    main()
