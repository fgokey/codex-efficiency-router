"""Distribution regression: documented optional sources must survive packaging."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from release_package import source_payload


class SourceClosureTests(unittest.TestCase):
    def fixture(self, root):
        for name in ('VERSION', 'LICENSE', 'README.md', 'README.zh-CN.md', 'CHANGELOG.md',
                     'AGENTS.md', 'CONTRIBUTING.md', 'SECURITY.md', 'SUPPORT.md',
                     'CODE_OF_CONDUCT.md', '.editorconfig', '.gitattributes', '.gitignore',
                     'plugin.json', 'install.sh', 'install.ps1', 'uninstall.sh',
                     'uninstall.ps1', 'cer.ps1'):
            (root / name).write_bytes(b'fixture\n')
        (root / 'host').mkdir()
        (root / 'docs').mkdir()
        (root / 'docs/INSTALL.md').write_text(
            '[host patch](../host/required-agent-admission.patch)\n', encoding='utf-8')
        patch = root / 'host/required-agent-admission.patch'
        patch.write_bytes(b'diff --git a/example b/example\n')
        return patch

    def test_documented_patch_is_packaged_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            patch = self.fixture(root)
            payload = source_payload(root)
            self.assertEqual(payload['host/required-agent-admission.patch'], patch.read_bytes())

    def test_host_checkout_and_private_files_are_not_swept_into_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.fixture(root)
            for name in ('auth.json', 'unreviewed.patch', 'codex.exe', 'private.md'):
                (root / 'host' / name).write_bytes(b'not for distribution')
            payload = source_payload(root)
            self.assertEqual([n for n in payload if n.startswith('host/')],
                             ['host/required-agent-admission.patch'])

    def test_missing_documented_patch_fails_before_build(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.fixture(root).unlink()
            with self.assertRaisesRegex(ValueError, 'documented host patch is missing'):
                source_payload(root)

    def test_no_patch_requirement_without_documented_dependency(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.fixture(root).unlink()
            (root / 'docs/INSTALL.md').write_text('Native installation.\n', encoding='utf-8')
            self.assertNotIn('host/required-agent-admission.patch', source_payload(root))

    def test_patch_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            patch = self.fixture(root)
            original = patch.read_bytes()
            patch.unlink()
            target = root / 'outside.patch'
            target.write_bytes(original)
            try:
                patch.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest('symlink unavailable without platform privilege')
            with self.assertRaisesRegex(ValueError, 'refuses symlinks'):
                source_payload(root)


if __name__ == '__main__':
    unittest.main()
