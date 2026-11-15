"""Compare historical business cells to the verified snapshot, read-only SQLite."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
VOLATILE = {'audit_logs', 'audit_log', 'app_settings', 'schema_migrations', 'cdc_llm_runs', 'thunderbird_jobs',
    'mail_enrichment_jobs', 'memory_projections', 'project_document_jobs'}
VOLATILE_COLUMNS = {'milestone_scan_jobs': {'updated_at', 'status', 'warnings'},
    'project_knowledge_analyses': {'retry_after', 'updated_at'}}


def quote(name):
    return '"' + name.replace('"', '""') + '"'


def digest(row):
    values = [v.hex() if isinstance(v, bytes) else v for v in row]
    return hashlib.sha256(json.dumps(values, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def compare(before_path, actual_path):
    before = sqlite3.connect(before_path.resolve().as_uri() + '?mode=ro', uri=True)
    actual = sqlite3.connect(actual_path.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        before.execute('PRAGMA query_only=ON')
        actual.execute('PRAGMA query_only=ON')
        prior = {r[0] for r in before.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        current = {r[0] for r in actual.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
        result = {'before': str(before_path), 'actual': str(actual_path), 'tables': [], 'missing_tables': sorted(prior-current),
            'new_tables': sorted(current-prior), 'volatile_tables_excluded': sorted(prior & VOLATILE)}
        for table in sorted((prior & current)-VOLATILE):
            columns = [r[1] for r in before.execute(f'PRAGMA table_info({quote(table)})')]
            excluded = sorted(set(columns) & VOLATILE_COLUMNS.get(table, set()))
            columns = [c for c in columns if c not in excluded]
            actual_columns = {r[1] for r in actual.execute(f'PRAGMA table_info({quote(table)})')}
            if not set(columns).issubset(actual_columns):
                result['tables'].append({'name': table, 'passed': False, 'missing_columns': sorted(set(columns)-actual_columns)})
                continue
            sql = 'SELECT ' + ','.join(quote(c) for c in columns) + ' FROM ' + quote(table)
            prior_rows = Counter(digest(r) for r in before.execute(sql))
            current_rows = Counter(digest(r) for r in actual.execute(sql))
            missing = sum((prior_rows-current_rows).values())
            added = sum((current_rows-prior_rows).values())
            result['tables'].append({'name': table, 'passed': missing == 0, 'historical_rows': sum(prior_rows.values()),
                'current_rows': sum(current_rows.values()), 'historical_cells_missing_or_changed': missing, 'rows_added': added,
                'volatile_columns_excluded': excluded})
        result['passed'] = not result['missing_tables'] and all(t['passed'] for t in result['tables'])
        return result
    finally:
        before.close()
        actual.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--brain', type=Path, default=ROOT / 'project_brain.db')
    parser.add_argument('--erp', type=Path, default=Path.home() / '.minipilot' / 'minipilot.db')
    parser.add_argument('--report', type=Path, default=ROOT / 'logs' / 'foresight-runtime' / 'production-preservation.json')
    args = parser.parse_args()
    report = {'created_at': datetime.now(timezone.utc).isoformat(), 'sqlite_mode': 'ro/query_only',
        'brain': compare(args.backup / 'data' / 'brain' / 'project_brain.db', args.brain),
        'erp': compare(args.backup / 'data' / 'erp' / 'minipilot.db', args.erp)}
    report['passed'] = report['brain']['passed'] and report['erp']['passed']
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'tables': sum(len(report[k]['tables']) for k in ['brain', 'erp']),
        'historical_rows': sum(t.get('historical_rows', 0) for k in ['brain', 'erp'] for t in report[k]['tables']),
        'report': str(args.report)}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
