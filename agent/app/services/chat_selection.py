"""Bounded, relevant context with one turn per project before filling slots."""
import math
from collections import defaultdict

from .memory_port import search_words


def select_context(hits, query, limit=8):
    words = search_words(query)

    def score(hit):
        text = " ".join(str(hit.get(key) or "") for key in ("subject", "value", "text", "excerpt"))
        overlap = len(words & search_words(text)) / max(1, len(words))
        try:
            semantic = float(hit.get("score") or 0)
        except (ValueError, TypeError):
            semantic = 0
        return overlap + (max(0, min(1, semantic)) if math.isfinite(semantic) else 0)

    buckets = defaultdict(list)
    seen = set()
    for hit in hits:
        identity = (hit["project_code"], hit.get("id"), hit.get("source_id"),
                    hit.get("value"), hit.get("text"), hit.get("excerpt"))
        if identity in seen:
            continue
        seen.add(identity)
        buckets[hit["project_code"]].append(hit)
    for bucket in buckets.values():
        bucket.sort(key=score, reverse=True)
    selected = []
    while buckets and len(selected) < limit:
        projects = sorted(buckets, key=lambda code: (-score(buckets[code][0]), code))
        for code in projects:
            if len(selected) == limit:
                break
            selected.append(buckets[code].pop(0))
            if not buckets[code]:
                del buckets[code]
    return selected
