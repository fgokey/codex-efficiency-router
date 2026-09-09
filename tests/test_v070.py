"""v0.7 candidate regressions. All Canary fixtures here are SYNTHETIC TEST DATA.
No test in this module calls a model or certifies the real Codex host.
"""
from __future__ import annotations
import contextlib
import copy
from datetime import timedelta
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import canary
import manage
import release_package
import write_guard as wg
from compare_v2 import compare_three, call_cost
from release_identity import policy_hash, bundle_hash
from task_handshake import handshake


class TempCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.directory, self.config, self.backups = wg.targets('project', self.root)
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__(); self.addCleanup(self.quiet.__exit__, None, None, None)

    def install(self):
        wg.lifecycle('install', 'project', self.root)

    def status(self):
        return wg.inspect_status('project', self.root)


class GuardDiagnosticsV070(TempCase):
    def test_absent_is_policy_only_and_readonly(self):
        result = self.status()
        self.assertEqual(result['registration'], 'ABSENT')
        self.assertEqual(result['installation_mode'], 'policy-only')
        self.assertEqual(result['trust'], 'UNKNOWN')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_registered_not_live_and_exact_hash_binding(self):
        self.install(); result = self.status()
        self.assertEqual(result['registration'], 'PRESENT')
        self.assertEqual(result['live_verification'], 'NOT_RUN')
        self.assertEqual(result['runtime_loaded_version'], 'UNKNOWN')
        self.assertEqual(result['guard_sha256'], bundle_hash(ROOT / 'hooks'))
        self.assertIn(result['guard_sha256'], self.config.read_text())

    def test_legacy_manifest_outdated_not_broken(self):
        self.install()
        p = self.directory / 'manifest.json'; d = json.loads(p.read_text())
        for k in ('version', 'interpreter', 'guard_sha256', 'base_commit', 'policy_sha256'):
            d.pop(k, None)
        p.write_text(json.dumps(d))
        self.assertEqual(self.status()['registration'], 'OUTDATED')
        wg.lifecycle('update', 'project', self.root)
        self.assertEqual(self.status()['registration'], 'PRESENT')

    def test_missing_interpreter_is_broken(self):
        self.install()
        p = self.directory / 'manifest.json'; d = json.loads(p.read_text())
        d['interpreter'] = str(self.root / 'missing-python.exe'); p.write_text(json.dumps(d))
        result = self.status()
        self.assertEqual(result['registration'], 'BROKEN')
        self.assertFalse(result['interpreter_exists'])

    def test_modified_script_is_broken_and_preserved(self):
        self.install(); p = self.directory / wg.FILES[0]; p.write_text('custom')
        self.assertEqual(self.status()['registration'], 'BROKEN')
        with self.assertRaises(ValueError):
            wg.lifecycle('update', 'project', self.root)
        self.assertEqual(p.read_text(), 'custom')

    def test_malformed_config_returns_broken_json_not_exception(self):
        self.config.parent.mkdir(parents=True); self.config.write_text('{bad')
        self.assertEqual(self.status()['registration'], 'BROKEN')
        self.assertEqual(self.config.read_text(), '{bad')

    def test_duplicate_keys_fail_closed_diagnostic(self):
        self.config.parent.mkdir(parents=True); self.config.write_text('{"hooks":{},"hooks":{}}')
        self.assertEqual(self.status()['registration'], 'BROKEN')

    def test_overlap_report_preserves_foreign_group(self):
        self.install(); d = json.loads(self.config.read_text())
        foreign = {'matcher': '^Bash$', 'hooks': [{'type': 'command', 'command': 'echo foreign'}]}
        d['hooks']['PreToolUse'].append(foreign); self.config.write_text(json.dumps(d))
        before = self.config.read_bytes(); result = self.status()
        self.assertTrue(result['overlapping_groups'])
        self.assertEqual(self.config.read_bytes(), before)

    def test_duplicate_owned_hook_is_broken(self):
        self.install(); d = json.loads(self.config.read_text()); d['hooks']['PreToolUse'] *= 2
        self.config.write_text(json.dumps(d)); self.assertEqual(self.status()['registration'], 'BROKEN')

    def test_inline_hooks_and_disabled_feature_reported_without_edits(self):
        self.install(); cfg = self.config.with_name('config.toml')
        cfg.write_text('[features]\nhooks = false\n[[hooks.PreToolUse]]\nmatcher = "Bash"\n')
        before = cfg.read_bytes(); result = self.status()
        self.assertTrue(any('disabled' in w for w in result['warnings']))
        self.assertTrue(any('config.toml' in w for w in result['warnings']))
        self.assertEqual(cfg.read_bytes(), before)

    def test_update_dry_run_has_no_writes(self):
        self.install(); before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        wg.lifecycle('update', 'project', self.root, dry_run=True)
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_update_does_not_implicitly_install(self):
        with self.assertRaises(ValueError):
            wg.lifecycle('update', 'project', self.root, dry_run=True)
        self.assertFalse(self.config.exists())

    def test_rollback_never_overwrites_concurrent_external_edit(self):
        real = wg.replace; count = 0; first = None
        def raced(path, data):
            nonlocal count, first
            count += 1
            if count == 1:
                first = path
                return real(path, data)
            if count == 2:
                first.write_bytes(b'new external content')
                raise OSError('injected mid-transaction failure')
            return real(path, data)
        with patch.object(wg, 'replace', side_effect=raced), self.assertRaises(OSError):
            self.install()
        self.assertEqual(first.read_bytes(), b'new external content')
        self.assertFalse(self.config.exists())

    def test_skill_rollback_preserves_concurrent_edit(self):
        skill, agents, backups = manage.resolve_targets('project', self.root)
        backups.mkdir(parents=True)
        real = manage.replace; count = 0; first = None
        def raced(path, data):
            nonlocal count, first
            count += 1
            if count == 1:
                first = path; return real(path, data)
            if count == 2:
                first.write_bytes(b'external'); raise OSError('injected')
            return real(path, data)
        with patch.object(manage, 'replace', side_effect=raced), self.assertRaises(OSError):
            manage.apply({'skill/a.md': b'a', 'skill/b.md': b'b'}, skill, agents, backups, False)
        self.assertEqual(first.read_bytes(), b'external')

    def test_installed_fixed_profile_preserved_on_update(self):
        manage.install(ROOT, 'project', self.root, mode='fixed')
        manage.install(ROOT, 'project', self.root)
        skill, agents, _ = manage.resolve_targets('project', self.root)
        self.assertEqual(manage.installed_profile(skill, agents).mode, 'fixed')
        self.assertFalse(manage.installed_profile(skill, agents).allow_low)
        self.install(); result = self.status()
        self.assertEqual(result['installed_policy_sha256'], policy_hash(skill))

    def test_current_policy_edits_change_fingerprint(self):
        manage.install(ROOT, 'project', self.root, mode='fixed'); self.install()
        before = self.status()
        skill, _, _ = manage.resolve_targets('project', self.root)
        p = skill / 'references/dispatch.md'; p.write_text(p.read_text() + '\nchanged\n')
        after = self.status()
        self.assertNotEqual(before['fingerprint'], after['fingerprint'])
        self.assertTrue(any('bytes changed' in w for w in after['warnings']))

    def test_json_stdout_is_machine_readable(self):
        p = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/write_guard.py'), 'doctor', '--json',
                            '--scope', 'project', '--project-root', str(self.root)],
                           capture_output=True, text=True, timeout=15)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)['registration'], 'ABSENT')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_registered_bundle_tamper_denies_even_executor(self):
        self.install(); status = self.status()
        (self.directory / 'readonly_reader.py').write_text('# changed')
        event = {'hook_event_name': 'PreToolUse', 'model': 'gpt-5.6-sol', 'tool_name': 'apply_patch'}
        p = subprocess.run([sys.executable, '-I', '-B', str(self.directory / wg.FILES[0]),
                            '--expected-bundle', status['guard_sha256']], input=json.dumps(event),
                           capture_output=True, text=True, timeout=15)
        self.assertEqual(json.loads(p.stdout)['hookSpecificOutput']['permissionDecision'], 'deny')


