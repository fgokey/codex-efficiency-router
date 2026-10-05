# Evidence and recovery

first load SKILL alone in bounded pages. Reader handoff both. All ops: `--root ABS --path PATH`. Files/rules: `page`, same root/path `--cursor TOKEN` to null; unknown: `locate --query Q`; current located lines: `excerpt --start N --lines N` (count 1..200). Check exit before JSON; fix limits/page/locate on error. Page <=4096B; default `--max-bytes 3072`; framing extra. no full-file slicing/merging pages/files.

capture result, select fields, retain cursor, serialize/count total output below outer incl framing <=4KiB, then emit one page. Inner/item/line caps fail. Resume gaps; shrink batches; disclose omissions. Commentary, completed queries/waits and prompt rewrites do not reset backoff. Two unchanged snapshots: one saved-offset delta then back off; no repeat tails/polls/nudges until change. No doc/hook preload or child router copy. Report requested/observed; reconcile unknown effects before replay. Never invent identity/savings/enforcement/cleanup.

Check semantic invariants, platform/macros, consumers, validation. Loss/eviction/coalescing: preserve effects or supported discard/replay/rebuild across affected states; else PARTIAL/BLOCKED.

Exhaustion stops blind edits, not diagnosis. Patch mismatch: inspect context/encoding/line endings; one justified repair, then repeat stops blind retry. Retries persist per task/unit/signature across ALL owners/models/efforts/compaction; exhaustion needs diagnosis and justified absolute ceiling.

New tests are not independent proof. Do not weaken assertions. Unrun is UNKNOWN, not PASS; required gaps mean PARTIAL/BLOCKED.

Contract: requirement/check/state/PASS/FAIL/UNKNOWN. Findings cite before/after or requirement violation; label hypotheses. P1/P2: HEAD/line endings/callee/gray path; separate preexisting defects. Callback/gray/static score cannot prove event loss safe. Keep preexisting hazards open; unchanged baseline is not diff.

Red/green: production, exact extraction + named stubs, or handwritten MODEL. Require text identity/full affected baseline; half-old/claimed extraction or whole-project stubs only illustrate.

`quality_reference.reuse_validation`: repo/commit, file/dependency hashes, command/scope/environment, PASS receipt. Change/unknown revalidates; commit-only needs unaffected scope. Supplied, not authenticated/cached.

Checkpoint state/work/workers/failures/pairs/ceiling.

Heartbeat inherits parent model/effort cost; child cost != task cost. Existing records: calls, uncached input, output, repeated checks; cached input separate. Usage/prices UNKNOWN; no paid probes/polls. Router source: `doctor.py --source-tree ROOT --preflight` then full checks once; repeat only on new changes/failures.
