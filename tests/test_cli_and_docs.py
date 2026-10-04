import json
import os
import re
import shutil
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

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell 7 unavailable")
    def test_installed_powershell_reader_and_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            flags = ("--scope", "project", "--project-root", str(project))
            self.assertEqual(self.run_cli("install.py", *flags, "--dry-run").returncode, 0)
            self.assertEqual(list(project.iterdir()), [])
            self.assertEqual(self.run_cli("install.py", *flags).returncode, 0)
            skill, agents, backups = resolve_targets("project", project)
            manifest = json.loads((skill / MANIFEST).read_text(encoding="utf-8"))
            for key in ("skill/cer.ps1", "skill/scripts/readonly_reader.py"):
                self.assertIn(key, manifest["files"])
            self.assertEqual((skill / "scripts/readonly_reader.py").read_bytes(),
                             (ROOT / "hooks/readonly_reader.py").read_bytes())
            source = project / "source.txt"
            expected = ('汉🙂"\\' * 1200) + '\r\n' + ('x' * 4500)
            source.write_bytes(expected.encode("utf-8"))
            original = (source.read_bytes(), source.stat().st_mtime_ns)
            env = dict(os.environ, CER_PYTHON=sys.executable, PYTHONIOENCODING="ascii")
            def read(*args):
                result = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-File",
                                         str(skill / "cer.ps1"), "read", *args], env=env,
                                        capture_output=True, timeout=20)
                self.assertLessEqual(len(result.stdout) + len(result.stderr), 4096)
                return result
            common = ("--root", str(project), "--path", "source.txt")
            (project / "small.txt").write_text("small 汉🙂", encoding="utf-8")
            first = read("page", "--root", str(project), "--path", "small.txt")
            self.assertEqual(first.returncode, 0, first.stderr.decode("utf-8", "replace"))
            self.assertEqual(json.loads(first.stdout)["data"], "small 汉🙂")
            self.assertIsNone(json.loads(first.stdout)["next_cursor"])
            index = read("index", *common)
            self.assertEqual(index.returncode, 0, index.stderr.decode("utf-8", "replace"))
            cursor = json.loads(index.stdout)["cursor"]
            parts = []
            for _ in range(20):
                page = read("page", *common, "--cursor", cursor)
                self.assertEqual(page.returncode, 0, page.stderr.decode("utf-8", "replace"))
                data = json.loads(page.stdout)
                parts.append(data["data"])
                cursor = data["next_cursor"]
                if cursor is None:
                    break
            else:
                self.fail("installed reader did not terminate")
            self.assertEqual("".join(parts), expected)
            self.assertEqual((source.read_bytes(), source.stat().st_mtime_ns), original)
            excerpt = read("excerpt", *common, "--start", "2", "--lines", "1")
            self.assertEqual(excerpt.returncode, 0, excerpt.stderr.decode("utf-8", "replace"))
            excerpt_page = json.loads(excerpt.stdout)
            excerpt_parts = [excerpt_page["data"]]
            while excerpt_page["next_cursor"] is not None:
                excerpt = read("page", *common, "--cursor", excerpt_page["next_cursor"])
                self.assertEqual(excerpt.returncode, 0, excerpt.stderr.decode("utf-8", "replace"))
                excerpt_page = json.loads(excerpt.stdout)
                excerpt_parts.append(excerpt_page["data"])
            self.assertEqual("".join(excerpt_parts), "x" * 4500)
            help_result = read("--help")
            self.assertEqual(help_result.returncode, 0, help_result.stderr.decode("utf-8", "replace"))
            self.assertIn(b"locate", help_result.stdout)
            self.assertIn(b"json", help_result.stdout)
            (project / 'large.json').write_text('{"array":[1,{"nested":2}]}',encoding='utf-8')
            projected=read('json','--root',str(project),'--path','large.json',
                           '--pointer','/array','--mode','members')
            self.assertEqual(projected.returncode,0,projected.stderr.decode('utf-8','replace'))
            self.assertLessEqual(len(projected.stdout)+len(projected.stderr),4096)
            self.assertEqual([item['type'] for item in json.loads(projected.stdout)['members']],
                             ['number','object'])
            invalid=read('json','--root',str(project),'--path','large.json','--pointer','#/array')
            self.assertEqual(invalid.returncode,2);self.assertEqual(invalid.stdout,b'')
            if shutil.which("rg"):
                located = read("locate", "--root", str(project), "--path", "source.txt",
                               "--query", "汉")
                self.assertEqual(located.returncode, 0, located.stderr.decode("utf-8", "replace"))
                self.assertEqual(json.loads(located.stdout)["candidates"],
                                 [{"path": "source.txt", "line": 1}])
            blocked = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-File",
                                      str(skill / "cer.ps1"), "install", *flags], env=env,
                                     capture_output=True, timeout=20)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn(b'read only', blocked.stderr)
            self.assertEqual(self.run_cli("doctor.py", *flags).returncode, 0)
            self.assertEqual(self.run_cli("uninstall.py", *flags).returncode, 0)
            self.assertFalse((skill / "cer.ps1").exists())
            manage.restore(sorted(p for p in backups.iterdir() if p.is_dir())[-1], "project", project)
            self.assertEqual(self.run_cli("doctor.py", *flags).returncode, 0)

    def test_malformed_manifest_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            skill, agents, _ = resolve_targets("project", root)
            skill.mkdir(parents=True)
            (skill / MANIFEST).write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                manage.load_manifest(skill, agents)

    def test_doctor_detects_missing_or_changed_installed_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp).resolve()
            flags = ("--scope", "project", "--project-root", str(project))
            self.assertEqual(self.run_cli("install.py", *flags).returncode, 0)
            skill, _, _ = resolve_targets("project", project)
            for path in (skill / "cer.ps1", skill / "scripts/readonly_reader.py"):
                original = path.read_bytes()
                path.unlink()
                self.assertEqual(self.run_cli("doctor.py", *flags).returncode, 1)
                path.write_bytes(original + b'\n# local edit\n')
                self.assertEqual(self.run_cli("doctor.py", *flags).returncode, 1)
                path.write_bytes(original)
            self.assertEqual(self.run_cli("doctor.py", *flags).returncode, 0)

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