class BatchReaderV070(TempCase):
    def setUp(self):
        super().setUp()
        self.reader = runpy.run_path(str(ROOT / 'hooks/readonly_reader.py'))
        (self.root / 'a.txt').write_text('Owner\nnext\n', encoding='utf-8')

    def run_reader(self, req):
        return self.reader['run'](self.root, req)

    def test_batch_matches_single_results(self):
        req = {'op': 'batch', 'requests': [{'op': 'read', 'path': 'a.txt'}, {'op': 'search', 'path': 'a.txt', 'query': 'Owner'}]}
        text = self.run_reader(req)
        self.assertIn('[1:read]\n1: Owner\n2: next', text)
        self.assertIn('[2:search]\n1: Owner', text)

    def test_batch_limit_and_nested_batches(self):
        for items in ([], [{'op': 'list'}] * 17, [{'op': 'batch', 'requests': [{'op': 'list'}]}]):
            with self.assertRaises(ValueError): self.run_reader({'op': 'batch', 'requests': items})

    def test_all_paths_preflight_before_any_operation(self):
        request = {'op': 'batch', 'requests': [{'op': 'read', 'path': 'a.txt'}, {'op': 'read', 'path': '../outside'}]}
        with patch.dict(self.reader['run'].__globals__, {'one': lambda *args: self.fail('partial execution')}):
            with self.assertRaises(ValueError): self.run_reader(request)

    def test_input_limit(self):
        with self.assertRaises(ValueError):
            self.run_reader({'op': 'search', 'path': 'a.txt', 'query': 'x' * 20000})

    def test_aggregate_file_budget(self):
        for name in ('big1', 'big2'):
            with (self.root / name).open('wb') as stream: stream.truncate(9 * 1024 * 1024)
        with self.assertRaises(ValueError):
            self.run_reader({'op': 'batch', 'requests': [{'op': 'read', 'path': name} for name in ('big1', 'big2')]})

    def test_runtime_growth_cannot_exceed_aggregate_budget(self):
        reader_run = self.reader['run']
        original_one = reader_run.__globals__['one']
        (self.root / 'b.txt').write_text('abc')
        def grow_after_preflight(root, request, path, remaining):
            if path.name == 'a.txt':
                path.write_text('1234567')
            return original_one(root, request, path, remaining)
        request = {'op': 'batch', 'requests': [{'op': 'read', 'path': n} for n in ('a.txt', 'b.txt')]}
        (self.root / 'a.txt').write_text('abc')
        with patch.dict(reader_run.__globals__, {'READ_LIMIT': 8, 'one': grow_after_preflight}):
            with self.assertRaises(ValueError):
                self.run_reader(request)

    def test_output_is_byte_bounded(self):
        (self.root / 'a.txt').write_text(('界' * 4096 + '\n') * 200, encoding='utf-8')
        result = self.run_reader({'op': 'read', 'path': 'a.txt', 'lines': 200})
        self.assertLessEqual(len(result.encode()), self.reader['LIMIT'])

    def test_aggregate_output_overflow_no_partial_return(self):
        (self.root / 'a.txt').write_text(('x' * 4096 + '\n') * 200, encoding='utf-8')
        with self.assertRaises(ValueError):
            self.run_reader({'op': 'batch', 'requests': [{'op': 'read', 'path': 'a.txt', 'lines': 200}] * 2})

    def test_batch_never_accepts_arbitrary_options(self):
        for extra in ('command', 'environment', 'git_args', 'redirect'):
            with self.assertRaises(ValueError):
                self.run_reader({'op': 'batch', 'requests': [{'op': 'read', 'path': 'a.txt', extra: 'bad'}]})

    def test_search_stays_single_file(self):
        with self.assertRaises(ValueError):
            self.run_reader({'op': 'search', 'path': '.', 'query': 'Owner'})

    def test_symlink_in_any_request_refuses_whole_batch(self):
        link = self.root / 'alias'
        try: link.symlink_to(self.root / 'a.txt')
        except OSError: self.skipTest('symlink privilege unavailable')
        with self.assertRaises(ValueError):
            self.run_reader({'op': 'batch', 'requests': [{'op': 'read', 'path': 'a.txt'}, {'op': 'read', 'path': 'alias'}]})

    def test_nonfinite_json_rejected_by_guard(self):
        guard = ROOT / 'hooks/astra_write_guard.py'
        raw = '{"hook_event_name":"PreToolUse","model":"gpt-5.6-sol","tool_name":"apply_patch","extra":NaN}'
        p = subprocess.run([sys.executable, '-I', '-B', str(guard)], input=raw, capture_output=True, text=True, timeout=10)
        self.assertEqual(json.loads(p.stdout)['hookSpecificOutput']['permissionDecision'], 'deny')


