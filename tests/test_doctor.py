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
        self.assertIn("scoped_repair_binding_reused_until_invalidation", policy["principles"])
        self.assertIn("forward_mutation_is_separate_from_destructive_recovery", policy["principles"])
        self.assertIn("policy_denial_stops_equivalent_replay", policy["principles"])
        self.assertIn("parent_reviews_complete_diff_validation_and_blocking_findings", policy["principles"])
        self.assertIn("every_batched_read_member_is_bounded_before_content", policy["principles"])
        self.assertEqual(policy["context_efficiency"], {
            "mandatory_rules": "separate bounded chunks until the required text is complete",
            "unknown_size": "index, summarize or split before combining; line count alone does not bound content volume",
            "batch": "all shell, web and nested-tool results plus headroom fit the smallest enclosing output cap",
            "mixed_command": "every result counts against the outer envelope",
            "truncation": "recover only the missing relevant range from its cursor without replaying effects",
            "tool_discovery": "reuse known schemas until host or state invalidation",
            "roundtrip": "act only on changed state or a due checkpoint; batch bounded independent checks",
            "worker_progress": "after two unchanged snapshots read one saved-offset delta, then back off until change or due; no overlapping tails, status nudges or short polls",
        })
        self.assertEqual(policy["mutation_admission"], {
            "writer_binding": "parent verifies host-observed model, effort, role, permission and owner once per scoped repair unit; reuse until invalidated by those fields, session resume or contradictory evidence",
            "repair_unit": "implementation, source/build config, formatting, targeted tests and self-check need no per-command reauthorization",
            "separate_units": "binary copy, runtime/permission config, deployment and destructive recovery remain separately bounded",
            "policy_denial": "stop exact or equivalent replay until a supported permission change",
            "approval_never": "approval=never alone is not a manual-action boundary",
        })

    def test_shipped_core_budget(self):
        core = (ROOT / "skills" / PROJECT / "SKILL.md").read_bytes()
        self.assertLessEqual(len(core), 8000)


if __name__ == "__main__":
    unittest.main()
