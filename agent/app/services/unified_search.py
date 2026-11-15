"""Read-only hybrid search over current canonical sources and the existing EG2 index."""
import asyncio
import json
import math
import re
import sqlite3
import unicodedata
from contextlib import closing
from datetime import datetime, time, timedelta
from functools import lru_cache

from sqlalchemy.orm import selectinload

from ..models import KnowledgeItem, Project, ProvenanceLink, Source
from .eg2_memory import EG2MemoryAdapter, evidence_ref, split_passages
from .project_access import filter_brain, require_brain
from .settings_service import get_section
from .memory_port import search_words
from .current_evidence import is_current_evidence


def fold(text):
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(c))


@lru_cache(maxsize=128)
def query_terms(query):
    phrase = fold(query.strip())
    words = search_words(query)
    # Keep invoice/project identifiers whole; the embedding cannot preserve them exactly.
    refs = [ref for ref in re.findall(r"\b[\w]+(?:[-_/][\w]+)+\b", phrase) if re.search(r"\d", ref)]
    patterns = [re.compile(r"(?<!\w)" + re.escape(ref) + r"(?!\w)") for ref in refs]
    return words, re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)"), patterns


def lexical(query, text):
    normalized = fold(text)
    words, phrase, refs = query_terms(query)
    exact = bool(phrase.search(normalized))
    reference = any(ref.search(normalized) for ref in refs)
    overlap = len(words & set(re.findall(r"\w+", normalized))) / max(1, len(words))
    return (2.0 if exact or reference else 0.0) + overlap, exact or reference


def excerpt(text, query, size=700):
    # Preserve original offsets even when accent/case normalization expands a character.
    normalized, positions = [], []
    for offset, character in enumerate(text):
        part = fold(character)
        normalized.append(part)
        positions.extend([offset] * len(part))
    words, phrase, refs = query_terms(query)
    patterns = [phrase, *refs, *(re.compile(re.escape(word)) for word in sorted(words, key=len, reverse=True))]
    folded = "".join(normalized)
    match = next((m for pattern in patterns if (m := pattern.search(folded))), None)
    start = max(0, positions[match.start()] - 120) if match and match.start() < len(positions) else 0
    return ("…" if start else "") + text[start:start + size] + ("…" if len(text) > start + size else "")


def date_filter(query, column, after, before):
    if after:
        query = query.filter(column >= datetime.combine(after, time.min))
    if before:
        query = query.filter(column < datetime.combine(before + timedelta(days=1), time.min))
    return query


def read_index(adapter, projects, source_ids=None):
    """Never create, migrate or rewrite the index while searching."""
    rows = []
    if source_ids is not None and not source_ids:
        return rows
    with closing(sqlite3.connect(adapter.path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)) as index:
        column = 'project' if source_ids is None else 'source'
        ids = list(projects if source_ids is None else source_ids)
        for start in range(0, len(ids), 400):
            batch = ids[start:start + 400]
            matches = index.execute("SELECT project,ref,source,ordinal,text,vector,profile FROM passages "
                                    f"WHERE {column} IN (" + ",".join("?" for _ in batch) + ")", batch)
            rows.extend(row for row in matches if row[0] in projects)
    return rows


