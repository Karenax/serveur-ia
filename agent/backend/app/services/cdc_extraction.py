"""Moteur d'analyse CDC repris de XPilot (extraction document + citations).

Port fidèle de `backend/app/services/cdc_document_extraction.py` (XPilot) :
mêmes formats, mêmes seuils de qualité, même détection du texte barré.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from pypdf import PdfReader
from pypdf.errors import PdfReadError

ALLOWED_CDC_SUFFIXES = {".pdf", ".docx", ".xlsx", ".xlsm", ".csv", ".txt", ".md"}
MAX_EXTRACTED_CELLS = 200_000
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


class CdcExtractionError(ValueError):
    """Document illisible ou format non pris en charge."""


@dataclass(frozen=True)
class ExtractedPage:
    physical_page: int
    printed_page: str | None
    text: str
    quality: float
    visual_review_required: bool


def validate_cdc_filename(file_name: str) -> str:
    normalized = Path(file_name).name.strip()
    if not normalized or normalized in {".", ".."}:
        raise CdcExtractionError("Le nom du document CDC est invalide.")
    if Path(normalized).suffix.casefold() not in ALLOWED_CDC_SUFFIXES:
        allowed = ", ".join(sorted(ALLOWED_CDC_SUFFIXES))
        raise CdcExtractionError(
            f"Format CDC non pris en charge. Formats autorises : {allowed}.")
    return normalized


def extract_document(path: Path, file_name: str) -> list[ExtractedPage]:
    from app.services.document_sandbox import extract_cdc
    return extract_cdc(path, file_name)


def _extract_document_local(path: Path, file_name: str) -> list[ExtractedPage]:
    suffix = Path(file_name).suffix.casefold()
    try:
        if suffix in {".docx", ".xlsx", ".xlsm"}:
            with ZipFile(path) as archive:
                entries = archive.infolist()
                if len(entries) > 10000 or sum(x.file_size for x in entries) > 100 * 1024 * 1024:
                    raise CdcExtractionError("Document décompressé trop volumineux")
        if suffix == ".pdf":
            return _extract_pdf(path)
        if suffix == ".docx":
            return _extract_docx(path)
        if suffix in {".xlsx", ".xlsm"}:
            return _extract_xlsx(path)
        if suffix in {".csv", ".txt", ".md"}:
            return [_text_page(_decode_text(path.read_bytes()), 1)]
    except (BadZipFile, OSError, ValueError, KeyError, PdfReadError) as exc:
        raise CdcExtractionError(f"Le document ne peut pas etre extrait : {exc}") from exc
    raise CdcExtractionError("Le format du document CDC n'est pas pris en charge.")


def _extract_pdf(path: Path) -> list[ExtractedPage]:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # pypdf expose des erreurs moteur spécifiques
            raise CdcExtractionError("Le PDF est chiffre et ne peut pas etre analyse.") from exc
    pages: list[ExtractedPage] = []
    if len(reader.pages) > 2000:
        raise CdcExtractionError("Document limité à 2000 pages")
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:  # une page malformée reste visible pour revue
            text = ""
        pages.append(_text_page(text, index))
    if not pages:
        raise CdcExtractionError("Le PDF ne contient aucune page.")
    return pages


def _extract_docx(path: Path) -> list[ExtractedPage]:
    from defusedxml import ElementTree as SafeElementTree  # noqa: PLC0415 (optionnel)

    with ZipFile(path) as archive:
        xml = archive.read("word/document.xml")
    root = SafeElementTree.fromstring(xml)
    lines: list[str] = []
    for paragraph in root.iter(f"{{{WORD_NS}}}p"):
        fragments: list[str] = []
        for run in paragraph.iter(f"{{{WORD_NS}}}r"):
            run_text = "".join(node.text or "" for node in run.iter(f"{{{WORD_NS}}}t")).strip()
            if not run_text:
                continue
            struck = run.find(f"{{{WORD_NS}}}rPr/{{{WORD_NS}}}strike") is not None
            fragments.append(f"[BARRE] {run_text}" if struck else run_text)
        line = " ".join(fragments).strip()
        if line:
            lines.append(line)
    return [_text_page("\n".join(lines), 1)]


def _extract_xlsx(path: Path) -> list[ExtractedPage]:
    workbook = load_workbook(filename=path, read_only=True, data_only=True, keep_links=False)
    pages: list[ExtractedPage] = []
    extracted_cells = 0
    try:
        for page_number, sheet in enumerate(workbook.worksheets, start=1):
            lines = [f"Feuille : {sheet.title}"]
            for row in sheet.iter_rows():
                row_values: list[str] = []
                for cell in row:
                    if cell.value is None or str(cell.value).strip() == "":
                        continue
                    extracted_cells += 1
                    if extracted_cells > MAX_EXTRACTED_CELLS:
                        raise CdcExtractionError(
                            "Le classeur depasse la limite de cellules extractibles.")
                    coordinate = f"{get_column_letter(cell.column)}{cell.row}"
                    row_values.append(f"{coordinate} = {cell.value}")
                if row_values:
                    lines.append(" | ".join(row_values))
            pages.append(_text_page("\n".join(lines), page_number, sheet.title))
    finally:
        workbook.close()
    return pages or [_text_page("", 1)]


def _text_page(text: str, physical_page: int, printed_page: str | None = None) -> ExtractedPage:
    cleaned = "\n".join(line.strip() for line in text.replace("\r", "\n").splitlines())
    cleaned = "\n".join(line for line in cleaned.splitlines() if line)
    length = len(cleaned)
    quality = 1.0 if length >= 200 else 0.5 if length >= 30 else 0.2 if length else 0.0
    return ExtractedPage(physical_page=physical_page, printed_page=printed_page, text=cleaned,
                         quality=quality, visual_review_required=quality < 0.5)


def _decode_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")
