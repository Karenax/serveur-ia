"""Advisory UI checks. Standard library only; never rewrites application sources."""
from __future__ import annotations

import argparse
import fnmatch
from html import unescape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "maintenance/ux-ui/ux-check.json"
TECHNICAL = re.compile(r"\b(?:HTTP\s*[45]\d\d|SYNC_[A-Z_]+|stack\s*trace|backend|undefined|null|NaN|exception|traceback)\b", re.I)
TOKENS = re.compile(r"//[^\n]*|/\*[\s\S]*?\*/|'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|`(?:\\.|[^`\\])*`", re.S)
VISIBLE_SINK = re.compile(r"(?:\.(?:textContent|innerText|innerHTML|outerHTML|placeholder|title|ariaLabel)\s*=\s*|\b(?:alert|confirm|toast|notify|showToast|showError|setText|setTitle|setHint)\s*\(\s*|\.setAttribute\(\s*['\"](?:aria-label|title|placeholder)['\"]\s*,\s*)$", re.I)
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def matches(name, patterns):
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


class Check:
    def __init__(self, root, config):
        self.root, self.config = Path(root), config
        self.findings, self.templates, self.suppressed = [], {}, 0
        self.lines = {}

    def warn(self, name, line, rule, message):
        lines = self.lines.get(name, [])
        nearby = "\n".join(lines[max(0, line - 2):line])
        # A suppression must explain itself; only the same/next line is suppressed.
        if re.search(r"ux-ignore\s*:\s*\S.{3,}", nearby):
            self.suppressed += 1
            return
        item = {"file": name, "line": line, "rule": rule, "message": message}
        if item not in self.findings:
            self.findings.append(item)

    def text(self, name, line, value, technical=False):
        value = " ".join(unescape(value).split())
        if not value or re.fullmatch(r"[\W\d_]+|__[A-Z_]+__", value):
            return
        sample = value[:100]
        if not technical and not matches(name, self.config["technicalExempt"]) and TECHNICAL.search(value):
            self.warn(name, line, "TECHNICAL-TEXT", f"Texte technique potentiellement visible : {sample}")
        if len(value) > self.config["longText"]:
            self.warn(name, line, "LONG-TEXT", f"Texte de {len(value)} caractères à relire : {sample}")
        for term, preferred in self.config["terminology"].items():
            if value.casefold() == term.casefold():
                self.warn(name, line, "TERMINOLOGY", f"Vérifier « {value} » ; terme de référence : « {preferred} »")

    def markup(self, name, value, offset=0):
        parser = UIParser(self, name, offset)
        parser.feed(value)
        parser.finish()
        for block in re.finditer(r"<(form|dialog|section)\b[^>]*>[\s\S]*?</\1>", value, re.I):
            normal = " ".join(block.group().split())
            if len(normal) < 350:
                continue
            location = (name, offset + value[:block.start()].count("\n") + 1)
            prior = self.templates.get(normal)
            if prior and prior[0] != name:
                self.warn(*location, "DUPLICATE-TEMPLATE", f"Bloc identique à {prior[0]}:{prior[1]} ; vérifier une mutualisation")
            else:
                self.templates[normal] = location

    def scan(self, path):
        name = path.relative_to(self.root).as_posix()
        raw = path.read_bytes()
        try:
            source = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
        except UnicodeError:
            self.warn(name, 1, "SOURCE-ENCODING", "Encodage inconnu ; fichier non analysé")
            return
        self.lines[name] = source.splitlines()
        if path.suffix == ".html":
            self.markup(name, source)
            for script in re.finditer(r"<script\b[^>]*>([\s\S]*?)</script>", source, re.I):
                self.javascript(name, script[1], source[:script.start(1)].count("\n"))
        elif path.suffix in {".js", ".cjs", ".mjs", ".ts", ".tsx", ".jsx", ".java", ".kt"}:
            self.javascript(name, source)
        elif path.suffix == ".xml":
            for match in re.finditer(r'android:(?:text|hint|contentDescription)="([^"@][^"]*)"|<string\b[^>]*>([^<]*)</string>', source):
                self.text(name, source[:match.start()].count("\n") + 1, match[1] or match[2])
        if path.suffix == ".css":
            clean = re.sub(r"/\*[\s\S]*?\*/", lambda m: "\n" * m.group().count("\n"), source)
            for match in re.finditer(r"transition\s*:\s*all\b", clean):
                self.warn(name, clean[:match.start()].count("\n") + 1, "MOTION", "transition: all ; préciser les propriétés et vérifier reduced-motion")

    def javascript(self, name, source, offset=0):
        for token in TOKENS.finditer(source):
            value = token.group()
            if value.startswith(("//", "/*")):
                continue
            context = source[max(0, token.start() - 180):token.start()]
            if not VISIBLE_SINK.search(context):
                continue
            line = offset + source[:token.start()].count("\n") + 1
            value = value[1:-1].replace("\\n", "\n").replace("\\'", "'").replace('\\"', '"')
            value = re.sub(r"\$\{[^{}]*\}", "", value)
            statement = re.split(r"[;\n]", context)[-1]
            technical = bool(re.search(r"(?:getElementById|querySelector)\(\s*['\"][^'\"]*(?:admin|diagnostic|debug|local-api)[^'\"]*['\"]\s*\)", statement, re.I))
            if re.search(r"<[a-z][^>]*>", value, re.I):
                self.markup(name, value, line - 1)
            else:
                self.text(name, line, value, technical)


