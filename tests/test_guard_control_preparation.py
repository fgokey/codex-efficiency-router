"""Actual preparation/send contract regressions, without a Codex or model call."""
import copy
import json
from pathlib import Path
import runpy
import unittest

import test_dispatch_coherence as coherence

ROOT = Path(__file__).resolve().parents[1]


class ControlPreparationTests(unittest.TestCase):
    setUp = coherence.DispatchCoherenceTests.setUp
    child = coherence.DispatchCoherenceTests.child
    request = coherence.DispatchCoherenceTests.request
    prepare = coherence.DispatchCoherenceTests.prepare
    send = coherence.DispatchCoherenceTests.send
    assertDenied = coherence.DispatchCoherenceTests.assertDenied

    def native_prepare(self, request):
        return coherence.G['decide_dispatch'](
            {'hook_event_name': 'PreToolUse', 'model': 'gpt-6-astra',
             'session_id': 'parent', 'tool_name': 'prepare_agent_task',
             'tool_input': {'request': request}},
            host_directory=self.host, policy_root=self.skill)

    def test_prepared_controls_reuse_unit_without_recreating_worker(self):
        receiver = self.child()
        work = self.request(receiver)
        release = self.prepare(work)
        self.assertEqual(self.send(receiver, coherence.R['assignment_message'](release, work['message'])), {})
        before = self.db.read_bytes()
        for purpose, word in (('continue', '继续'), ('status', 'status'), ('stop', '停止')):
            request = {'unit_id': work['unit_id'], 'purpose': purpose, 'scope': work['scope'],
                       'message': word, 'recipient': receiver, 'receipt': release['receipt']}
            result = self.native_prepare(request)
            prepared = json.loads(result['hookSpecificOutput']['additionalContext'])
            self.assertEqual(prepared['status'], 'VERIFIED')
            self.assertEqual(self.send(receiver, coherence.R['assignment_message'](prepared, word)), {})
            self.assertEqual(prepared['receipt']['message_sha256'], release['receipt']['message_sha256'])
        self.assertEqual(self.db.read_bytes(), before)

    def test_control_label_never_readmits_new_work(self):
        receiver = self.child()
        work = self.request(receiver)
        release = self.prepare(work)
        for purpose in ('continue', 'status', 'stop'):
            # Previously silently promoted to new_unit by the Reader, despite a
            # control label. Require explicit new_unit for any additional work.
            for message in (work['message'], purpose + '\nEdit another file.', 'RELEASE other_unit'):
                request = dict(work, purpose=purpose, message=message)
                for receipt in (None, {}, release['receipt']):
                    bad = copy.deepcopy(request)
                    if receipt is not None:
                        bad['receipt'] = receipt
                    self.assertDenied(self.native_prepare(bad))
            bad = dict(work, purpose=purpose, message=purpose)
            self.assertDenied(self.native_prepare(bad))

    def test_reviewable_guard_digest_is_emitted_for_packaging(self):
        identity = runpy.run_path(str(ROOT / 'scripts/release_identity.py'))['source_identity'](ROOT)
        self.assertRegex(identity['guard_sha256'], r'^[0-9a-f]{64}$')
        print('CER_REVIEWED_GUARD_BUNDLE=' + identity['guard_sha256'])


if __name__ == '__main__':
    unittest.main()