class CanaryV070(TempCase):
    def prepare_fixture(self):
        self.install(); run = canary.prepare(self.root)
        plan = json.loads((run / 'plan.json').read_text())
        observed = json.loads((run / 'observations.json').read_text())
        observed.update(codex_version='codex-cli test-host', reviewed_fingerprint=plan['fingerprint'], preexisting_exec_sessions=False)
        for name, item in observed['cases'].items():
            item.update(model='gpt-5.6-sol' if name.startswith('executor') else 'gpt-6-astra',
                        result=canary.CASES[name][1], hook_invoked=True,
                        guard_sha256=plan['guard_sha256'], elapsed_ms=1.0)
        (run / 'observations.json').write_text(json.dumps(observed))
        (run / 'executor.txt').write_bytes(canary.WRITTEN)
        return run, observed

    def test_prepare_needs_current_guard_and_no_implicit_install(self):
        with self.assertRaises(ValueError): canary.prepare(self.root)
        self.assertFalse(self.config.exists())

    def test_prepare_does_not_call_codex(self):
        self.install()
        with patch.object(canary, 'synthetic_unknown_check', side_effect=AssertionError('not during prepare')):
            run = canary.prepare(self.root)
        self.assertFalse((run / 'executor.txt').exists())
        self.assertIsNone(json.loads((run / 'observations.json').read_text())['codex_version'])

    def test_synthetic_observation_cannot_be_claimed_native(self):
        run, observed = self.prepare_fixture(); observed['source'] = 'synthetic'
        (run / 'observations.json').write_text(json.dumps(observed))
        with self.assertRaises(ValueError): canary.verify(run)

    def test_no_sentinel_alone_does_not_pass(self):
        run, observed = self.prepare_fixture(); observed['cases']['astra_patch_denied']['hook_invoked'] = False
        (run / 'observations.json').write_text(json.dumps(observed))
        self.assertEqual(canary.verify(run)['result'], 'FAIL')

    def test_unexpected_astra_write_is_failure(self):
        run, _ = self.prepare_fixture(); (run / 'astra-patch.txt').write_text('forbidden')
        self.assertEqual(canary.verify(run)['result'], 'FAIL')

    def test_unknown_existing_sessions_is_not_pass(self):
        for value in (None, True):
            run, observed = self.prepare_fixture(); observed['preexisting_exec_sessions'] = value
            (run / 'observations.json').write_text(json.dumps(observed))
            self.assertEqual(canary.verify(run)['result'], 'UNKNOWN')
            canary.cleanup(run)

    def test_fixture_pass_still_documents_unprotected_paths(self):
        run, _ = self.prepare_fixture(); report = canary.verify(run)
        self.assertEqual(report['result'], 'PASS')
        self.assertEqual(report['evidence_basis'], 'operator-witnessed-native')
        self.assertEqual(report['coverage']['write_stdin'], 'UNPROTECTED')
        # This is a test fixture, NOT an actual native Canary run.

    def test_hash_change_invalidates_canary(self):
        run, _ = self.prepare_fixture(); doc = json.loads(self.config.read_text())
        doc['description'] = 'changed'; self.config.write_text(json.dumps(doc))
        self.assertEqual(canary.verify(run)['result'], 'STALE')

    def test_expiry_invalidates_canary(self):
        run, _ = self.prepare_fixture(); p = run / 'plan.json'; d = json.loads(p.read_text())
        d['expires_at'] = (canary.now() - timedelta(seconds=1)).isoformat(); p.write_text(json.dumps(d))
        self.assertEqual(canary.verify(run)['result'], 'STALE')

    def test_private_extra_fields_are_rejected(self):
        run, observed = self.prepare_fixture(); observed['prompt'] = 'not allowed'
        (run / 'observations.json').write_text(json.dumps(observed))
        with self.assertRaises(ValueError): canary.verify(run)

    def test_cleanup_refuses_unknown_file(self):
        run, _ = self.prepare_fixture(); p = run / 'user-file'; p.write_text('keep')
        with self.assertRaises(ValueError): canary.cleanup(run)
        self.assertEqual(p.read_text(), 'keep')

    def test_cleanup_is_owned_only(self):
        run, _ = self.prepare_fixture(); outside = self.root / 'keep.txt'; outside.write_text('user')
        canary.cleanup(run)
        self.assertFalse(run.exists()); self.assertEqual(outside.read_text(), 'user')

    def test_reused_report_requires_current_codex_version_and_cleanup(self):
        run, _ = self.prepare_fixture(); report = canary.verify(run); status = self.status()
        self.assertEqual(canary.evaluate_saved_report(status, report)['live_verification'], 'UNKNOWN')
        self.assertEqual(canary.evaluate_saved_report(status, report, 'other-version')['live_verification'], 'STALE')
        self.assertEqual(canary.evaluate_saved_report(status, report, report['codex_version'])['live_verification'], 'FAIL')
        canary.cleanup(run); report['cleanup'] = 'PASS'
        state = canary.evaluate_saved_report(status, report, report['codex_version'])
        self.assertEqual(state['installation_mode'], 'live-verified')
        self.assertEqual(state['trust'], 'UNKNOWN')
        self.assertEqual(state['runtime_loaded_version'], 'UNKNOWN')

    def test_saved_pass_requires_actual_case_identity(self):
        run, _ = self.prepare_fixture(); report = canary.verify(run)
        canary.cleanup(run); report['cleanup'] = 'PASS'
        report['cases'][0]['actual'] = 'success'
        result = canary.evaluate_saved_report(self.status(), report, report['codex_version'])
        self.assertEqual(result['live_verification'], 'FAIL')

    def test_task_handshake_never_inferrs_loading_from_disk(self):
        self.install(); result = handshake(mode='fixed', guard_status=self.status())
        self.assertIn('vUNKNOWN', result); self.assertIn('policy=UNKNOWN', result)
        self.assertIn('guard=guarded', result)
        self.assertIsNone(handshake(already_reported=True))


