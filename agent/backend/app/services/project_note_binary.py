"""Pure binary type validation shared by live uploads and offline transports."""
from io import BytesIO
from pathlib import PurePosixPath
import warnings

from PIL import Image, UnidentifiedImageError

MAX_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 16_000_000
IMAGE_TYPES = {'.png': ('PNG', 'image/png'), '.jpg': ('JPEG', 'image/jpeg'),
               '.jpeg': ('JPEG', 'image/jpeg'), '.webp': ('WEBP', 'image/webp')}
DOWNLOAD_TYPES = {'.txt': 'text/plain', '.md': 'text/plain', '.pdf': 'application/pdf',
                  '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                  '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}


def image(data, expected_format):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as decoded:
                if (decoded.format != expected_format or decoded.width * decoded.height > MAX_PIXELS
                        or getattr(decoded, 'n_frames', 1) != 1):
                    raise ValueError('Image statique bornée requise')
                decoded.verify()
            with Image.open(BytesIO(data)) as decoded:
                decoded.load()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
            Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ValueError('Image PNG, JPEG ou WebP statique valide requise (16 millions de pixels maximum)') from exc


def content_type(filename, data):
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_BYTES:
        raise ValueError('Pièce binaire non vide de 5 Mio maximum requise')
    extension = PurePosixPath(filename).suffix.casefold()
    if extension in IMAGE_TYPES:
        image_format, mime = IMAGE_TYPES[extension]
        image(data, image_format)
        return mime
    return DOWNLOAD_TYPES.get(extension, 'application/octet-stream')
