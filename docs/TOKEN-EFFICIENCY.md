# Token and latency efficiency

## Account for the whole task

Measure parent plus all children, retries, tool-result input, verification and coordination. Distinguish total tokens, expensive-model tokens, monetary cost when actually available, and elapsed time. A cheaper model may emit more tokens. A parallel plan can finish sooner and consume more tokens. API prices are not Codex subscription quota conversion rates.

## Low-overhead defaults

Keep classification in the current coordinator; no extra LLM classifier. Use native tools for deterministic operations and safe tool concurrency before parallel model contexts. Avoid a child for a tiny/tool-bound task. Independent reasoning or capability requirements, not a file count, justify children.

Keep discovery metadata short. Load the core Skill only when relevant, and load routing/dispatch references only when necessary. Preserve evidence pointers, invariants, accepted decisions and final-workspace state in a compact handoff. Do not dump repository trees, full logs, the whole chat, or unrelated documentation into every child.

Prefer one child; cap ordinary parallelism at two and observe the actual host capacity. No fixed seconds or token-savings thresholds are presented as measured platform constants. Startup/context costs must be observed or conservatively estimated for the user's host and workload.

## Preserve useful cache and verification

Stable instructions and append-oriented context can help caching where the host supports it. This Skill does not control cache keys, compaction, or mid-conversation configuration APIs, and cannot promise cache reuse across model changes. Cached input still exists as tokens even when processing or pricing differs.

Specify required checks and stop conditions before work. Run checks that can falsify the intended behavior, plus repository requirements. Avoid repeated already-successful tests after no relevant change, but do not omit integration or residual-risk checks to make numbers look better.

## Evidence before claims

The v0.2 core was reduced from 13,264 to 7,206 UTF-8 bytes (45.67%) by removing duplication and moving detail to optional references. This is an instruction-size measurement, not tokenizer output, total-context savings, task-cost savings, latency improvement or proven quality equivalence. Actual gains require [paired trials](BENCHMARKING.md).

[Primary sources and applicability limits](PRIOR-ART.md)
