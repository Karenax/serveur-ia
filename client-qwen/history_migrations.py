"""Keep valid encrypted histories when a reset marker is missing or outdated."""
import secrets
from pathlib import Path

import history_store


def migrate_cache(path, meta_path, reset_path, protect):
    path, meta_path, reset_path = map(Path, (path, meta_path, reset_path))
    reset = reset_path.read_text(encoding='utf-8') if reset_path.exists() else ''
    if reset == history_store.HISTORY_RESET_ID:
        return False
    quarantined = False
    if path.exists():
        try:
            history_store.read(path, protect)
        except history_store.HistoryError:
            # Keep the original protected bytes beside the cache. Never erase
            # existing unreadable archives or reuse a recovery file name.
            suffix = '.recovery-' + secrets.token_hex(8)
            for original in (path, meta_path):
                if original.exists():
                    target = original.with_name(original.stem + suffix + original.suffix)
                    original.rename(target)
            quarantined = True
    history_store.atomic(reset_path, history_store.HISTORY_RESET_ID.encode())
    return quarantined
