"""Profils de classement recalculés depuis les décisions humaines courantes."""
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from email.utils import getaddresses
from email.parser import BytesHeaderParser
from pathlib import Path
import html
import re
import unicodedata

from sqlalchemy.orm import Session

from ..models import Contact, KnowledgeItem, Source, SourceArtifact

STOP_WORDS = set("""avec pour dans vous nous votre notre cette sont plus tout tous bien
bonjour merci cordialement bonne journee suivant suite objet message mail email
from sent subject original telephone mobile adresse envoyer envoi piece jointe
please thanks regards best hello dear reply forward attachment attached meeting
have this that with from your will http https www com excent projet project
livraison commande demande prix facture devis achat achat purchase order client
information fourniture fournir livraison recipient expediteur destinataire
confidential confidentiel signature monsieur madame""".split())
PUBLIC_DOMAINS = {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "orange.fr", "free.fr"}


def addresses(values) -> set[str]:
    if isinstance(values, str):
        values = [values]
    return {address.strip().casefold() for _, address in getaddresses(values or [])
            if "@" in address}


def normalized(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", value.casefold())
                   if not unicodedata.combining(c))


def authored_text(value: str) -> str:
    value = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<blockquote\b[^>]*>.*?</blockquote>", " ", value, flags=re.I | re.S)
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    lines = []
    for line in value.splitlines():
        if line.strip() == "--":
            break
        if re.match(r"\s*(?:le .+ecrit\s*:|on .+wrote\s*:|-{2,}\s*(?:original|message)|de\s*:|from\s*:)", normalized(line)):
            break
        if not line.lstrip().startswith(">"):
            lines.append(line)
    return "\n".join(lines)[:6000]


def terms(value: str) -> set[str]:
    value = re.sub(r"\S+@\S+|https?://\S+", " ", value)
    value = value.replace("_", " ")
    return {word for word in re.findall(r"\b[a-z]{4,}\b", normalized(authored_text(value)))
            if word not in STOP_WORDS}


def subject_key(subject: str) -> str:
    value = normalized(subject)
    value = re.sub(r"^(?:(?:re|fw|fwd|tr)\s*:\s*)+", "", value)
    return " ".join(value.split())


def message_ids(value) -> set[str]:
    if isinstance(value, list):
        value = " ".join(str(x) for x in value)
    return set(re.findall(r"<[^<>\s]+>", str(value or "")))


def reply_headers(meta: dict, original_uri: str) -> dict:
    """Les anciens imports peuvent retrouver leurs en-têtes dans l’original."""
    result = {key: meta.get(key, "") for key in ("in_reply_to", "references")}
    if all(key in meta for key in result):
        return result
    try:
        header_lines = []
        size = 0
        with Path(original_uri).open("rb") as source:
            while size < 256 * 1024:
                line = source.readline(256 * 1024 - size)
                if not line or line in (b"\r\n", b"\n"):
                    break
                header_lines.append(line)
                size += len(line)
        header = BytesHeaderParser().parsebytes(b"".join(header_lines))
        for key, name in (("in_reply_to", "In-Reply-To"), ("references", "References")):
            if key not in meta:
                result[key] = str(header.get(name, "") or "")
    except (OSError, ValueError):
        pass
    return result