async def search(db, *, query, project_id=None, source_type="all", after=None, before=None, offset=0, limit=25,
                 adapter=None, source_ids=None):
    projects_query = filter_brain(db.query(Project), Project.id)
    if project_id:
        require_brain(project_id)
        projects_query = projects_query.filter(Project.id == project_id)
    projects = {p.id: {"code": p.code, "name": p.name} for p in projects_query}
    if project_id and not projects:
        from fastapi import HTTPException
        raise HTTPException(404, "Projet de connaissance introuvable")
    empty = {"items": [], "total": 0, "offset": offset, "limit": limit, "has_next": False,
             "engine": "eg2", "semantic_status": "not_needed", "warnings": [],
             "sources": 0, "indexed_sources": 0}
    if not projects:
        return empty
    adapter = adapter or EG2MemoryAdapter(config=get_section(db, "memory"), ai_config=get_section(db, "ai"))
    warnings = []
    rows, vector = [], None
    status = "not_needed"
    if source_type != "knowledge":
        try:
            rows = await asyncio.to_thread(read_index, adapter, projects, source_ids)
            incompatible = any(r[6] != adapter.channel.profile for r in rows)
            rows = [r for r in rows if r[6] == adapter.channel.profile]
            if incompatible:
                warnings.append("Des passages utilisent un autre profil EG2 et doivent être réindexés.")
            if rows:
                vector = (await adapter.channel.embed([query], query=True))[0]
                status = "ok"
            else:
                status = "empty"
        except Exception:
            status = "unavailable"
            warnings.append("EG2 indisponible : seuls les mots et références exacts sont recherchés.")

    # Keep the API event loop responsive while scanning the local corpus.
    return await asyncio.to_thread(rank_current, db, query, projects, adapter, rows, vector, status, warnings,
                                   empty, source_type, after, before, offset, limit, source_ids)


