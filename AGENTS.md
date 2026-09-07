# Repository work instructions

This repository implements a quality-gated policy, not a model-switching API. Preserve that distinction. Prefer the smallest evidence-supported improvement; do not add mandatory model calls, nested Codex processes or runtime ledgers.

Keep the core Skill and its packaged references self-contained. Model/effort presets must match `scripts/package.py`, TOML roles and policy metadata. Never claim live host compatibility or actual savings from static tests. Legacy fixtures are test data only.

Before completion run the unittest suite, source doctor, Python compileall, and `git diff --check`. Add negative cases for new boundaries. For lifecycle changes test dry-run, unowned collisions, customization preservation, migration, rollback and uninstall/restore. Never test against a real user's config when temporary directories suffice.

Update English and Chinese READMEs for installation/removal changes and keep links valid. Do not weaken acceptance to obtain green tests. Do not publish credentials, private prompts or installation backups.
