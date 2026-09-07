import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import install as installer  # noqa: E402
from doctor import validate_tree  # noqa: E402


class InstallerTests(unittest.TestCase):
    def test_user_install_copies_only_managed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            codex_home = Path(tmp) / "codex"
            home.mkdir()
            codex_home.mkdir()

            unrelated = codex_home / "agents" / "my-existing-agent.toml"
            unrelated.parent.mkdir(parents=True)
            unrelated.write_text('name = "existing"\n', encoding="utf-8")

            with patch.dict(os.environ, {"HOME": str(home), "CODEX_HOME": str(codex_home)}, clear=False):
                with patch.object(Path, "home", return_value=home):
                    self.assertEqual(installer.install("user", None, False), 0)

            skill = home / ".agents" / "skills" / installer.PROJECT / "SKILL.md"
            self.assertTrue(skill.exists())
            self.assertTrue(unrelated.exists(), "installer must preserve unrelated custom agents")

            errors = validate_tree(skill, codex_home / "agents")
            self.assertEqual(errors, [])

    def test_project_dry_run_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(installer.install("project", root, True), 0)
            self.assertFalse((root / ".agents").exists())
            self.assertFalse((root / ".codex").exists())


if __name__ == "__main__":
    unittest.main()