@dataclass
class LearningContext:
    samples: Counter = field(default_factory=Counter)
    senders: dict = field(default_factory=lambda: defaultdict(Counter))
    participants: dict = field(default_factory=lambda: defaultdict(Counter))
    domains: dict = field(default_factory=lambda: defaultdict(Counter))
    subjects: dict = field(default_factory=lambda: defaultdict(Counter))
    threads: dict = field(default_factory=lambda: defaultdict(set))
    vocabulary: dict = field(default_factory=lambda: defaultdict(Counter))
    contacts: dict = field(default_factory=lambda: defaultdict(set))
    teams: dict = field(default_factory=lambda: defaultdict(set))
    _keyword_cache: dict = field(default_factory=dict)

    @staticmethod
    def affinity(index, key, project_id):
        counts = index.get(key, {})
        n = counts.get(project_id, 0)
        return n, n / sum(counts.values()) if n else 0.0

    def keywords(self, project_id: str) -> list[str]:
        if project_id in self._keyword_cache:
            return self._keyword_cache[project_id]
        ranked = []
        for word, count in self.vocabulary.get(project_id, {}).items():
            total = sum(words.get(word, 0) for words in self.vocabulary.values())
            if count / total >= 0.65:
                ranked.append((count / total, min(count, 5), word))
        self._keyword_cache[project_id] = [word for _, _, word in sorted(ranked, reverse=True)[:30]]
        return self._keyword_cache[project_id]

    def describe(self, project_id: str) -> dict:
        senders = [address for address in self.senders
                   if self.affinity(self.senders, address, project_id)[1] >= 0.7]
        return {"validated_mail_count": self.samples[project_id],
                "known_senders": sorted(senders)[:15], "keywords": self.keywords(project_id)[:15]}

    def prepare(self, parsed: dict) -> dict:
        return {**parsed, "_sender_addresses": addresses(parsed.get("sender", "")),
                "_participant_addresses": addresses(parsed.get("participants") or parsed.get("to", []) + parsed.get("cc", [])),
                "_message_terms": terms(parsed.get("subject", "") + "\n" + parsed.get("body_text", "")),
                "_attachment_terms": terms(" ".join(a.get("filename", "") for a in parsed.get("attachments", [])))}

    def evidence(self, parsed: dict, project) -> list[dict]:
        pid = project.id
        sender = parsed["_sender_addresses"]
        people = parsed["_participant_addresses"]
        evidence = []

        def add(key, weight, label, samples=0, shared=False):
            evidence.append({"key": key, "weight": round(weight, 3), "label": label,
                             "samples": samples, "shared": shared})

        sender_matches = [(self.affinity(self.senders, address, pid), address) for address in sender]
        if sender_matches:
            (n, share), address = max(sender_matches)
            if n:
                weight = (0.42 if n == 1 else 0.62 if n == 2 else 0.8) * share
                shared = len(self.senders[address]) > 1
                if shared:
                    weight = min(weight, 0.5)
                add("learned_sender", weight,
                    f"Expéditeur {address} : {n} mail(s) validé(s) dans ce projet, {share:.0%} de son historique."
                    + (" Ce contact intervient aussi sur d’autres projets." if shared else ""), n, shared)
        if sender & self.contacts.get(pid, set()):
            shared = any(sender & emails for other, emails in self.contacts.items() if other != pid)
            add("project_contact", 0.35 if shared else 0.55,
                "L’expéditeur est un contact déclaré de ce projet.", shared=shared)
        recipient_matches = []
        team_matches = (sender | people) & self.teams.get(pid, set())
        if team_matches:
            shared = any(team_matches & emails for other, emails in self.teams.items() if other != pid)
            add("project_team", 0.12 if shared else 0.35,
                "Correspondant membre de l’équipe projet : " + ", ".join(sorted(team_matches))
                + (" ; intervient aussi sur d’autres projets." if shared else "."), shared=shared)
        for address in people:
            n, share = self.affinity(self.participants, address, pid)
            weight = 0.25 * min(1, n / 3) * share
            if len(self.participants.get(address, {})) > 1:
                weight = min(weight, 0.12)
            recipient_matches.append((weight, n, share, address))
        if recipient_matches:
            weight, n, share, address = max(recipient_matches)
            if n:
                add("learned_participants", weight,
                    f"Destinataire {address} : {n} échange(s) validé(s) dans ce projet.", n,
                    len(self.participants[address]) > 1)
        # Le domaine n’est pas compté une deuxième fois si l’expéditeur est connu.
        if not any(e["key"] in {"learned_sender", "project_contact"} for e in evidence):
            domains = {a.rsplit("@", 1)[1] for a in sender} - PUBLIC_DOMAINS
            matches = [(self.affinity(self.domains, domain, pid), domain) for domain in domains]
            if matches:
                (n, share), domain = max(matches)
                if n:
                    add("learned_domain", 0.12 * min(1, n / 3) * share,
                        f"Domaine {domain} déjà présent dans les échanges du projet.", n)
        refs = message_ids(parsed.get("in_reply_to")) | message_ids(parsed.get("references"))
        thread_projects = set().union(*(self.threads.get(ref, set()) for ref in refs)) if refs else set()
        if pid in thread_projects:
            add("learned_thread", 0.88 / len(thread_projects), "Réponse à un mail déjà classé dans ce projet.")
        key = subject_key(parsed.get("subject", ""))
        n, share = self.affinity(self.subjects, key, pid)
        if n and len(terms(key)) >= 2:
            add("learned_subject", 0.4 * share, f"Objet déjà rencontré dans {n} mail(s) validé(s).", n)
        message_terms = parsed["_message_terms"]
        attachment_terms = parsed["_attachment_terms"]
        keywords = set(self.keywords(pid))
        matched = sorted(message_terms & keywords)
        if len(matched) >= 2:
            n = self.samples[pid]
            add("learned_vocabulary", min(0.38, 0.095 * len(matched)) * (1 if n >= 2 else 0.6),
                "Vocabulaire du projet : " + ", ".join(matched[:6]) + ".", n)
        matched = sorted(attachment_terms & keywords)
        if matched:
            add("attachment_vocabulary", min(0.18, 0.06 * len(matched)),
                "Pièce jointe liée aux thèmes du projet : " + ", ".join(matched[:5]) + ".")
        title_terms = terms(getattr(project, "name", "") or "")
        matched = sorted(message_terms & title_terms)
        if len(matched) >= 2:
            add("project_title", min(0.3, 0.1 * len(matched)),
                "Mots du nom du projet : " + ", ".join(matched[:5]) + ".")
        return evidence


