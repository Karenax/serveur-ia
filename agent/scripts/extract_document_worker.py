"""Private, single-shot document parser. No database or model startup."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    request = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    try:
        from app.services.document_sandbox import worker
        response = {'ok': True, 'items': worker(request)}
    except (ValueError, OSError, MemoryError, RuntimeError) as exc:
        response = {'ok': False, 'error': str(exc)[:500] or 'Capacité d’extraction dépassée'}
    Path(request['result']).write_text(json.dumps(response, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
