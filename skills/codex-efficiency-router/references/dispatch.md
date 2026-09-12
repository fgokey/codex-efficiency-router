# Native dispatch and guard

Wait for owners; never interrupt writers or let leaves spawn/publish.

## Native change summary and review

Before write routing, compare every target repository with task workspace roots. A required parent badge needs that repository as task workspace and the same parent to own writes. Normally use a write-capable Sol/Terra parent and Astra as a read-only child. Root Astra may own only the fully qualified bounded local-patch exception. Otherwise an Astra parent, outside repository or missing child `fileChange` aggregation makes the badge unavailable: stop before writes. Native review/open-review does not populate that badge.

Writers return every repository root, exact changed paths/status and owned vs pre-existing dirt. Parent verifies status/diff per repository and opens unstaged review. Never touch/reapply files only for attribution.

The optional strict PreToolUse Guard denies every Astra/unknown shell, patch and unknown tool. The root exception requires confirmed inactive status; unknown/active blocks it. Reads/coordination work.

Astra NEVER inputs to existing shells: `write_stdin` is UNPROTECTED. Only the original executor continues. Hosted paths are UNPROTECTED; specialized paths UNKNOWN.

With an active Guard, `cer-read` supports read/list/search/diff/status and flat batches. It is a rewrite protocol, NOT a shell binary; never replay it inactive. Shell/build/test belongs to executors.

Batch: 1-16 requests; 16 KiB input, 16 MiB reads, 128 KiB output. Preflight paths; invalid batch has no partial output. Search is one-file literal; no commands.