class UIParser(HTMLParser):
    def __init__(self, check, name, offset):
        super().__init__(convert_charrefs=True)
        self.check, self.name, self.line_offset = check, name, offset
        self.stack, self.inputs, self.buttons, self.labels = [], [], [], set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        line = self.line_offset + self.getpos()[0]
        section = " ".join(attrs.get(key, "") or "" for key in ("id", "class", "data-view"))
        technical = any(n[2] for n in self.stack) or any(
            re.search(r"(?:^|[\s_-])" + re.escape(term) + r"(?:$|[\s_-])", section, re.I)
            for term in self.check.config["technicalSections"])
        hidden = any(n[3] for n in self.stack) or "hidden" in attrs or attrs.get("aria-hidden") == "true"
        node = [tag, attrs, technical, hidden, line, "", []]
        for parent in self.stack:
            parent[6].append(node)
        if tag == "label" and attrs.get("for"):
            self.labels.add(attrs["for"])
        if tag == "input" and attrs.get("type", "text") not in {"hidden", "submit", "button", "reset", "image"}:
            self.inputs.append((node, any(n[0] == "label" for n in self.stack)))
        if tag in {"select", "textarea"}:
            self.inputs.append((node, any(n[0] == "label" for n in self.stack)))
        if tag == "button":
            self.buttons.append(node)
        if not hidden:
            if tag == "img" and "alt" not in attrs and attrs.get("role") not in {"presentation", "none"} and not attrs.get("aria-label"):
                self.check.warn(self.name, line, "A11Y-IMG", "Image sans alternative ; vérifier alt ou rôle décoratif")
            if tag in {"div", "span"} and any(key in attrs for key in ("onclick", "onClick")) and not (attrs.get("role") in {"button", "link"} and "tabindex" in attrs):
                self.check.warn(self.name, line, "A11Y-CLICK", "Élément cliquable non natif ; vérifier clavier, rôle et focus")
            if tag == "meta" and attrs.get("name") == "viewport" and re.search(r"user-scalable\s*=\s*no|maximum-scale\s*=\s*1(?:\D|$)", attrs.get("content", "")):
                self.check.warn(self.name, line, "A11Y-ZOOM", "Restriction du zoom à vérifier")
            for key in ("title", "placeholder", "aria-label", "alt"):
                if attrs.get(key):
                    self.check.text(self.name, line, attrs[key], technical)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if any(n[0] in {"script", "style", "pre", "code"} or n[3] for n in self.stack):
            return
        for node in self.stack:
            node[5] += data
        self.check.text(self.name, self.line_offset + self.getpos()[0], data, any(n[2] for n in self.stack))

    def finish(self):
        for node, wrapped in self.inputs:
            tag, attrs, _, hidden, line, _, _ = node
            if not hidden and not (wrapped or attrs.get("aria-label") or attrs.get("aria-labelledby") or attrs.get("id") in self.labels):
                self.check.warn(self.name, line, "A11Y-LABEL", f"{tag} sans label statique associé ; vérifier le nom calculé dans le navigateur")
        for tag, attrs, _, hidden, line, text, children in self.buttons:
            named_child = any(c[1].get("alt") or c[1].get("aria-label") or c[0] == "title" for c in children)
            if not hidden and not (text.strip() or attrs.get("aria-label") or attrs.get("aria-labelledby") or attrs.get("title") or named_child):
                self.check.warn(self.name, line, "A11Y-BUTTON", "Bouton sans nom statique ; vérifier le nom accessible calculé")