class AccountingV070(unittest.TestCase):
    def rows(self, trials=1):
        rows = []
        for trial in range(trials):
            for n, variant in enumerate(('baseline', 'policy-only', 'guarded')):
                rows.append({'task_id': 'same', 'trial_id': str(trial), 'environment_id': 'same',
                    'acceptance_id': 'same', 'input_id': 'same-input-hash', 'variant': variant, 'outcome': 'pass',
                    'elapsed_seconds': 10 - n, 'critical_path_seconds': 5, 'waiting_seconds': 1,
                    'calls_complete': True, 'run_order': (n + trial) % 3 + 1, 'randomized_order': True,
                    'astra_writes': 0, 'duplicate_writers': 0, 'retry_replays': 0,
                    'guard': {'calls': 2, 'denied': 1, 'errors': 0, 'latencies_ms': [1, 2]} if variant == 'guarded' else None,
                    'calls': [{'call_id': 'root', 'model': 'gpt-6-astra', 'effort': 'high', 'attempt': 1,
                        'status': 'completed', 'input_tokens': 100, 'cached_input_tokens': 40, 'output_tokens': 20,
                        'actual_cost': {'amount': .1, 'currency': 'USD', 'source': 'test-invoice'}},
                        {'call_id': 'child', 'model': 'gpt-5.6-sol', 'effort': 'medium', 'attempt': 2,
                         'status': 'failed', 'input_tokens': 50, 'cached_input_tokens': 10, 'output_tokens': 5,
                         'actual_cost': {'amount': .02, 'currency': 'USD', 'source': 'test-invoice'}}]})
        return rows

    def test_parent_child_failed_costs_all_counted(self):
        result = compare_three(self.rows())
        self.assertAlmostEqual(result['measurements']['monetary_cost']['guarded'], .12)
        self.assertEqual(result['measurements']['total_tokens']['guarded'], 175)
        self.assertEqual(result['measurements']['elapsed_seconds']['guarded'], 8)

    def test_single_trial_not_formal_efficiency_claim(self):
        self.assertFalse(compare_three(self.rows())['efficiency_claim_eligible'])

    def test_three_randomized_complete_trials_sampling_gate(self):
        result = compare_three(self.rows(3))
        self.assertTrue(result['formal_sampling_ready']); self.assertTrue(result['efficiency_claim_eligible'])

    def test_quality_failure_blocks_all_efficiency_claims(self):
        rows = self.rows(3); rows[1]['outcome'] = 'fail'
        self.assertFalse(compare_three(rows)['efficiency_claim_eligible'])

    def test_missing_cost_unknown_not_zero(self):
        rows = self.rows(); rows[1]['calls'][0].pop('actual_cost')
        self.assertEqual(compare_three(rows)['measurements']['monetary_cost']['status'], 'UNKNOWN')

    def test_different_currencies_not_summed(self):
        rows = self.rows(); rows[2]['calls'][0]['actual_cost']['currency'] = 'CNY'
        self.assertEqual(compare_three(rows)['measurements']['monetary_cost']['status'], 'UNKNOWN')

    def test_cached_input_not_double_counted_in_price(self):
        call = self.rows()[0]['calls'][0]; call.pop('actual_cost')
        call['rates'] = {'model': call['model'], 'currency': 'USD', 'source': 'test-card', 'effective_at': '2026-09-09',
                         'input_per_million': 10, 'cached_input_per_million': 1, 'output_per_million': 20}
        value, _, basis = call_cost(call)
        self.assertAlmostEqual(value, (60 * 10 + 40 * 1 + 20 * 20) / 1000000)
        self.assertEqual(basis, 'rate-card-estimate')

    def test_missing_descendants_cannot_be_claimed_complete(self):
        rows = self.rows(3); rows[2]['calls_complete'] = False
        result = compare_three(rows)
        self.assertFalse(result['accounting_complete']); self.assertFalse(result['efficiency_claim_eligible'])

    def test_nan_and_boolean_metrics_are_rejected(self):
        for value in (float('nan'), float('inf'), True, -1):
            rows = self.rows(); rows[0]['calls'][0]['input_tokens'] = value
            with self.assertRaises(ValueError): compare_three(rows)

    def test_duplicate_call_and_changed_input_are_rejected(self):
        rows = self.rows(); rows[0]['calls'].append(copy.deepcopy(rows[0]['calls'][0]))
        with self.assertRaises(ValueError): compare_three(rows)
        rows = self.rows(); rows[1]['input_id'] = 'different'
        with self.assertRaises(ValueError): compare_three(rows)

    def test_writes_or_unknown_effort_prevent_efficiency_claim(self):
        rows = self.rows(3); rows[1]['astra_writes'] = 1
        self.assertFalse(compare_three(rows)['efficiency_claim_eligible'])
        rows = self.rows(3); rows[1]['calls'][0]['effort'] = 'UNKNOWN'
        self.assertFalse(compare_three(rows)['efficiency_claim_eligible'])

    def test_guard_counter_consistency(self):
        rows = self.rows(); rows[2]['guard']['calls'] = 20
        with self.assertRaises(ValueError): compare_three(rows)