def build_learning_context(db: Session, projects: list, *, exclude_source_id: str | None = None) -> LearningContext:
    """Aucune suggestion non validée ne nourrit le profil. Pas de cache durable."""
    context = LearningContext()
    project_ids = {p.id for p in projects if p.code.upper() != "DIVERS"}
    if not project_ids:
        return context
    history = db.query(Source).filter(Source.status == "resolved", Source.source_type == "email",
                                      Source.project_id.in_(project_ids))
    if exclude_source_id:
        history = history.filter(Source.id != exclude_source_id)
    sources = history.all()
    bodies = defaultdict(list)
    # Jointure plutôt qu’un IN de tous les IDs (limite SQLite pour gros historiques).
    artifacts = db.query(SourceArtifact).join(Source).filter(
        Source.status == "resolved", Source.source_type == "email", Source.project_id.in_(project_ids),
        SourceArtifact.kind == "body_text")
    if exclude_source_id:
        artifacts = artifacts.filter(Source.id != exclude_source_id)
    for artifact in artifacts:
        bodies[artifact.source_id].append(artifact.content_text or "")
    seen_messages = set()
    for source in sources:
        pid = source.project_id
        meta = source.source_metadata or {}
        identity = (pid, tuple(sorted(message_ids(meta.get("message_id")))) or source.sha256)
        if identity in seen_messages:
            continue
        seen_messages.add(identity)
        context.samples[pid] += 1
        sender = addresses(source.author or "")
        for address in sender:
            context.senders[address][pid] += 1
        for address in addresses(source.participants):
            context.participants[address][pid] += 1
        for domain in {a.rsplit("@", 1)[1] for a in sender}:
            context.domains[domain][pid] += 1
        key = subject_key(meta.get("subject", ""))
        if key:
            context.subjects[key][pid] += 1
        for ref in message_ids(meta.get("message_id")):
            context.threads[ref].add(pid)
        text = meta.get("subject", "") + "\n" + "\n".join(bodies[source.id])
        text += "\n" + " ".join(a.get("filename", "") for a in meta.get("attachments", []))
        context.vocabulary[pid].update(terms(text))
    for item in db.query(KnowledgeItem).filter(KnowledgeItem.status == "validated", KnowledgeItem.project_id.in_(project_ids)):
        context.vocabulary[item.project_id].update(terms(item.subject + "\n" + item.value))
    for contact in db.query(Contact):
        for pid in (contact.roles or {}):
            if pid in project_ids:
                context.contacts[pid].update(addresses(contact.emails))
    from .mail_team import team_emails
    for pid, email in team_emails(project_ids):
        context.teams[pid].update(addresses(email))
    return context
