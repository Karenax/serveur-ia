"""Bounded local logs for windowless Windows launches."""
import logging
import re
from logging.handlers import RotatingFileHandler

from app.config import STORAGE_DIR


class RedactingFormatter(logging.Formatter):
    """Redact secrets in both log messages and formatted exception tracebacks."""
    def __init__(self, formatter):
        self.delegate = formatter if isinstance(formatter, logging.Formatter) else None
        super().__init__(None if self.delegate else formatter)

    def format(self, record):
        value = self.delegate.format(record) if self.delegate else super().format(record)
        value = re.sub(r'(?i)\bBearer\s+[^\s\'"<>,;]+', 'Bearer [masqué]', value)
        value = re.sub(r'dpapi:[A-Za-z0-9+/=]+', 'dpapi:[masqué]', value)
        return re.sub(r'''(?ix)(\b(?:api_key|access_token|refresh_token|password|client_secret)\b["']?\s*[:=]\s*)(?:"[^"]*"|'[^']*'|[^\s"'&,}\]]+)''',
                      r'\1[masqué]', value)


def configure_logging():
    path = STORAGE_DIR / "logs" / "agent.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if any(isinstance(h, RotatingFileHandler) and h.baseFilename == str(path.resolve()) for h in root.handlers):
        return
    handler = RotatingFileHandler(path, maxBytes=5 * 1024**2, backupCount=3, encoding="utf-8")
    handler.setFormatter(RedactingFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root.addHandler(handler)
    for name in ("uvicorn", "uvicorn.access"):
        logging.getLogger(name).addHandler(handler)
    # Windowless launches persist Uvicorn's console streams too. Preserve their
    # formatting while applying the same redaction before stdout/stderr writes.
    for logger in (root, *(logging.getLogger(name) for name in ("uvicorn", "uvicorn.error", "uvicorn.access"))):
        for existing in logger.handlers:
            if not isinstance(existing.formatter, RedactingFormatter):
                existing.setFormatter(RedactingFormatter(existing.formatter or logging.Formatter()))
