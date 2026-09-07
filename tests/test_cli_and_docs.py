import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import manage
from package import PROJECT, MANIFEST, resolve_targets


class CliAndDocsTests(unittest.TestCase):
    def run_cli(self, script, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args],
                              cwd=ROOT, text=True, encoding="utf-8", capture_output=True, timeout=20)

    def test_full_project_cli_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            flags = ("--scope", "project", "--project-root", str(project))
            before = list(project.iterdir())
            result = self.run_cli("install.py", *flags, "--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(project.iterdir()), before)
            result = self.run_cli("install.py", *flags)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.run_cli("doctor.py", *flags)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("STATIC PASS", result.stdout)
            self.assertIn("NOT VERIFIED", result.stdout)
            skill = project / ".agents/skills" / PROJECT
            (skill / "references/routing.md").write_text("customized", encoding="utf-8")
            self.assertEqual(self.run_cli("doctor.py", *flags).returncode, 1)
            self.assertEqual(self.run_cli("uninstall.py", *flags).returncode, 2)
            self.assertEqual(self.run_cli("uninstall.py", *flags, "--force").returncode, 0)
            self.assertFalse((skill / MANIFEST).exists())

    def test_malformed_manifest_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            skill, agents, _ = resolve_targets("project", root)
            skill.mkdir(parents=True)
            (skill / MANIFEST).write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                manage.load_manifest(skill, agents)

    def test_malformed_backup_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            backup = root / "backup"
            backup.mkdir()
            (backup / "backup.json").write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                manage.restore(backup, "project", root, dry_run=True)

    def test_documentation_relative_targets_exist(self):
        documents = list(ROOT.glob("*.md")) + list((ROOT / "docs").glob("*.md"))
        documents += list((ROOT / "skills").rglob("*.md"))
        errors = []
        for document in documents:
            for url in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                if "://" in url or url.startswith(("#", "mailto:")):
                    continue
                target = document.parent / url.split("#")[0]
                if not target.exists():
                    errors.append(f"{document.relative_to(ROOT)} -> {url}")
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
