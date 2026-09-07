# Token and latency efficiency

## Account for the whole task

Measure parent plus all children, retries, tool-result input, verification and coordination. Distinguish total tokens, expensive-model tokens, monetary cost when actually available, and elapsed time. A cheaper model may emit more tokens. A parallel plan can finish sooner and consume more tokens. API prices are not Codex subscription quota conversion rates.

## Low-overhead defaults

Keep classification in the current coordinator; no extra LLM classifier. Use native tools for deterministic operations and safe tool concurrency before parallel model contexts. Avoid a child for a tiny/tool-bound task. Independent reasoning or capability requirements, not a file count, justify children.

Keep discovery metadata short. Load the core Skill only when relevant, and load routing/dispatch/quality references only when necessary. Preserve evidence pointers, invariants, accepted decisions and final-workspace state in a compact handoff. Do not dump repository trees, full logs, the whole chat, or unrelated documentation into every child.

Prefer one child; cap ordinary parallelism at two and observe the actual host capacity. No fixed seconds or token-savings thresholds are presented as measured platform constants. Startup/context costs must be observed or conservatively estimated for the user's host and workload.

## Preserve useful cache and verification

Stable instructions and append-oriented context can help caching where the host supports it. This Skill does not control cache keys, compaction, or mid-conversation configuration APIs, and cannot promise cache reuse across model changes. Cached input still exists as tokens even when processing or pricing differs.

Specify required checks and stop conditions before work. Run checks that can falsify the intended behavior, plus repository requirements. Avoid repeated already-successful tests after no relevant change, but do not omit integration or residual-risk checks to make numbers look better.

## Historical measurement (v0.2.0)

The v0.2 core was reduced from 13,264 to 7,206 UTF-8 bytes (45.67%) by removing duplication and moving detail to optional references. This is an instruction-size measurement, not tokenizer output, total-context savings, task-cost savings, latency improvement or proven quality equivalence. Actual gains require [paired trials](BENCHMARKING.md).

[Primary sources and applicability limits](PRIOR-ART.md)

## v0.2.1 full-path budget

Core-only reduction was insufficient: the independent v0.2.0 experiment found full reference loading could exceed v0.1 core overhead. v0.2.1 removes repeated rules, keeps boundary examples separate from native-dispatch details, and checks both core and **all** references. The ordinary doctor enforces byte budgets without a tokenizer dependency; separate offline CI counts raw text using pinned tiktoken and two named encodings. Its full-load gate must not exceed the historical v0.1 core under either encoding.

These are scoped source-text measurements, not host prompt totals or billed usage. The baseline is read from its fixed Git commit, never edited to make the comparison pass. Descriptions already inside the core are not added a second time. Per-role instructions are reported separately; inherited context and host framing remain excluded. [Current validation](VALIDATION-v0.2.1.md) records results, and [acceptance](ACCEPTANCE.md) leaves real quality/usage/latency verification to the user.

## v0.3 regression budget

The full current Skill includes three references. Separate offline CI compares core, all references, and all-reference text plus each role's own instruction text against the immutable v0.2.1 tree. Budgets are not raised to accommodate quality additions. A raw-text budget is not full-context billing; observed model identity, actual usage, retries and elapsed time still require user acceptance. See [release validation](VALIDATION-v0.3.0.md).
