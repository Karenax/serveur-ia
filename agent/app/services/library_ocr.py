"""Explicit local scan extraction; immutable originals and evidence interpretations."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time
import uuid

from fastapi import HTTPException
from sqlalchemy import update

from ..models import Source, SourceArtifact
from ..source_library_models import LibraryItem, LibraryVersion
from .current_evidence import is_current_evidence
from .library_extraction import MAX_TEXT
from .project_access import require_brain

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/windows_ocr.ps1'
OCR_TIMEOUT_SECONDS = 90
RENDER_TIMEOUT_SECONDS = 60
DOCUMENT_TIMEOUT_SECONDS = 15 * 60
_locks = {}
_cancellations = {}
_guard = threading.Lock()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def file_hash(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            result.update(block)
    return result.hexdigest()


def powershell(*args):
    if os.name != 'nt':
        raise ValueError('OCR Windows indisponible sur ce système')
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive',
                             '-ExecutionPolicy', 'RemoteSigned', '-File', str(SCRIPT), *args],
                            stdin=subprocess.DEVNULL, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW,
        timeout=OCR_TIMEOUT_SECONDS)
    if result.returncode:
        raise ValueError('OCR Windows indisponible : vérifiez les langues installées et le fichier original')
    return json.loads(result.stdout.decode('utf-8'))


def profile():
    from .pdf_render import PDF_RENDER_PROFILE
    status = powershell('-Status')
    languages = status['languages']
    language = next((item for item in ('fr-FR', 'en-US') if item in languages), None)
    if not language:
        raise ValueError('Installer la reconnaissance Windows française ou anglaise pour utiliser l’OCR')
    return {'engine':'windows-ocr', 'language':language, 'windows_build':status['windows_build'],
            'engine_version':status['engine_version'], 'script_sha256':file_hash(SCRIPT),
            'render':PDF_RENDER_PROFILE, 'contract':1}


def recognize_page(original, page, storage, expected_hash, settings):
    """Checkpoint each page; retries reuse it without re-opening the OCR engine."""
    from .pdf_render import runtime_python
    key = digest({'sha256':expected_hash, 'page':page, 'profile':settings})
    directory = storage/'ocr'/key
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory/'result.json'
    if receipt.exists():
        saved = json.loads(receipt.read_text(encoding='utf-8'))
        payload = saved['result']
        if (saved.get('sha256') != digest(payload) or payload.get('original_sha256') != expected_hash
                or payload.get('physical_page') != page or payload.get('profile') != settings):
            raise ValueError('Résultat OCR conservé incompatible ; original et tentative préservés')
        return payload
    image = directory/(uuid.uuid4().hex+'.png')
    python = runtime_python()
    result = subprocess.run([str(python), str(ROOT/'scripts/render_pdf.py'),
        '--input', str(original), '--output', str(image), '--storage', str(storage), '--page', str(page)],
        stdin=subprocess.DEVNULL, capture_output=True, encoding='utf-8',
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        timeout=RENDER_TIMEOUT_SECONDS)
    if result.returncode or not image.is_file():
        raise ValueError('Rendu PDF indisponible ; original conservé')
    rendered = json.loads(result.stdout)
    if rendered.get('source_sha256') != expected_hash or rendered.get('physical_page') != page:
        raise ValueError('Original modifié pendant le rendu PDF')
    recognized = powershell('-InputImage', str(image), '-LanguageTag', settings['language'])
    if not isinstance(recognized.get('text'), str) or recognized.get('language') != settings['language']:
        raise ValueError('Réponse OCR incompatible')
    payload = {**recognized, 'original_sha256':expected_hash, 'physical_page':page,
               'profile':settings, 'image_sha256':file_hash(image)}
    temporary = directory/(uuid.uuid4().hex+'.json.part')
    temporary.write_text(json.dumps({'result':payload, 'sha256':digest(payload)}, ensure_ascii=False), encoding='utf-8')
    temporary.replace(receipt)
    return payload


def recognize_source(db, source_id, *, storage=None):
    from backend.app.services.project_operator import current_operator
    from .source_library import require_enabled
    require_enabled(db)
    if current_operator().role == 'reader':
        raise HTTPException(403, 'Opérateur en lecture seule')
    with _guard:
        lock = _locks.setdefault(source_id, threading.Lock())
    if not lock.acquire(blocking=False):
        raise HTTPException(409, 'Reconnaissance déjà en cours pour ce document')
    cancellation = threading.Event()
    with _guard:
        _cancellations[source_id] = cancellation
    try:
        return _recognize_source(db, source_id, storage=storage, cancellation=cancellation)
    except subprocess.TimeoutExpired as exc:
        db.rollback()
        raise HTTPException(409, 'Reconnaissance trop longue ; original et pages traitées conservés, reprendre le traitement') from exc
    except (ValueError, OSError, KeyError) as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc
    finally:
        with _guard:
            _cancellations.pop(source_id, None)
        lock.release()


def cancel_source(db, source_id):
    from backend.app.services.project_operator import current_operator
    source = db.get(Source, source_id)
    if not source or not source.project_id:
        raise HTTPException(404, 'Source introuvable')
    require_brain(source.project_id)
    if current_operator().role == 'reader':
        raise HTTPException(403, 'Opérateur en lecture seule')
    with _guard:
        cancellation = _cancellations.get(source_id)
        if cancellation:
            cancellation.set()
    return {'source_id': source_id, 'cancel_requested': cancellation is not None,
            'original_preserved': True}


def _recognize_source(db, source_id, *, storage=None, cancellation=None):
    from ..config import RAW_DIR
    from .projections import enqueue
    source = db.get(Source, source_id)
    if not source or not source.project_id:
        raise HTTPException(404, 'Source introuvable')
    require_brain(source.project_id)
    meta = source.source_metadata or {}
    item = db.get(LibraryItem, meta.get('library_item_id')) if meta.get('library_item_id') else None
    version = db.get(LibraryVersion, meta.get('library_version_id')) if meta.get('library_version_id') else None
    if (not item or not version or version.item_id != item.id or item.project_id != source.project_id
            or Path(meta.get('filename', '')).suffix.casefold() != '.pdf'):
        raise HTTPException(409, 'Choisissez un PDF conservé dans les Sources pour reconnaître son texte')
    if item.current_source_id != source.id or not is_current_evidence(source):
        raise HTTPException(409, 'Le document a changé ; actualisez les Sources avant de reprendre l’OCR')
    root = Path(storage or RAW_DIR).resolve()
    original = Path(source.original_uri).resolve()

    def check_original():
        if (not original.is_relative_to(root) or not original.is_file() or original.is_symlink()
                or original.stat().st_size != version.size_bytes or file_hash(original) != version.content_sha256):
            raise ValueError('Original conservé incompatible ; reconnaissance refusée')

    check_original()
    artifacts = db.query(SourceArtifact).filter_by(source_id=source.id).all()
    artifacts.sort(key=lambda row: (row.content_json or {}).get('ordinal', 0))
    pending = [row for row in artifacts if (row.content_json or {}).get('physical_page')
               and not (row.content_text or '').strip() and not (row.content_json or {}).get('superseded')]
    if not pending:
        return {'source_id':source.id, 'recognized_pages':0, 'empty_pages':0, 'replayed':True,
                'extraction_status':meta.get('extraction_status'), 'current':True}
    settings = profile()
    results = {}
    deadline = time.monotonic() + DOCUMENT_TIMEOUT_SECONDS
    for artifact in pending:
        if cancellation is not None and cancellation.is_set():
            raise HTTPException(409, 'Reconnaissance annulée ; original et pages traitées conservés')
        if time.monotonic() >= deadline:
            raise HTTPException(409, 'Durée de reconnaissance atteinte ; reprendre pour traiter les pages restantes')
        page = artifact.content_json['physical_page']
        if not isinstance(page, int) or page < 1:
            raise ValueError('Numéro de page PDF invalide')
        results[artifact.id] = recognize_page(original, page, root, version.content_sha256, settings)
    if cancellation is not None and cancellation.is_set():
        raise HTTPException(409, 'Reconnaissance annulée ; original et pages traitées conservés')
    check_original()
    recognized_count = sum(bool(row['text'].strip()) for row in results.values())
    empty_count = len(results)-recognized_count
    if not recognized_count:
        return {'source_id':source.id, 'recognized_pages':0, 'empty_pages':empty_count,
                'extraction_status':meta.get('extraction_status'), 'current':True}
    if sum(len(results[a.id]['text'] if a.id in results else a.content_text or '') for a in artifacts) > MAX_TEXT:
        raise ValueError('Texte OCR supérieur à la capacité documentaire de 2 millions de caractères')
    interpretation = str(uuid.uuid5(uuid.UUID(source.id), 'windows-ocr:'+digest(results)))
    # All recognition is complete before changing canonical evidence. A concurrent
    # import may win; conditional binding prevents moving a newer version back.
    db.refresh(source)
    if not is_current_evidence(source):
        raise HTTPException(409, 'Source remplacée pendant la reconnaissance ; résultats locaux conservés')
    existing = db.get(Source, interpretation)
    if existing:
        db.refresh(item)
        return {'source_id':existing.id, 'recognized_pages':recognized_count, 'empty_pages':empty_count,
                'replayed':True, 'current':item.current_source_id == existing.id,
                'extraction_status':existing.source_metadata['extraction_status']}
    metadata = {**source.source_metadata, 'extraction_version_id':interpretation,
        'reinterprets_source_id':source.id, 'ocr_profile':settings,
        'extraction_status':'ocr_partial' if empty_count else 'ocr_extracted', 'extraction_error':None,
        'visual_review_required':True, 'superseded':False}
    new = Source(id=interpretation, project_id=source.project_id, status='resolved', source_type=source.source_type,
        original_uri=source.original_uri, sha256=digest([item.id, version.content_sha256, interpretation]),
        mime_type=source.mime_type, author=source.author, source_metadata=metadata)
    db.add(new)
    db.flush()
    for artifact in artifacts:
        recognized = results.get(artifact.id)
        locator = {**(artifact.content_json or {}), 'extraction_version_id':interpretation,
                   'content_version_id':version.id}
        if recognized:
            locator.update(text_is_OCR=True, visual_review_required=True, ocr_profile=settings,
                ocr_lines=recognized['lines'], image_dimensions=[recognized['width'], recognized['height']],
                extraction_status='ocr_extracted' if recognized['text'].strip() else 'ocr_no_text')
        db.add(SourceArtifact(source_id=new.id, kind=artifact.kind,
            content_text=recognized['text'] if recognized else artifact.content_text, content_json=locator))
    changed = db.execute(update(LibraryItem).where(LibraryItem.id == item.id,
        LibraryItem.current_source_id == source.id).values(current_source_id=new.id))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, 'Version remplacée pendant la reconnaissance ; résultats locaux conservés')
    source.source_metadata = {**source.source_metadata, 'superseded':True}
    enqueue(db, source.project_id, 'evidence', source_id=new.id)
    db.commit()
    return {'source_id':new.id, 'recognized_pages':recognized_count, 'empty_pages':empty_count,
            'extraction_status':metadata['extraction_status'], 'current':True, 'replayed':False}
