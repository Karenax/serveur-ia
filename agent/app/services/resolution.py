"""Suggestions de classement ; la décision reste humaine."""
import re
import json


def proposal_details(value: str, project_id: str | None) -> dict:
    """Même explication dans la file historique et la recherche paginée."""
    try:
        payload = json.loads(value)
        candidates = payload.get("candidates", []) if isinstance(payload, dict) else []
    except (ValueError, TypeError):
        candidates = []
    candidates = [c for c in candidates if isinstance(c, dict)] if isinstance(candidates, list) else []
    suggested = next((c for c in candidates if c.get("project_id") == project_id), {})
    return {"candidates": candidates, "evidence": suggested.get("evidence", [])}


def _contains_reference(text: str, reference: str) -> bool:
    # Tirets/underscores servent aussi de séparateurs dans les objets métier
    # (PO-…-CODE-Votre colis, CODE_AFC). Un suffixe de sous-référence compact
    # ou numérique (-4, -AB, -4bis) reste attaché au code et interdit le préfixe.
    return bool(reference and re.search(
        r"(?<![^\W_])" + re.escape(reference)
        + r"(?![^\W_]|[-_](?:\d+[a-z0-9]*|[a-z]{1,2})(?![^\W_]))", text))


def candidate_rank(candidate: dict) -> tuple[int, float]:
    """Une référence déclarée prime sur les indices contextuels ou IA."""
    explicit = bool({"explicit_code", "explicit_alias"}.intersection(candidate.get("reasons", [])))
    return (2 if explicit and candidate.get("reference_location") == "subject" else int(explicit),
            candidate["score"])


def choose_candidate(candidates: list[dict], threshold: float = 0.75) -> dict | None:
    """Abstention si références contradictoires ou candidats contextuels proches."""
    if not candidates or candidates[0]["score"] < threshold:
        return None
    best = candidates[0]
    tier = candidate_rank(best)[0]
    peers = [c for c in candidates[1:] if candidate_rank(c)[0] == tier]
    if tier and peers:
        return None
    if not tier and peers and best["score"] - peers[0]["score"] < 0.12:
        return None
    evidence = best.get("evidence", [])
    network_keys = {"learned_sender", "learned_participants", "learned_domain", "project_contact", "project_team", "ai_hint", "sender_customer"}
    discriminating = any(e["key"] == "ai_hint" or e["key"] not in network_keys or (
        e["key"] in {"learned_sender", "learned_participants"}
        and not e.get("shared") and e.get("samples", 0) >= 3) for e in evidence)
    shared_sender = any(e.get("shared") and e["key"] in {"learned_sender", "project_contact", "project_team"} for e in evidence)
    if not tier and shared_sender and not discriminating:
        return None
    return best


def merge_ai_hints(result: dict, projects: list, hints: list) -> None:
    by_code = {(p.code or "").strip().upper(): p for p in projects}
    for hint in hints or []:
        project = by_code.get(str(hint).strip().upper())
        if not project:
            continue
        candidate = next((c for c in result["candidates"] if c["project_id"] == project.id), None)
        if candidate:
            if "ai_hint" not in candidate["reasons"]:
                candidate["reasons"].append("ai_hint")
            candidate["score"] = max(candidate["score"], 0.75)
            candidate.setdefault("evidence", []).append({"key": "ai_hint", "weight": 0.75,
                "label": "Le contenu correspond à ce projet selon l’analyse IA."})
        else:
            result["candidates"].append({"project_id": project.id, "code": project.code,
                                         "score": 0.75, "reasons": ["ai_hint"], "evidence": [{
                                             "key": "ai_hint", "weight": 0.75,
                                             "label": "Le contenu correspond à ce projet selon l’analyse IA."}]})
    result["candidates"].sort(key=candidate_rank, reverse=True)


def resolve_project(parsed: dict, projects: list, thread_project_id: str | None = None,
                    learning_context=None) -> dict:
    """Retourne {candidates:[{project_id, score, reasons}], auto:false}."""
    if learning_context:
        parsed = learning_context.prepare(parsed)
    text = f"{parsed.get('subject','')} {parsed.get('body_text','')}".lower()
    subject = (parsed.get("subject") or "").lower()
    cands: list[dict] = []
    # 1. Référence explicite [P26-0148] ou code projet
    for p in projects:
        reasons: list[str] = []
        evidence: list[dict] = []
        reference_location = None
        score = 0.0
        aliases = {a.strip().lower() for a in (p.aliases or []) if a.strip()}
        if _contains_reference(text, (p.code or "").strip().lower()):
            score += 0.9
            reasons.append("explicit_code")
            reference_location = "subject" if _contains_reference(subject, p.code.strip().lower()) else "body"
            evidence.append({"key": "explicit_code", "weight": 0.9,
                             "label": f"Référence {p.code} présente dans l’objet." if reference_location == "subject"
                             else f"Référence {p.code} présente dans le corps du mail."})
        for a in sorted(aliases):
            if _contains_reference(text, a):
                # Un alias alphanumérique est une référence métier déclarée,
                # pas un simple mot-clé ; ne jamais déduire un alias par similarité.
                is_reference = bool(re.search(r"[a-z]", a) and re.search(r"\d", a))
                score += 0.9 if is_reference else 0.4
                reason = "explicit_alias" if is_reference else "alias"
                if reason not in reasons:
                    reasons.append(reason)
                if is_reference:
                    location = "subject" if _contains_reference(subject, a) else "body"
                    if reference_location != "subject":
                        reference_location = location
                evidence.append({"key": reason, "weight": 0.9 if is_reference else 0.4,
                                 "label": f"Référence alternative déclarée : {a}." if is_reference
                                 else f"Alias du projet reconnu : {a}."})
        # expéditeur connu ?
        from .mail_learning import addresses
        if addresses(parsed.get("sender", "")) & addresses(p.customer_id or ""):
            score += 0.2
            reasons.append("sender_customer")
            evidence.append({"key": "sender_customer", "weight": 0.2,
                             "label": "L’adresse de l’expéditeur correspond au client déclaré."})
        if thread_project_id and thread_project_id == p.id:
            score += 0.5
            reasons.append("thread_history")
        if learning_context:
            learned = learning_context.evidence(parsed, p)
            # Team membership corroborates the same correspondents, without inflating their score.
            if any(e["key"] in {"learned_sender", "learned_participants", "project_contact"} for e in learned):
                for item in learned:
                    if item["key"] == "project_team":
                        item["weight"] = 0.0
            # Un contact déjà appris ne compte pas deux fois comme expéditeur.
            sender_evidence = [e for e in learned if e["key"] in {"learned_sender", "project_contact"}]
            if len(sender_evidence) > 1:
                strongest = max(sender_evidence, key=lambda e: e["weight"])
                learned = [e for e in learned if e not in sender_evidence or e is strongest]
            evidence.extend(learned)
            reasons.extend(e["key"] for e in learned)
            score += sum(e["weight"] for e in learned)
        if reasons:
            cap = 1.0 if reference_location else 0.89
            cands.append({"project_id": p.id, "code": p.code, "score": round(min(score, cap), 3),
                          "reasons": reasons, "evidence": evidence, "reference_location": reference_location})
    cands.sort(key=candidate_rank, reverse=True)
    auto = False
    return {"candidates": cands, "auto": auto}