class ReleaseV070(TempCase):
    def test_release_versions_hashes_and_schema(self):
        try: import jsonschema  # noqa: F401
        except ImportError: self.skipTest('optional jsonschema unavailable')
        self.assertEqual(release_package.validate_release(ROOT, schema=True), [])

    def test_package_is_reproducible_and_excludes_private_runtime_files(self):
        a = self.root / 'a.zip'; b = self.root / 'b.zip'
        release_package.build(a); release_package.build(b)
        self.assertEqual(a.read_bytes(), b.read_bytes())
        with zipfile.ZipFile(a) as archive:
            names = archive.namelist()
            self.assertFalse(any('/.git/' in n or '__pycache__' in n or '/evaluation-results/' in n for n in names))
            manifest = json.loads(archive.read('codex-efficiency-router/RELEASE-MANIFEST.json'))
            self.assertEqual(manifest['live_canary'], 'NOT_RUN')
            for name, expected in manifest['files'].items():
                self.assertEqual(release_package.sha(archive.read('codex-efficiency-router/' + name)), expected)

    def test_package_refuses_existing_output(self):
        p = self.root / 'already.zip'; p.write_bytes(b'keep')
        with self.assertRaises(ValueError): release_package.build(p)
        self.assertEqual(p.read_bytes(), b'keep')

    def test_plugin_windows_override_and_synchronous_mode(self):
        doc = json.loads((ROOT / 'hooks/hooks.json').read_text())
        command = doc['hooks']['PreToolUse'][0]['hooks'][0]
        self.assertIn('${PLUGIN_ROOT}', command['command'])
        self.assertIn('$env:PLUGIN_ROOT', command['commandWindows'])
        self.assertIsNot(command.get('async'), True)
        self.assertIn('--expected-bundle', command['command'])


if __name__ == '__main__':
    unittest.main()