def rank_current(db, query, projects, adapter, rows, vector, status, warnings, empty,
                 source_type, after, before, offset, limit, source_ids=None):

    # Read canonical state after the network await, so a replaced/discarded source is never recalled.
    db.expire_all()
    sources_query = db.query(Source).options(selectinload(Source.artifacts)).filter(
        Source.project_id.in_(projects), Source.status == "resolved")
    if source_type not in {"all", "knowledge"}:
        sources_query = sources_query.filter(Source.source_type == source_type)
    if source_ids is not None:
        sources_query = sources_query.filter(Source.id.in_(source_ids))
    sources_query = date_filter(sources_query, Source.received_at, after, before)
    sources = {s.id: s for s in sources_query if is_current_evidence(s)} if source_type != "knowledge" else {}
    contents = {sid: "\n".join(a.content_text or "" for a in s.artifacts
                               if a.kind not in {"audio_pending", "attachment_status"} and not (a.content_json or {}).get("superseded"))
                for sid, s in sources.items()}
    refs = {sid: evidence_ref(s.project_id, sid, contents[sid], adapter.channel.profile)
            for sid, s in sources.items()}
    indexed = set()
    semantic = {}
    invalid_vectors = False
    for pid, ref, sid, ordinal, text, raw_vector, profile in rows:
        if sid not in sources or pid != sources[sid].project_id or ref != refs[sid]:
            continue
        indexed.add(sid)
        if vector is None:
            continue
        try:
            values = json.loads(raw_vector)
            if not isinstance(values, list) or len(values) != len(vector) or "true" in raw_vector or "false" in raw_vector:
                raise ValueError("Invalid vector")
            # sumprod validates numeric types and computes in C; a Python loop over 12M floats stalls searches.
            score = math.sumprod(vector, values)
            if not math.isfinite(score):
                raise ValueError("Invalid score")
            if sid not in semantic or score > semantic[sid][0]:
                semantic[sid] = (score, text, ordinal)
        except (ValueError, TypeError, OverflowError):
            invalid_vectors = True
    if invalid_vectors:
        warnings.append("Des vecteurs EG2 invalides ont été ignorés ; réindexation nécessaire.")
    unindexed = sum(bool(contents[sid].strip()) and sid not in indexed for sid in sources)
    if unindexed:
        warnings.append(f"{unindexed} source(s) avec du texte ne sont pas encore indexées dans ce profil EG2.")

    # Bound purely semantic candidates relative to the best match, instead of returning the whole corpus.
    semantic_floor = max(0.25, max((hit[0] for hit in semantic.values()), default=0) - 0.12)
    semantic_candidates = {sid for sid, hit in sorted(semantic.items(), key=lambda pair: (-pair[1][0], pair[0]))[:100]
                           if hit[0] >= semantic_floor}
    explicit_reference = bool(query_terms(query)[2])
    items = []
    for sid, source in sources.items():
        metadata = source.source_metadata or {}
        title = str(metadata.get("subject") or metadata.get("filename") or source.source_type)
        header = " ".join([title, source.author or ""])
        # Choose the lexical passage independently of EG2 to retain exact references in long documents.
        passages = split_passages(contents[sid]) or [""]
        text = max(passages, key=lambda part: lexical(query, part)[0])
        lex, exact = lexical(query, header + "\n" + text)
        project_lex, project_exact = lexical(query, projects[source.project_id]["code"])
        # An assigned project is a useful filter, but a reference actually in the document ranks first.
        project_match = bool(project_lex)
        if project_match:
            lex += 0.35
        sem, sem_text, ordinal = semantic.get(sid, (0, "", None))
        # Similarity is a ranking signal, never a probability. Conservative noise floor, to qualify on real queries.
        relevant_semantic = sid in semantic_candidates
        if explicit_reference and not (exact or project_exact):
            continue
        if not lex and not relevant_semantic:
            continue
        methods = (["exact"] if exact else ["keywords"] if lex > (0.35 if project_match else 0) else [])
        methods += (["project"] if project_match else []) + (["semantic"] if relevant_semantic else [])
        if not lex:
            text = sem_text
        artifacts = [a for a in source.artifacts if a.content_text and a.kind != "audio_pending"
                     and not (a.content_json or {}).get("superseded")]
        artifact = next((a for a in artifacts if text and text in a.content_text), None)
        artifact = artifact or (max(artifacts, key=lambda a: lexical(query, a.content_text)[0]) if artifacts else None)
        locator = {**(artifact.content_json or {}), "artifact_id": artifact.id} if artifact else {}
        for private_key in ("content", "source_metadata", "provenance"):
            locator.pop(private_key, None)
        locator.update(note_id=metadata.get("note_id"), note_version_id=metadata.get("note_version_id"),
                       erp_project_id=metadata.get("erp_project_id"))
        items.append({"id": sid, "kind": "source", "source_id": sid, "source_type": source.source_type,
                      "project_id": source.project_id, "project_code": projects[source.project_id]["code"],
                      "title": title, "author": source.author, "date": source.received_at.isoformat(),
                      "excerpt": excerpt(text, query), "methods": methods, "score": lex + max(0, sem),
                      "semantic_score": sem if relevant_semantic else None,
                      "passage": ordinal if not lex else None, "level": "evidence", "locator": locator})

    if source_ids is None and source_type in {"all", "knowledge"}:
        facts = date_filter(db.query(KnowledgeItem).filter(KnowledgeItem.project_id.in_(projects),
                            KnowledgeItem.status == "validated"), KnowledgeItem.created_at, after, before).all()
        from .knowledge_context import contexts, usable_as_current
        qualifications = contexts(db, facts)
        links = {}
        for link, linked_project in db.query(ProvenanceLink, Source.project_id).join(Source, Source.id == ProvenanceLink.source_id).filter(
                Source.project_id.in_(projects), Source.status == "resolved").order_by(ProvenanceLink.id):
            links.setdefault((link.knowledge_item_id, linked_project), link.source_id)
        for fact in facts:
            context = qualifications[fact.id]
            if not usable_as_current(fact, context):
                continue
            lex, exact = lexical(query, fact.subject + "\n" + fact.value)
            if not lex or explicit_reference and not exact:
                continue
            items.append({"id": fact.id, "kind": "knowledge", "source_id": links.get((fact.id, fact.project_id)),
                          "source_type": "knowledge", "project_id": fact.project_id,
                          "project_code": projects[fact.project_id]["code"], "title": fact.subject,
                          "author": None, "date": fact.created_at.isoformat(), "excerpt": excerpt(fact.value, query),
                          "methods": ["exact" if exact else "keywords"], "score": lex, "semantic_score": None,
                          "passage": None, "context": context,
                          "level": "default" if fact.validated_by == "auto-default" else "validated"})
    items.sort(key=lambda item: (-item["score"], item["project_code"], item["id"]))
    return {**empty, "items": items[offset:offset + limit], "total": len(items),
            "has_next": offset + limit < len(items), "semantic_status": status, "warnings": warnings,
            "sources": len(sources), "indexed_sources": len(indexed)}
