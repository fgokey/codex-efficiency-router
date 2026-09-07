# Repository instructions for coding agents

This repository defines a routing policy whose primary invariant is: **do not claim efficiency by accepting lower verified quality**.

When changing the project:

- keep runtime dependencies at zero unless a measurable requirement justifies one;
- do not add a separate LLM routing call to the default path;
- preserve the default installer's non-destructive behavior and its rule of not modifying `config.toml`;
- verify current OpenAI model identifiers/effort support before changing compatibility claims;
- add/update `tests/cases.json` when routing behavior changes;
- run `python -m unittest discover -s tests -v` and `python scripts/doctor.py --source-tree .`;
- do not fabricate token/latency improvements; label unmeasured expectations as such;
- avoid unrelated repository-wide formatting changes.
