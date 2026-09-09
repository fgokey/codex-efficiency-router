# Offline quality and text-token evaluation

Target source: `7111d7d2b83f330c9f0e693a74fe97c5ea4dec1b`.
Historical routing baseline: `e92d89a79c05985980420a0bfd6a51baec93ba81`.

This isolated evaluation branch does not change runtime policy, tests, installer or main.
It reruns the existing tests, tests ten deliberate policy mutations, checks eight
additional boundary scenarios, and counts actual text tokens under two explicitly
named reference encodings using pinned OpenAI tiktoken 0.11.0.

```sh
python -m pip install tiktoken==0.11.0
python evaluation/quality_token_audit.py
```

The output and full test logs are in `evaluation-results/` and in the read-only
GitHub Actions artifact. A failed boundary intentionally makes the workflow red;
this is not masked by passing existing tests. Mutations execute only in isolated
subprocess module objects and never alter source files. The new same-lane holdout
is a proposed executable interpretation of the Skill's requirement that same-model
delegation have a concrete isolation/review benefit. It does not measure live model
quality, and a failing offline helper case is not proof of live Codex misbehavior.

Text counts omit host framing, other instructions, tools, task input, hidden
reasoning, output, retries and live child contexts. Model-to-tokenizer mappings
not known to the pinned library are explicitly UNKNOWN, not silently assumed.
Counts for o200k_base/cl100k_base are reproducible reference-encoding counts,
NOT a claim of exact Astra billing. Full loaded references may offset core-size
reductions. A byte or reference-token reduction is not a whole-task saving.

No model inference, login, credentials or live coding A/B test is performed. Actual
quality, total usage and elapsed-time comparisons still require the user's Codex
host with independent acceptance checks and full parent/child/retry accounting.
See `docs/BENCHMARKING.md` in the target repository.
