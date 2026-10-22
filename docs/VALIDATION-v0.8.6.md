# v0.8.6 validation

Base: `5457e97d95d77f2dc17b6a869e4082c338b510f0` (2026-10-22), not the older audited `ab2e882`.

This revision preserves the latest full/compat installation and paired-accounting changes.
It repairs the model-admission intersection, identity-only creation, source-package closure,
fixture path handling and surviving-mutation coverage. The ordinary native workflow and
explicitly configured strict admission are documented separately. No installed permission,
Guard registration, parent model or active user session is changed by this source update.

Validation is performed on the candidate source and immutable CI checkout. Record exact
results below after execution; an old version's green CI is not evidence for this revision.

## Acceptance boundary

The positive integration tests use real preparation/guard code and a temporary identity
SQLite database, not live model calls. They establish the tested software contracts, not
native Hook delivery/trust, actual Codex model selection, real task-quality equivalence,
total task tokens, subscription usage, latency or savings. The pinned host patch is
packaged unchanged and is not compiled or live-validated in this revision.

Native status/wait/interrupt/close use control tools. Bare continue/resume under strict
admission is intentionally still denied: caller receipts are not host-authenticated
reusable authority. Ordinary native routing does not fabricate those receipts or require
the optional patched host. Existing installed protections are never silently removed.
