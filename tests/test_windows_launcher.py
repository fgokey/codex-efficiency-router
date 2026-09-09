"""Launcher behavior, isolated from user configuration; Windows CI runs native PS.

Fake old runtimes test selection, not Python 3.10 compatibility. A separate CI job
also exercises an actual 3.10 default and an explicit real 3.12 override.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PWSH = shutil.which('pwsh')


class LauncherPackagingTests(unittest.TestCase):
    def test_launcher_is_in_source_distribution(self):
        sys.path.insert(0, str(ROOT / 'scripts'))
        from release_package import source_payload
        self.assertIn('cer.ps1', source_payload())

    def test_windows_readmes_use_checked_launcher(self):
        for name in ('README.md', 'README.zh-CN.md'):
            text = (ROOT / name).read_text(encoding='utf-8')
            blocks = re.findall(r'```powershell\n(.*?)```', text, re.S)
            self.assertTrue(blocks)
            self.assertFalse(any(re.search(r'\bpy -3 scripts/', b) for b in blocks))
            self.assertIn('CER_PYTHON', text)
            self.assertIn('policy-only', text)


@unittest.skipUnless(os.name == 'nt' and PWSH, 'native Windows PowerShell launcher tests')
class WindowsLauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.project = self.root / "project with space and O'Brien"
        self.project.mkdir()
        self.env = dict(os.environ, CER_PYTHON=sys.executable)

    def invoke(self, *args, env=None, entry='cer.ps1', host=PWSH):
        return subprocess.run([host, '-NoProfile', '-NonInteractive', '-File', str(ROOT / entry), *args],
                              env=env or self.env, capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=30)

    def fake_old(self, path):
        path.write_text('@echo off\necho ' + json.dumps({'executable': sys.executable, 'version': [3, 10, 99]}) + '\nexit /b 0\n')
        return path

    def test_valid_override_and_clean_json_stdout(self):
        p = self.invoke('doctor', '--source-tree', str(ROOT), '--json')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)['policy'], 'PASS')
        self.assertIn('CER Python', p.stderr)

    def test_dry_run_preserves_project_and_forwards_spaces(self):
        p = self.invoke('install', '--scope', 'project', '--project-root', str(self.project), '--dry-run')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_missing_explicit_override_does_not_fall_back(self):
        env = dict(self.env, CER_PYTHON=str(self.root / 'missing.exe'))
        p = self.invoke('install', '--scope', 'project', '--project-root', str(self.project), env=env)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('CER_PYTHON', p.stderr)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_old_explicit_override_does_not_fall_back(self):
        env = dict(self.env, CER_PYTHON=str(self.fake_old(self.root / 'old.cmd')))
        p = self.invoke('install', '--scope', 'project', '--project-root', str(self.project), env=env)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('3.11+', p.stderr)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_old_path_default_can_use_py_listed_runtime(self):
        fakebin = self.root / 'fakebin'; fakebin.mkdir()
        self.fake_old(fakebin / 'python.cmd')
        self.fake_old(fakebin / 'python3.cmd')
        # A version-selecting py invocation would fail; discovery must only list.
        (fakebin / 'py.cmd').write_text('@echo off\nif not "%~1"=="-0p" exit /b 9\necho  -V:3.12 * ' + sys.executable + '\nexit /b 0\n')
        env = dict(self.env, CER_PYTHON='', PATH=str(fakebin))
        p = self.invoke('guard', 'status', '--scope', 'project', '--project-root', str(self.project), '--json', env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)['registration'], 'ABSENT')
        self.assertEqual(list(self.project.iterdir()), [])

    def test_only_old_candidates_fail_without_writes(self):
        fakebin = self.root / 'fakebin'; fakebin.mkdir()
        self.fake_old(fakebin / 'python.cmd')
        env = dict(self.env, CER_PYTHON='', PATH=str(fakebin))
        p = self.invoke('install', '--scope', 'project', '--project-root', str(self.project), env=env)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('3.11+', p.stderr)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_script_failure_exit_code_is_preserved(self):
        p = self.invoke('install', '--scope', 'invalid')
        self.assertEqual(p.returncode, 2, p.stderr)

    def test_install_and_uninstall_wrappers(self):
        flags = ('--scope', 'project', '--project-root', str(self.project))
        for entry in ('install.ps1', 'uninstall.ps1'):
            p = self.invoke(*flags, '--dry-run', entry=entry)
            self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_windows_powershell_51_probe_quoting(self):
        host = shutil.which('powershell.exe')
        if not host:
            self.skipTest('Windows PowerShell 5.1 unavailable')
        p = self.invoke('doctor', '--source-tree', str(ROOT), '--json', host=host)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)['policy'], 'PASS')


if __name__ == '__main__':
    unittest.main()
