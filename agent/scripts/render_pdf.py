"""Render one PDF page for document OCR, without SDK, network or database."""
import argparse
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
from uuid import uuid4


def file_hash(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(1024 * 1024):
            result.update(block)
    return result.hexdigest()


def io_path(path):
    # Windows CRT file opening can still enforce MAX_PATH in a venv executable.
    if os.name == 'nt' and not str(path).startswith('\\\\?\\'):
        return Path('\\\\?\\UNC\\'+str(path)[2:] if str(path).startswith('\\\\') else '\\\\?\\'+str(path))
    return path


def main():
    import pypdfium2 as pdfium
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--storage', type=Path, required=True)
    parser.add_argument('--page', type=int, required=True)
    args = parser.parse_args()
    root, original, output = args.storage.resolve(), args.input.resolve(), args.output.resolve()
    if not original.is_relative_to(root) or not output.is_relative_to(root) or original == output:
        raise ValueError('PDF et rendu doivent rester dans le stockage autorisé')
    original, output = io_path(original), io_path(output)
    if version('pypdfium2') != '5.14.0' or version('Pillow') != '13.0.0':
        raise ValueError('Dépendances PDF différentes du profil de rendu')
    source_hash = file_hash(original)
    with pdfium.PdfDocument(original) as document:
        if not 1 <= args.page <= len(document):
            raise ValueError('Page physique PDF invalide')
        page = document[args.page-1]
        try:
            width, height = page.get_size()
            if width <= 0 or height <= 0:
                raise ValueError('Dimensions PDF invalides')
            # Bound the rendered image, not page count.
            bitmap = page.render(scale=2048/max(width, height))
            try:
                with bitmap.to_pil() as native_image:
                    image = native_image.convert('RGB')
                try:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    temporary = output.with_name(output.name+'.'+uuid4().hex+'.part')
                    image.save(temporary, format='PNG')
                    temporary.replace(output)
                    dimensions = list(image.size)
                finally:
                    image.close()
            finally:
                bitmap.close()
        finally:
            page.close()
    if file_hash(original) != source_hash:
        raise ValueError('PDF modifié pendant le rendu')
    print(json.dumps({'physical_page':args.page,'source_sha256':source_hash,'dimensions':dimensions}))


if __name__ == '__main__':
    main()
