# Contributing

Use Python 3.11+ and standard-library code. Keep the runtime Skill small; put detailed explanations in references or documentation, not every turn's context. Do not add a daemon, classifier call or mandatory ledger without measured evidence that its benefit exceeds overhead.

Before a change, state the failure case or measurable objective. Preserve explicit user constraints, required verification, current configuration, ownership boundaries and honest unknown states. Do not treat more agents, higher effort, or shorter prompts as improvements by themselves.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/doctor.py --source-tree .
python3 -m compileall -q scripts tests
git diff --check
```

Add regression and negative cases for routing changes. Keep Skill text, role presets, `scripts/package.py`, policy metadata and docs consistent. Test user and project scope, CRLF migration, customized files, unowned collisions, dry-run, rollback and recovery when changing lifecycle code. Legacy fixtures are immutable historical input, not runtime payload.

For model/effort changes, cite current official docs and supply workload-specific paired evaluation data where possible. Offline unit tests are not a live model-quality benchmark. Do not publish secrets, prompts, project backups or private code in evidence files. Report missing measurements as unknown.

Update both READMEs when installation or removal changes. Describe compatibility, validation and remaining risks in the PR template. Keep source links and review dates in [prior art](docs/PRIOR-ART.md), and summarize user-facing changes in [CHANGELOG](CHANGELOG.md).

Contributions are under the repository's [MIT License](LICENSE) and [Code of Conduct](CODE_OF_CONDUCT.md).
