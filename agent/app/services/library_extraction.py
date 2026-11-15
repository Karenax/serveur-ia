"""Extract retained files with actual page, sheet and cell locators."""
from pathlib import Path
import zipfile

MAX_TEXT = 2_000_000


def extract(path, filename):
    from .document_sandbox import extract as isolated_extract
    return isolated_extract(path, filename, 'library')


def _extract_local(path, filename):
    suffix = Path(filename).suffix.casefold()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".wav", ".mp3", ".m4a", ".webm", ".ogg"}:
        return [{"text": "", "locator": {"file": filename}, "kind": "media",
                 "status": "empty"}]
    if suffix in {".xlsx", ".xlsm"}:
        from openpyxl import load_workbook
        from openpyxl.utils import get_column_letter
        with zipfile.ZipFile(path) as archive:
            if len(archive.infolist()) > 10000 or sum(x.file_size for x in archive.infolist()) > 100 * 1024**2:
                raise ValueError("Tableur décompressé trop volumineux")
        workbook = load_workbook(path, read_only=True, data_only=False, keep_links=False)
        result = []
        cells = 0
        try:
            for sheet in workbook:
                sheet.reset_dimensions()  # Ignore stale formatting-only worksheet dimensions.
                for row_number, row in enumerate(sheet.iter_rows(), start=1):
                    cells += sum(cell.value is not None for cell in row)
                    if cells > 200_000 or row_number > 200_000:
                        raise ValueError("Tableur trop volumineux")
                    values = [f"{cell.coordinate}={cell.value}" for cell in row if cell.value is not None]
                    if values:
                        result.append({"text": " | ".join(values), "kind": "sheet_row", "status": "extracted",
                                       "locator": {"sheet": sheet.title, "range": f"A{row_number}:{get_column_letter(len(row))}{row_number}"}})
        finally:
            workbook.close()
    elif suffix in {".pdf", ".docx", ".csv", ".txt", ".md"}:
        from backend.app.services.cdc_extraction import _extract_document_local
        pages = _extract_document_local(Path(path), filename)
        result = [{"text": p.text, "kind": "document_page", "status": "extracted" if p.text.strip() else "ocr_required",
                   "locator": {("physical_page" if suffix == ".pdf" else "document_part"): p.physical_page, "printed_page": p.printed_page if suffix == ".pdf" else None,
                               "visual_review_required": p.visual_review_required}} for p in pages]
    elif suffix in {".html", ".htm"}:
        from backend.app.services.project_note_html import html_plain_text
        result = [{"text": html_plain_text(Path(path).read_bytes()), "kind": "web_page", "status": "extracted",
                   "locator": {"file": filename}}]
    else:
        raise ValueError("Format non pris en charge")
    if sum(len(row["text"]) for row in result) > MAX_TEXT:
        raise ValueError("Texte extrait supérieur à 2 millions de caractères")
    return result