def run(root=ROOT, paths=None, changed=False, config=None):
    root = Path(root).resolve()
    config = config or json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    check = Check(root, config)
    if changed:
        names = set()
        for args in (["diff", "--name-only", "-z"], ["diff", "--cached", "--name-only", "-z"], ["ls-files", "--others", "--exclude-standard", "-z"]):
            result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True)
            names.update(result.stdout.decode("utf-8").split("\0"))
        files = [root / name for name in names if name]
    else:
        files = []
        entries = paths or config["roots"]
        for entry in entries:
            path = (root / entry).resolve()
            if not path.is_relative_to(root):
                raise ValueError(f"Chemin hors projet : {entry}")
        listed = subprocess.run(["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", *entries], capture_output=True)
        if listed.returncode == 0:
            files = [root / name for name in listed.stdout.decode("utf-8").split("\0") if name]
        else:
            for entry in entries:
                path = root / entry
                if path.is_file():
                    files.append(path)
                elif path.is_dir():
                    for parent, dirs, names in os.walk(path):
                        dirs[:] = [d for d in dirs if not matches((Path(parent, d).relative_to(root).as_posix() + "/"), config["exclude"])]
                        files.extend(Path(parent, n) for n in names)
    scanned = []
    for path in sorted(set(files)):
        if not path.is_file() or not path.resolve().is_relative_to(root):
            continue
        name = path.relative_to(root).as_posix()
        if not any(name == r or name.startswith(r.rstrip("/") + "/") for r in config["roots"]):
            continue
        if matches(name, config["exclude"]) or path.suffix not in {".html", ".js", ".cjs", ".mjs", ".css", ".ts", ".tsx", ".jsx", ".xml", ".java", ".kt"}:
            continue
        check.scan(path)
        scanned.append(name)
    return {"advisory": True, "files": scanned, "warnings": check.findings, "suppressed": check.suppressed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Chemins frontend relatifs au projet")
    parser.add_argument("--changed", action="store_true", help="Modifications Git locales, index et nouveaux fichiers")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    if args.changed and args.paths:
        parser.error("Choisir --changed ou des chemins explicites")
    report = run(paths=args.paths, changed=args.changed, config=json.loads(args.config.read_text(encoding="utf-8-sig")))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report["warnings"]:
            print(f'{item["file"]}:{item["line"]}: warning {item["rule"]}: {item["message"]}')
        print(f'UX : {len(report["files"])} fichiers, {len(report["warnings"])} avertissements, {report["suppressed"]} exclusions locales. Revue humaine requise ; aucune suppression automatique.')
    return 0  # Suspicions never fail tests or builds. Operational errors still fail.


if __name__ == "__main__":
    raise SystemExit(main())
