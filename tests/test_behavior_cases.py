"""Validate the acceptance corpus structure, not model responses or triggering."""
import json
import unittest
from pathlib import Path


class BehaviorCorpusTests(unittest.TestCase):
    def test_corpus_is_complete_and_explicitly_unrun(self):
        source = Path(__file__).resolve().parents[1] / 'evaluation/behavior_cases.json'
        data = json.loads(source.read_text(encoding='utf-8'))
        self.assertEqual(data['schema'], 1)
        self.assertIn('NOT executed', data['purpose'])
        cases = data['cases']
        self.assertEqual(len(cases), 21)
        self.assertEqual(len({item['id'] for item in cases}), len(cases))
        self.assertTrue(any(not item['should_invoke_router'] for item in cases))
        self.assertEqual({item['category'] for item in cases}, {'trigger', 'handoff', 'completion', 'measurement', 'recovery', 'routing'})
        for item in cases:
            with self.subTest(case=item['id']):
                self.assertIs(type(item['should_invoke_router']), bool)
                self.assertTrue(item['user_prompt'].strip() and item['setup'].strip())
                self.assertTrue(item['required_observations'] and item['forbidden_observations'])
                self.assertIsNone(item['live_result'])


    def test_effort_corpus_is_separate_and_unrun(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / 'evaluation/effort_cases.json').read_text(encoding='utf-8'))
        self.assertIn('NOT executed', data['purpose'])
        self.assertEqual(len(data['cases']), 10)
        self.assertEqual(len({c['id'] for c in data['cases']}), 10)
        for case in data['cases']:
            self.assertTrue(case['setup'] and case['user_prompt'])
            self.assertTrue(case['required_observations'] and case['forbidden_observations'])
            self.assertIsNone(case['live_result'])


if __name__ == '__main__':
    unittest.main()
