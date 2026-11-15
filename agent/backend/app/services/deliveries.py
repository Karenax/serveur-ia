"""Immutable BE deliverables and the exact technical snapshot used to generate them."""
import hashlib
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from threading import RLock

from sqlalchemy import func

from ..db import APP_DIR
from ..models import DeliveryVersion, CdcEvidenceAnchor, CdcSource

_lock = RLock()


def _transfer_markdown(project, items, snapshot, draft):
    sources = {source["id"]: source for source in snapshot["sources"]}
    evidence = defaultdict(list)
    for anchor in snapshot["evidence"]:
        evidence[anchor["item_id"]].append(anchor)

    lines = [f"# Transfert BE — {project.code} {project.title}".strip(), "",
             "## 1. Demande transmise au BE", ""]
    for item in items:
        lines += [f"### [{item.kind}] {item.title}",
                  f"- Exigence : {item.normalized_wording or item.title}"]
        if evidence[item.id]:
            for anchor in evidence[item.id]:
                source = sources[anchor["source_id"]]
                revision = f", révision {source['revision']}" if source["revision"] else ""
                lines.append(f"- Preuve CDC — {source['filename']}{revision}, page {anchor['page']} — « {anchor['quote']} »")
        else:
            lines.append(f"- Preuve CDC : « {item.source_quote} » (page {item.physical_page})")
        lines += [f"- Modalité : {item.modality} | Priorité : {item.priority} | Confiance : {item.confidence}", ""]

    lines += ["## 2. Réponse technique du BE", "",
              "> À compléter : faisabilité, charge de travail et réserves techniques.", "",
              "## 3. Revue et arbitrage", "", "> À compléter : décisions, arbitrages, jalons.", ""]
    if draft:
        lines.insert(0, "# BROUILLON — revue non finalisée\n")
    return "\n".join(lines)


def save_version(db, project, items, checks, draft):
    project_id = project.id
    with _lock:
        number = (db.query(func.max(DeliveryVersion.version)).filter_by(project_id=project_id, kind="transfer-be").scalar() or 0) + 1
        identity = str(uuid.uuid4())
        directory = APP_DIR / "exports" / project_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"transfert-be-v{number:04d}-{'brouillon' if draft else 'final'}-{identity}.md"
        stamp = datetime.now(timezone.utc)
        anchors = db.query(CdcEvidenceAnchor).join(CdcSource, CdcEvidenceAnchor.source_id == CdcSource.id).filter(
            CdcSource.project_id == project_id, CdcEvidenceAnchor.item_id.in_([i.id for i in items])).order_by(
            CdcSource.filename, CdcSource.revision, CdcEvidenceAnchor.physical_page, CdcEvidenceAnchor.id).all()
        sources = db.query(CdcSource).filter(CdcSource.id.in_([a.source_id for a in anchors])).all()
        snapshot = {"items": [{"id": i.id, "title": i.title, "wording": i.normalized_wording,
                               "quote": i.source_quote, "page": i.physical_page, "status": i.knowledge_status,
                               "hours": i.estimated_hours, "kind": i.kind, "modality": i.modality,
                               "priority": i.priority, "confidence": i.confidence, "criterion": i.criterion,
                               "unit": i.unit, "acceptance_criterion": i.acceptance_criterion,
                               "responsible_party": i.responsible_party} for i in items],
                    "evidence": [{"item_id": a.item_id, "source_id": a.source_id, "page": a.physical_page,
                                  "quote": a.quote, "locator": a.locator} for a in anchors],
                    "sources": [{"id": s.id, "filename": s.filename, "revision": s.revision, "sha256": s.sha256} for s in sources],
                    "checks": checks}
        content = f"<!-- Version {number} · {stamp.isoformat()} -->\n\n" + _transfer_markdown(project, items, snapshot, draft)
        data = content.encode("utf-8")
        digest = hashlib.sha256(data).hexdigest()
        stream = path.open("xb")
        try:
            with stream:
                stream.write(data)
            db.add(DeliveryVersion(id=identity, project_id=project_id, kind="transfer-be", version=number,
                                   draft=draft, path=str(path), snapshot=snapshot, sha256=digest, created_at=stamp))
            db.commit()
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return {"file": str(path), "version": number, "version_id": identity, "sha256": digest, "markdown": content}
