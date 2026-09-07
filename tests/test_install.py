import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import manage
import install as installer
from package import MANIFEST, PROJECT, resolve_targets
from doctor import validate_tree


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name).resolve() / "project with spaces"
        self.project.mkdir()
        self.skill, self.agents, self.backups = resolve_targets("project", self.project)
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def install(self, **kwargs):
        return manage.install(ROOT, "project", self.project, **kwargs)

    def snapshot(self):
        paths = [p for directory in (self.skill, self.agents) if directory.exists()
                 for p in directory.rglob("*") if p.is_file()]
        return {str(p): p.read_bytes() for p in paths}

    def backup_list(self):
        return sorted(p for p in self.backups.iterdir() if p.is_dir())

    def legacy(self):
        fixture = ROOT / "tests/fixtures/v01"
        shutil.copytree(fixture / "skill", self.skill)
        shutil.copytree(fixture / "agents", self.agents)

    def source_copy(self):
        dst = Path(self.temp.name) / "source"
        shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        return dst

    def test_user_install_copies_only_managed_files(self):
        home = Path(self.temp.name).resolve() / "home"
        home.mkdir()
        codex = home / "custom codex"
        unrelated = codex / "agents/my-existing-agent.toml"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text('name = "existing"\n', encoding="utf-8")
        config = codex / "config.toml"
        config.write_bytes(b'# preserve exactly\r\nmodel = "custom"\r\n')
        with patch.object(Path, "home", return_value=home), patch.dict(os.environ, {"CODEX_HOME": str(codex)}):
            self.assertEqual(installer.install("user", None, False), 0)
            self.assertEqual(validate_tree(home / ".agents/skills" / PROJECT / "SKILL.md", codex / "agents"), [])
        self.assertEqual(config.read_bytes(), b'# preserve exactly\r\nmodel = "custom"\r\n')
        self.assertEqual(unrelated.read_text(), 'name = "existing"\n')

    def test_project_dry_run_changes_nothing(self):
        self.assertEqual(self.install(dry_run=True), 0)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_reinstall_is_idempotent(self):
        self.install()
        before, backups = self.snapshot(), self.backup_list()
        self.install()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.backup_list(), backups)

    def test_unowned_collision_is_not_overwritten_even_with_force(self):
        self.agents.mkdir(parents=True)
        p = self.agents / "terra-executor.toml"
        p.write_text("unrelated user file", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.install(force=True)
        self.assertEqual(p.read_text(), "unrelated user file")
        self.assertFalse((self.skill / "SKILL.md").exists())

    def test_modified_owned_file_blocks_update_without_partial_writes(self):
        self.install()
        p = self.agents / "terra-executor.toml"
        p.write_text("user customized", encoding="utf-8")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.install()
        self.assertEqual(self.snapshot(), before)

    def test_force_update_backs_up_customization(self):
        self.install()
        p = self.agents / "terra-executor.toml"
        p.write_text("user customized", encoding="utf-8")
        self.install(force=True)
        self.assertEqual((self.backup_list()[-1] / "files/agents/terra-executor.toml").read_text(), "user customized")

    def test_uninstall_preserves_untracked_files_directories_and_config(self):
        self.install()
        extra = self.skill / "my-notes.txt"
        extra.write_text("keep", encoding="utf-8")
        empty = self.skill / "user-empty-dir"
        empty.mkdir()
        unrelated = self.agents / "unrelated.toml"
        unrelated.write_text("keep", encoding="utf-8")
        config = self.project / ".codex/config.toml"
        config.write_text("# keep", encoding="utf-8")
        self.assertEqual(manage.uninstall("project", self.project), 0)
        self.assertFalse((self.skill / "SKILL.md").exists())
        self.assertTrue(extra.exists() and empty.is_dir() and unrelated.exists() and config.exists())
        self.assertTrue(self.backups.is_dir())

    def test_modified_owned_file_blocks_uninstall(self):
        self.install()
        (self.skill / "SKILL.md").write_text("local edit", encoding="utf-8")
        before = self.snapshot()
        with self.assertRaises(ValueError):
            manage.uninstall("project", self.project)
        self.assertEqual(self.snapshot(), before)

    def test_force_uninstall_retains_recoverable_backup(self):
        self.install()
        (self.skill / "SKILL.md").write_text("local edit", encoding="utf-8")
        manage.uninstall("project", self.project, force=True)
        self.assertEqual((self.backup_list()[-1] / "files/skill/SKILL.md").read_text(), "local edit")

    def test_uninstall_dry_run_changes_nothing(self):
        self.install()
        before, backups = self.snapshot(), self.backup_list()
        manage.uninstall("project", self.project, dry_run=True)
        self.assertEqual((self.snapshot(), self.backup_list()), (before, backups))

    def test_no_manifest_refuses_legacy_deletion(self):
        self.legacy()
        before = self.snapshot()
        with self.assertRaises(ValueError):
            manage.uninstall("project", self.project)
        self.assertEqual(before, self.snapshot())

    def test_explicit_legacy_adoption_then_uninstall(self):
        self.legacy()
        self.install(adopt_v01=True)
        self.assertTrue((self.skill / MANIFEST).is_file())
        self.assertEqual(validate_tree(self.skill / "SKILL.md", self.agents), [])
        manage.uninstall("project", self.project)
        self.assertFalse(self.skill.exists())

    def test_modified_legacy_is_not_adopted(self):
        self.legacy()
        (self.skill / "SKILL.md").write_text("not v0.1", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.install(adopt_v01=True, force=True)

    def test_crlf_legacy_can_be_adopted(self):
        self.legacy()
        for p in list(self.skill.rglob("*.md")) + list(self.agents.glob("*.toml")):
            p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
        self.install(adopt_v01=True)
        self.assertTrue((self.skill / MANIFEST).exists())

    def test_manifest_path_traversal_rejected(self):
        self.install()
        p = self.skill / MANIFEST
        manifest = json.loads(p.read_text())
        manifest["files"]["skill/../../victim.txt"] = "0" * 64
        p.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(ValueError):
            manage.uninstall("project", self.project, force=True)

    def test_managed_symlink_rejected(self):
        self.install()
        file = self.agents / "terra-executor.toml"
        victim = self.project / "victim.txt"
        victim.write_text("preserve", encoding="utf-8")
        file.unlink()
        try:
            file.symlink_to(victim)
        except OSError:
            self.skipTest("symlink privilege unavailable on this runner")
        with self.assertRaises(ValueError):
            self.install(force=True)
        self.assertEqual(victim.read_text(), "preserve")

    def test_mid_write_failure_restores_original_bytes(self):
        original = manage.os.replace
        calls = 0
        def fail_once(src, dst):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected write failure")
            return original(src, dst)
        with patch.object(manage.os, "replace", side_effect=fail_once), self.assertRaises(OSError):
            self.install()
        self.assertEqual(self.snapshot(), {})
        self.assertTrue((self.backup_list()[-1] / "backup.json").is_file())

    def test_restore_uninstall_backup(self):
        self.install()
        before = self.snapshot()
        manage.uninstall("project", self.project)
        manage.restore(self.backup_list()[-1], "project", self.project)
        self.assertEqual(self.snapshot(), before)

    def test_restore_refuses_newer_changes(self):
        self.install()
        manage.uninstall("project", self.project)
        backup = self.backup_list()[-1]
        self.agents.mkdir(parents=True, exist_ok=True)
        (self.agents / "terra-executor.toml").write_text("newer change", encoding="utf-8")
        with self.assertRaises(ValueError):
            manage.restore(backup, "project", self.project)

    def test_restore_refuses_different_target(self):
        self.install()
        other = self.project / "other"
        other.mkdir()
        with self.assertRaises(ValueError):
            manage.restore(self.backup_list()[-1], "project", other)

    def test_corrupt_backup_rejected_before_writes(self):
        self.install()
        manage.uninstall("project", self.project)
        backup = self.backup_list()[-1]
        (backup / "files/skill/SKILL.md").write_text("corrupt", encoding="utf-8")
        with self.assertRaises(ValueError):
            manage.restore(backup, "project", self.project)
        self.assertEqual(self.snapshot(), {})

    def test_source_reference_missing_fails_before_install(self):
        source = self.source_copy()
        (source / "skills" / PROJECT / "references/dispatch.md").unlink()
        with self.assertRaises(ValueError):
            manage.install(source, "project", self.project)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_scope_mismatch_refused(self):
        with self.assertRaises(ValueError):
            resolve_targets("user", self.project)

    def test_lock_contention_refused(self):
        self.backups.mkdir(parents=True)
        (self.backups / ".lock").write_text("active", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.install()
        self.assertFalse((self.skill / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
