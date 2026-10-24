"""Launcher behavior, isolated from user configuration; Windows CI runs native PS.

Fake old runtimes test selection, not Python 3.10 compatibility. A separate CI job
also exercises an actual 3.10 default and an explicit real 3.12 override.
"""
import json
import hashlib
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
        self.env = dict(os.environ, CER_PYTHON=sys.executable,
                        CODEX_HOME=str(self.root / 'isolated codex home'))

    def invoke(self, *args, env=None, entry='cer.ps1', host=PWSH):
        return subprocess.run([host, '-NoProfile', '-NonInteractive', '-File', str(ROOT / entry), *args],
                              env=env or self.env, capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=30)

    def fake_old(self, path):
        path.write_text('@echo off\necho ' + json.dumps({'executable': sys.executable, 'version': [3, 10, 99]}) + '\nexit /b 0\n')
        return path

    def host_bundle(self, name='host bundle'):
        bundle = self.project / name
        bundle.mkdir()
        names = ('codex.exe', 'codex.pdb', 'codex-app-server.exe',
                 'codex_app_server.pdb', 'codex-code-mode-host.exe')
        files = {}
        for name in names:
            payload = ('fixture ' + name).encode()
            (bundle / name).write_bytes(payload)
            files[name] = hashlib.sha256(payload).hexdigest()
        manifest = {'owner': 'cer-native-admission-host', 'admission_contract': 2, 'files': files}
        (bundle / 'install.json').write_text(json.dumps(manifest))
        desktop = self.project / 'ChatGPT.exe'
        desktop.write_bytes(b'not executed during dry-run')
        return bundle, desktop, manifest

    def host_scenario(self, actions, *, user_cli=None, packages=None, record=None,
                      fail_set=False, running=False):
        """Run production host control flow with only OS effects replaced.

        Bundle checks, filesystem receipts and discovery run normally. No test may
        change the real user environment, start the desktop or inspect user state.
        """
        state = self.root / 'selection.json'
        state.unlink(missing_ok=True)
        if record is not None:
            state.write_text(json.dumps(record), encoding='utf-8')
        data = dict(actions=actions, user_cli=user_cli, packages=packages or [],
                    selection=str(state), fail_set=fail_set, running=running)
        harness = self.root / 'host-scenario.ps1'
        entry = str(ROOT / 'cer.ps1').replace("'", "''")
        harness.write_text(". '" + entry + "'\n" + r'''
$case = $env:CER_LAUNCH_TEST_DATA | ConvertFrom-Json
$script:UserCli = $case.user_cli
$script:SelectionFile = $case.selection
$script:Launch = $null
$script:SetCalls = 0
function Get-CerUserCli { return $script:UserCli }
function Set-CerUserCli {
    param([AllowNull()][string]$Value)
    $script:SetCalls++
    if ($case.fail_set) { throw 'fixture registry write denied' }
    $script:UserCli = if ($Value) { $Value } else { $null }
}
function Get-CerHostSelectionPath { return $script:SelectionFile }
$script:WriteSelection = (Get-Command Write-CerHostSelection).ScriptBlock
function Write-CerHostSelection {
    param([string]$Path, $Record)
    if ($script:InterruptAt -eq 'after_env' -and
        'transition_cli' -notin $Record.PSObject.Properties.Name) {
        $script:InterruptAt = $null
        throw 'fixture interrupted before selection finalization'
    }
    & $script:WriteSelection $Path $Record
    if ($script:InterruptAt -eq 'before_env') {
        $script:InterruptAt = $null
        throw 'fixture interrupted before environment update'
    }
}
function Get-AppxPackage { return $case.packages }
function Get-Process { if ($case.running) { [pscustomobject]@{Id=123;Name='ChatGPT'} } }
function Start-Process {
    param([string]$FilePath)
    $script:Launch = @{desktop=$FilePath;cli=$env:CODEX_CLI_PATH}
}
$env:CODEX_CLI_PATH = 'inherited-process-value'
$errors = @()
$reports = @()
$snapshots = @()
foreach ($action in $case.actions) {
    $script:InterruptAt = $action.interrupt_at
    if ('change_user' -in $action.PSObject.Properties.Name) {
        $script:UserCli = $action.change_user
    }
    try { $reports += @(Invoke-CerHost -Arguments @($action.args)) }
    catch { $errors += $_.Exception.Message }
    $saved = if (Test-Path -LiteralPath $script:SelectionFile) {
        Get-Content -LiteralPath $script:SelectionFile -Raw | ConvertFrom-Json
    } else { $null }
    $snapshots += @{user_cli=$script:UserCli;record=$saved}
}
$record = if (Test-Path -LiteralPath $script:SelectionFile) {
    Get-Content -LiteralPath $script:SelectionFile -Raw | ConvertFrom-Json
} else { $null }
[pscustomobject]@{reports=$reports;errors=$errors;user_cli=$script:UserCli;
    record=$record;launch=$script:Launch;set_calls=$script:SetCalls;snapshots=$snapshots;
    process_cli=$env:CODEX_CLI_PATH} | ConvertTo-Json -Depth 8 -Compress
''', encoding='utf-8')
        p = subprocess.run([PWSH, '-NoProfile', '-NonInteractive', '-File', str(harness)],
                           env=dict(self.env, CER_LAUNCH_TEST_DATA=json.dumps(data)),
                           capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)

    def desktop_package(self, version, *, complete=True):
        package = self.project / ('desktop-' + version)
        (package / 'app').mkdir(parents=True)
        if complete:
            (package / 'app' / 'ChatGPT.exe').write_bytes(b'fixture not executed')
        return dict(Version=version, InstallLocation=str(package))

    def test_host_discovers_newest_package_without_version_pinned_path(self):
        bundle, _, _ = self.host_bundle()
        packages = [self.desktop_package('26.1021.999.0'), self.desktop_package('26.1021.3705.0')]
        result = self.host_scenario([dict(args=[str(bundle), '--dry-run'])], packages=packages)
        self.assertEqual(result['errors'], [])
        report = json.loads(result['reports'][0])
        self.assertEqual(Path(report['desktop']), Path(packages[1]['InstallLocation']) / 'app/ChatGPT.exe')
        self.assertIsNone(result['record'])
        self.assertIsNone(result['launch'])

    def test_host_does_not_fall_back_from_broken_current_package(self):
        bundle, _, _ = self.host_bundle()
        packages = [self.desktop_package('1.0'), self.desktop_package('2.0', complete=False)]
        result = self.host_scenario([dict(args=[str(bundle), '--dry-run'])], packages=packages)
        self.assertIn('incomplete', result['errors'][0])
        self.assertIsNone(result['launch'])

    def test_host_missing_explicit_desktop_explains_auto_discovery(self):
        bundle, _, _ = self.host_bundle()
        p = self.invoke('host', str(bundle), str(self.root / 'removed-version.exe'), '--dry-run')
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('Omit it to discover', p.stderr)

    def test_host_persist_is_idempotent_and_keeps_original_backup(self):
        bundle, desktop, _ = self.host_bundle()
        persist = dict(args=[str(bundle), str(desktop), '--persist'])
        result = self.host_scenario([persist, persist], user_cli='C:\\previous\\codex.exe', running=True)
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['user_cli'], str(bundle / 'codex.exe'))
        self.assertEqual(result['record']['previous_cli'], 'C:\\previous\\codex.exe')
        self.assertEqual(result['process_cli'], 'inherited-process-value')
        self.assertIsNone(result['launch'])

    def test_host_restore_preserves_absence_and_previous_value(self):
        bundle, desktop, _ = self.host_bundle()
        for previous in (None, 'C:\\previous\\codex.exe'):
            with self.subTest(previous=previous):
                result = self.host_scenario([
                    dict(args=[str(bundle), str(desktop), '--persist']), dict(args=['--restore'])
                ], user_cli=previous)
                self.assertEqual(result['errors'], [])
                self.assertEqual(result['user_cli'], previous)
                self.assertIsNone(result['record'])

    def test_host_persistence_previews_do_not_apply_changes(self):
        bundle, desktop, _ = self.host_bundle()
        result = self.host_scenario([dict(args=[str(bundle), str(desktop), '--persist', '--dry-run'])])
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['set_calls'], 0)
        self.assertIsNone(result['record'])
        result = self.host_scenario([
            dict(args=[str(bundle), str(desktop), '--persist']), dict(args=['--restore', '--dry-run'])
        ])
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['set_calls'], 1)
        self.assertEqual(result['user_cli'], str(bundle / 'codex.exe'))
        self.assertIsNotNone(result['record'])

    def test_host_restore_and_reinstall_refuse_external_environment_change(self):
        bundle, desktop, _ = self.host_bundle()
        persist = dict(args=[str(bundle), str(desktop), '--persist'])
        result = self.host_scenario([
            persist, dict(args=['--restore'], change_user='C:\\custom\\codex.exe'), persist
        ])
        self.assertEqual(len(result['errors']), 2)
        self.assertTrue(all('changed outside' in e for e in result['errors']))
        self.assertEqual(result['user_cli'], 'C:\\custom\\codex.exe')
        self.assertEqual(result['record']['cli'], str(bundle / 'codex.exe'))

    def test_host_refuses_unowned_selection_without_mutation(self):
        bundle, desktop, _ = self.host_bundle()
        record = {'owner': 'another-installer'}
        result = self.host_scenario([dict(args=[str(bundle), str(desktop), '--persist'])], record=record)
        self.assertIn('Unowned', result['errors'][0])
        self.assertEqual(result['record'], record)
        self.assertEqual(result['set_calls'], 0)

    def test_host_failed_environment_write_restores_backup_state(self):
        bundle, desktop, _ = self.host_bundle()
        result = self.host_scenario([dict(args=[str(bundle), str(desktop), '--persist'])], fail_set=True)
        self.assertIn('registry write denied', result['errors'][0])
        self.assertIsNone(result['record'])
        self.assertIsNone(result['user_cli'])

    def test_host_interrupted_update_can_retry_or_restore_original(self):
        first, desktop, _ = self.host_bundle()
        second, _, _ = self.host_bundle('updated host bundle')
        first_cli, second_cli = str(first / 'codex.exe'), str(second / 'codex.exe')
        for previous in (None, 'C:\\previous\\codex.exe'):
            for interruption in ('before_env', 'after_env'):
                for recovery in ('retry', 'restore'):
                    with self.subTest(previous=previous, interruption=interruption, recovery=recovery):
                        update = [str(second), str(desktop), '--persist']
                        result = self.host_scenario([
                            dict(args=[str(first), str(desktop), '--persist']),
                            dict(args=update, interrupt_at=interruption),
                            dict(args=update if recovery == 'retry' else ['--restore']),
                        ], user_cli=previous)
                        self.assertEqual(len(result['errors']), 1)
                        self.assertIn('fixture interrupted', result['errors'][0])
                        interrupted = result['snapshots'][1]
                        self.assertEqual(interrupted['user_cli'],
                                         first_cli if interruption == 'before_env' else second_cli)
                        self.assertEqual(interrupted['record']['cli'], second_cli)
                        self.assertEqual(interrupted['record']['previous_cli'], previous)
                        self.assertEqual(interrupted['record']['transition_cli'], first_cli)
                        if recovery == 'retry':
                            self.assertEqual(result['user_cli'], second_cli)
                            self.assertEqual(result['record'], dict(owner='cer-native-host-selection',
                                             schema=1, cli=second_cli, previous_cli=previous))
                        else:
                            self.assertEqual(result['user_cli'], previous)
                            self.assertIsNone(result['record'])

    def test_host_interrupted_update_refuses_unrelated_external_change(self):
        first, desktop, _ = self.host_bundle()
        second, _, _ = self.host_bundle('updated host bundle')
        external = 'C:\\custom\\codex.exe'
        for interruption in ('before_env', 'after_env'):
            with self.subTest(interruption=interruption):
                update = [str(second), str(desktop), '--persist']
                result = self.host_scenario([
                    dict(args=[str(first), str(desktop), '--persist']),
                    dict(args=update, interrupt_at=interruption),
                    dict(args=['--restore'], change_user=external), dict(args=update),
                ])
                self.assertEqual(len(result['errors']), 3)
                self.assertTrue(all('changed outside' in error for error in result['errors'][1:]))
                self.assertEqual(result['user_cli'], external)
                self.assertEqual(result['record'], result['snapshots'][1]['record'])

    def test_host_completed_update_does_not_trust_former_selection(self):
        first, desktop, _ = self.host_bundle()
        second, _, _ = self.host_bundle('updated host bundle')
        update = [str(second), str(desktop), '--persist']
        result = self.host_scenario([
            dict(args=[str(first), str(desktop), '--persist']), dict(args=update),
            dict(args=['--restore'], change_user=str(first / 'codex.exe')), dict(args=update),
        ])
        self.assertEqual(len(result['errors']), 2)
        self.assertTrue(all('changed outside' in error for error in result['errors']))
        self.assertNotIn('transition_cli', result['record'])
        self.assertEqual(result['user_cli'], str(first / 'codex.exe'))
        self.assertIsNone(result['record']['previous_cli'])

    def test_host_saved_selection_launch_discovers_package_and_restores_process_env(self):
        bundle, desktop, _ = self.host_bundle()
        package = self.desktop_package('26.1021.3705.0')
        result = self.host_scenario([
            dict(args=[str(bundle), str(desktop), '--persist']), dict(args=[])
        ], packages=[package])
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['launch']['cli'], str(bundle / 'codex.exe'))
        self.assertEqual(Path(result['launch']['desktop']), Path(package['InstallLocation']) / 'app/ChatGPT.exe')
        self.assertEqual(result['process_cli'], 'inherited-process-value')

    def test_host_launch_refuses_running_desktop(self):
        bundle, desktop, _ = self.host_bundle()
        result = self.host_scenario([dict(args=[str(bundle), str(desktop)])], running=True)
        self.assertIn('Close the desktop', result['errors'][0])
        self.assertIsNone(result['launch'])

    def test_host_saved_launch_preserves_external_environment_change(self):
        bundle, desktop, _ = self.host_bundle()
        result = self.host_scenario([
            dict(args=[str(bundle), str(desktop), '--persist']),
            dict(args=[], change_user='C:\\custom\\codex.exe')
        ])
        self.assertIn('refusing the saved selection', result['errors'][0])
        self.assertIsNone(result['launch'])
        self.assertEqual(result['user_cli'], 'C:\\custom\\codex.exe')

    def test_host_changed_bundle_cannot_be_persisted(self):
        bundle, desktop, _ = self.host_bundle()
        (bundle / 'codex.exe').write_bytes(b'changed')
        result = self.host_scenario([dict(args=[str(bundle), str(desktop), '--persist'])])
        self.assertIn('No desktop fallback', result['errors'][0])
        self.assertEqual(result['set_calls'], 0)
        self.assertIsNone(result['record'])

    def test_host_restore_after_interrupted_cleanup_does_not_overwrite_environment(self):
        bundle, _, _ = self.host_bundle()
        record = dict(owner='cer-native-host-selection', schema=1,
                      cli=str(bundle / 'codex.exe'), previous_cli=None)
        result = self.host_scenario([dict(args=['--restore'])], record=record)
        self.assertEqual(result['errors'], [])
        self.assertIsNone(result['record'])
        self.assertIsNone(result['user_cli'])

    def test_host_preview_verifies_files_without_starting_or_setting_environment(self):
        bundle, desktop, _ = self.host_bundle()
        before = dict(os.environ)
        p = self.invoke('host', str(bundle), str(desktop), '--dry-run')
        self.assertEqual(p.returncode, 0, p.stderr)
        report = json.loads(p.stdout)
        self.assertEqual(report['status'], 'VERIFIED_FILES_ONLY')
        self.assertEqual(report['live_admission'], 'UNKNOWN')
        self.assertEqual(os.environ, before)

    def test_host_missing_or_changed_binary_cannot_fall_back(self):
        bundle, desktop, _ = self.host_bundle()
        for payload in (b'changed official binary', None):
            if payload is None:
                (bundle / 'codex.exe').unlink()
            else:
                (bundle / 'codex.exe').write_bytes(payload)
            p = self.invoke('host', str(bundle), str(desktop), '--dry-run')
            self.assertNotEqual(p.returncode, 0)
            self.assertIn('No desktop fallback', p.stderr)

    def test_host_rejects_legacy_manifest_and_missing_auxiliary(self):
        bundle, desktop, manifest = self.host_bundle()
        (bundle / 'codex-code-mode-host.exe').unlink()
        p = self.invoke('host', str(bundle), str(desktop), '--dry-run')
        self.assertNotEqual(p.returncode, 0)
        manifest.pop('admission_contract')
        (bundle / 'install.json').write_text(json.dumps(manifest))
        p = self.invoke('host', str(bundle), str(desktop), '--dry-run')
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('legacy manifests', p.stderr)

    def test_host_rejects_path_escape_in_manifest(self):
        bundle, desktop, manifest = self.host_bundle()
        manifest['files']['../outside.exe'] = '0' * 64
        (bundle / 'install.json').write_text(json.dumps(manifest))
        p = self.invoke('host', str(bundle), str(desktop), '--dry-run')
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('Invalid host manifest', p.stderr)

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
