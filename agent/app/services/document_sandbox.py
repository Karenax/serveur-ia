"""Bound untrusted document parsing in a disposable, resource-limited process."""
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
EXTRACTION_TIMEOUT_SECONDS = 90
EXTRACTION_MEMORY_BYTES = 1024**3
MAX_RESULT_BYTES = 16 * 1024**2


def extract(path, filename, kind, *, python=None):
    with tempfile.TemporaryDirectory(prefix='agent-extract-') as directory:
        output = Path(directory) / 'result.json'
        request = Path(directory) / 'request.json'
        request.write_text(json.dumps({'path': str(Path(path).resolve()), 'filename': filename,
            'kind': kind, 'result': str(output), 'memory_bytes': EXTRACTION_MEMORY_BYTES}), encoding='utf-8')
        try:
            result = subprocess.run([str(python or sys.executable), str(ROOT / 'scripts/extract_document_worker.py'),
                str(request)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=EXTRACTION_TIMEOUT_SECONDS, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except subprocess.TimeoutExpired as exc:
            raise ValueError('Extraction trop longue ; original conservé, traitement à reprendre') from exc
        if result.returncode or not output.is_file() or output.stat().st_size > MAX_RESULT_BYTES:
            raise ValueError('Extraction interrompue ou capacité dépassée ; original conservé')
        response = json.loads(output.read_text(encoding='utf-8'))
        if not response.get('ok'):
            raise ValueError(response.get('error') or 'Document illisible ; original conservé')
        return response['items']


def extract_cdc(path, filename):
    from backend.app.services.cdc_extraction import CdcExtractionError, ExtractedPage
    try:
        return [ExtractedPage(**item) for item in extract(path, filename, 'cdc')]
    except (ValueError, OSError) as exc:
        raise CdcExtractionError(str(exc)) from exc


def worker(request):
    from .process_limits import limit_process
    limit_process(request['memory_bytes'])
    if request['kind'] == 'pdf_info':
        from pypdf import PdfReader
        count = len(PdfReader(request['path']).pages)
        if count > 2000:
            raise ValueError('Document limité à 2000 pages')
        return {'pages': count}
    if request['kind'] == 'cdc':
        from backend.app.services.cdc_extraction import _extract_document_local
        items = [asdict(page) for page in _extract_document_local(Path(request['path']), request['filename'])]
    elif request['kind'] == 'library':
        from .library_extraction import _extract_local
        items = _extract_local(Path(request['path']), request['filename'])
    elif request['kind'] == 'mail_attachment':
        from .mail_attachment_extraction import _extract_local
        items = _extract_local(Path(request['path']), request['filename'])
    elif request['kind'] == 'mail_pdfium':
        from .mail_attachment_extraction import _extract_pdfium
        items = _extract_pdfium(Path(request['path']))
    elif request['kind'] == 'mail_image':
        from .mail_attachment_extraction import _normalize_image
        items = [_normalize_image(Path(request['path']))]
    else:
        raise ValueError('Format de commande d’extraction invalide')
    return items
