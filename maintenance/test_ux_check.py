"""Behavioral tests for the advisory scanner, using isolated frontend fixtures."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("ux_check", Path(__file__).with_name("ux_check.py"))
ux = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ux)


class UXCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = copy.deepcopy(json.loads(ux.DEFAULT_CONFIG.read_text(encoding="utf-8")))
        self.config["roots"] = ["ui"]
        self.config["technicalExempt"] = ["ui/admin/**"]

    def write(self, name, source):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        return path

    def report(self):
        return ux.run(self.root, config=self.config)

    def test_visible_text_and_lines_without_logs_or_comments(self):
        self.write("ui/app.js", '// toast("backend error");\nconsole.log("backend error");\nconst payload = "backend error";\nnode.textContent = "backend error";\n')
        warnings = self.report()["warnings"]
        self.assertEqual(len(warnings), 1)
        self.assertEqual((warnings[0]["line"], warnings[0]["rule"]), (4, "TECHNICAL-TEXT"))

    def test_accessible_controls_and_diagnostic_section(self):
        self.write("ui/page.html", '<label for="name">Nom</label><input id="name">\n<button aria-label="Fermer"><svg></svg></button>\n<section id="diagnostic"><p>backend HTTP 500</p></section>\n<label>Nom<input></label>\n<input placeholder="Nom"><img src="x"><button></button>')
        warnings = self.report()["warnings"]
        self.assertEqual({w["rule"] for w in warnings}, {"A11Y-LABEL", "A11Y-IMG", "A11Y-BUTTON"})
        self.assertTrue(all(w["line"] == 5 for w in warnings))

    def test_exclusions_and_admin_accessibility_still_checked(self):
        self.write("ui/tests/fixture.html", '<p>backend</p><img>')
        self.write("ui/vendor/library.html", '<img>')
        self.write("ui/admin/page.html", '<p>backend</p><img>')
        report = self.report()
        self.assertEqual(report["files"], ["ui/admin/page.html"])
        self.assertEqual([w["rule"] for w in report["warnings"]], ["A11Y-IMG"])

    def test_generated_html_and_local_suppression(self):
        self.write("ui/app.js", 'node.innerHTML = `<input placeholder="Nom">`;\n// ux-ignore: écran de diagnostic prévu\nstatus.textContent = "backend";\nother.textContent = "backend";')
        report = self.report()
        self.assertEqual([(w["line"], w["rule"]) for w in report["warnings"]], [(1, "A11Y-LABEL"), (4, "TECHNICAL-TEXT")])
        self.assertEqual(report["suppressed"], 1)

    def test_long_text_terminology_and_no_mutation(self):
        source = '<button>Save</button><p>' + 'Message métier utile. ' * 15 + '</p>'
        path = self.write("ui/page.html", source)
        report = self.report()
        self.assertEqual({w["rule"] for w in report["warnings"]}, {"TERMINOLOGY", "LONG-TEXT"})
        self.assertTrue(report["advisory"])
        self.assertEqual(path.read_text(encoding="utf-8"), source)

    def test_duplicate_component_candidate(self):
        source = '<dialog id="confirm"><p>' + 'Confirmer cette opération. ' * 16 + '</p><button>Annuler</button></dialog>'
        self.write("ui/a.html", source)
        self.write("ui/b.html", source)
        warnings = self.report()["warnings"]
        duplicates = [w for w in warnings if w["rule"] == "DUPLICATE-TEMPLATE"]
        self.assertEqual(len(duplicates), 1)
        self.assertIn('ui/a.html:1', duplicates[0]["message"])

    def test_inline_script_location_and_utf16(self):
        self.write("ui/page.html", '<h1>Projets</h1>\n<script>\nstatus.textContent = "backend";\n</script>')
        path = self.write("ui/windows.html", '')
        path.write_text('<img src="x">', encoding="utf-16")
        report = self.report()
        self.assertEqual([(w["file"], w["line"], w["rule"]) for w in report["warnings"]], [
            ("ui/page.html", 3, "TECHNICAL-TEXT"), ("ui/windows.html", 1, "A11Y-IMG")])

    def test_changed_mode_includes_staged_and_untracked_ignores_generated(self):
        import subprocess
        def git(*args):
            subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)
        git('init')
        self.write('.gitignore', 'ui/generated/\n')
        self.write('ui/staged.html', '<button></button>')
        git('add', '.gitignore', 'ui/staged.html')
        self.write('ui/new.html', '<img>')
        self.write('ui/generated/asset.html', '<img>')
        report = ux.run(self.root, changed=True, config=self.config)
        self.assertEqual(report["files"], ['ui/new.html', 'ui/staged.html'])
        self.assertEqual({w["rule"] for w in report["warnings"]}, {'A11Y-IMG', 'A11Y-BUTTON'})


if __name__ == "__main__":
    unittest.main()
