import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import doctor
from package import EXPECTED, PROJECT


class DoctorTests(unittest.TestCase):
    def catalog(self):
        return {"result": {"data": [
            {"model": model, "supportedReasoningEfforts": [{"reasoningEffort": effort}]}
            for _, model, effort in EXPECTED.values()], "nextCursor": None}}

    def test_source_integrity(self):
        self.assertEqual(doctor.validate_tree(ROOT / "skills" / PROJECT / "SKILL.md", ROOT / "agents"), [])

    def test_truncation_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "skill"
            shutil.copytree(ROOT / "skills" / PROJECT, skill)
            p = skill / "SKILL.md"
            p.write_text(p.read_text(encoding="utf-8").split("## Handoff")[0], encoding="utf-8")
            self.assertTrue(doctor.validate_tree(p, ROOT / "agents"))

    def test_valid_export_and_raw_result(self):
        data = self.catalog()
        self.assertEqual(doctor.validate_catalog(data), [])
        self.assertEqual(doctor.validate_catalog(data["result"]), [])

    def test_incomplete_catalog_refused(self):
        data = self.catalog()
        data["result"]["nextCursor"] = "more"
        self.assertTrue(doctor.validate_catalog(data))

    def test_missing_model_or_effort(self):
        for field in ("model", "supportedReasoningEfforts"):
            data = self.catalog()
            data["result"]["data"][0][field] = "missing" if field == "model" else []
            self.assertTrue(doctor.validate_catalog(data))

    def test_malformed_catalog(self):
        for data in (None, [], {}, {"result": []}, {"data": [None]}, {"data": [{"model": [], "supportedReasoningEfforts": []}]}):
            with self.subTest(data=data):
                self.assertTrue(doctor.validate_catalog(data))

    def test_policy_manifest_matches_shipped_models(self):
        policy = json.loads((ROOT / "policy/routing-policy.json").read_text())
        actual = {(v["model"], v["effort"]) for v in policy["models"].values()}
        self.assertEqual(actual, {(m, e) for _, m, e in EXPECTED.values()})
        self.assertIn("benefit_gated_deescalation", policy["principles"])
        self.assertIn("bounded_output_envelope_before_batch_reads", policy["principles"])
        self.assertIn("model_roundtrips_are_budgeted_even_with_cached_input", policy["principles"])
        self.assertIn("tool_discovery_reused_until_invalidation", policy["principles"])
        self.assertIn("worker_monitoring_uses_backoff_and_delta_cursors", policy["principles"])
        self.assertIn("host_observed_writer_binding_precedes_every_write_tool", policy["principles"])
        self.assertIn("forward_mutation_is_separate_from_destructive_recovery", policy["principles"])
        self.assertIn("policy_denial_stops_equivalent_replay", policy["principles"])
        self.assertEqual(policy["context_efficiency"], {
            "mandatory_rules": "one file per output envelope",
            "unknown_size": "index before content",
            "batch": "known-small relevant slices within aggregate output budget",
            "truncation": "resume missing ranges; never reread captured prefixes",
            "tool_discovery": "reuse known schemas until host or state invalidation",
            "roundtrip": "act only on changed state or a due checkpoint; batch bounded independent checks",
            "worker_progress": "compact native wait with backoff; after two unchanged snapshots read one bounded rollout delta from a saved offset, never both paths",
        })
        self.assertEqual(policy["mutation_admission"], {
            "writer_binding": "parent verifies host-observed Terra/Sol model, effort and non-read-only role before every write tool",
            "command_shape": "one exact manifest and one bounded mutation class per tool call",
            "recovery": "forward copy, config rewrite and destructive recovery are separate reviewed units",
            "policy_denial": "stop exact or equivalent replay until host or user policy changes",
        })

    def test_shipped_core_budget(self):
        core = (ROOT / "skills" / PROJECT / "SKILL.md").read_bytes()
        self.assertLessEqual(len(core), 8000)


if __name__ == "__main__":
    unittest.main()
