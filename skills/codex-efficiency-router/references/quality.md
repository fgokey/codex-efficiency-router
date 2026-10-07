# Evidence and recovery

Files/rules: `page`; unknown: `locate --query Q`; current located lines: `excerpt --start N --lines N` (count 1..200). Fix limits/page/locate errors.

Checks: one Reader `batch --requests JSON_ARRAY --max-bytes N --framing-bytes N`. Check exit, then one results JSON; keep each cursor. JSON+CRLF+framing <=4KiB or narrow; no early member output. Resume gaps; disclose omissions. Other tools: capture/select/serialize/count before emit. Commentary/queries/waits/prompt rewrites do not reset backoff. Two unchanged snapshots: one saved-offset delta then back off; no repeat tails/polls/nudges until change. No doc/hook preload or child router copy. Requested/observed; reconcile unknown effects before replay. Never invent identity/savings/enforcement/cleanup.

Check semantic invariants, platform/macros, consumers, validation. Loss/eviction/coalescing: preserve effects or supported discard/replay/rebuild in affected states; else PARTIAL/BLOCKED.

Exhaustion stops blind edits, not diagnosis. Patch mismatch: inspect context/encoding/line endings; justified repair once, stop repeats. Retries persist per task/unit/signature across ALL owners/models/efforts/compaction; exhaustion needs diagnosis and justified absolute ceiling.

New tests != independent proof. Do not weaken assertions. Unrun is UNKNOWN, not PASS; required gaps: PARTIAL/BLOCKED.

Contract: requirement/check/state/PASS/FAIL/UNKNOWN. Findings cite before/after or requirement violation; label hypotheses. P1/P2: HEAD/line endings/callee/gray path; separate preexisting defects. Callback/gray/static score cannot prove event loss safe. Keep preexisting hazards open; unchanged baseline != diff.

Red/green: production, exact extraction + named stubs, or handwritten MODEL. Need text identity/full affected baseline; half-old/claimed extraction or whole-project stubs only illustrate.

`quality_reference.reuse_validation`: repo/commit, file/dependency hashes, command/scope/environment, PASS receipt. Change/unknown revalidates; commit-only: unaffected scope. Supplied, not authenticated/cached.

Checkpoint state/work/workers/failures/pairs/ceiling.

Status/check: one-shot; explicit watch: compact state/cadence; stop on cancel. BACKOFF: in-turn wait; heartbeat: defer schedule or pause, never skipped wakeups. Heartbeat: parent model/effort cost; child cost != task cost. Calls, uncached input/output/checks; cached input separate. Usage/prices UNKNOWN; no paid probes/polls. Router ROOT dev only: `ROOT/scripts/doctor.py --source-tree ROOT --preflight` full checks once; repeat for changes/failures.
