# Security

This package is an independent local Skill/configuration project, not a security boundary or an OpenAI product. Review changes before installing and run it without administrator privileges in a trusted, quiescent directory.

The installer has no network access logic, does not read credentials, and does not change Codex permissions, providers, MCP settings, authentication, `config.toml` or unrelated agents. Ownership manifests and checksums prevent accidental overwrite/removal of unrelated or locally edited content. `--force` only affects owned files after backup; it cannot claim an unrelated filename. Legacy adoption verifies known published content.

Managed targets reject path traversal, symlinks and Windows junction/reparse points. Locks protect against this installer's concurrent commands sharing a backup location. This does not defend against malicious local filesystem races or a tampered trusted manifest. Per-file replacement is atomic, not a power-loss-atomic multi-file transaction. Retain backups and inspect interrupted operations.

Backups can contain private custom instructions. Keep them local, out of Git and bug reports. Restore verifies checksums, package identity and original target paths, and refuses intervening modifications by default.

The Astra role is read-only in both configuration and instructions. Host permissions can take precedence over role defaults; instructions alone do not enforce a sandbox. Workers must not spawn agents, publish, deploy, or alter authorization. User intent and host policy remain authoritative.

Report security concerns privately through GitHub's private vulnerability reporting **when enabled**. Otherwise contact the maintainer through an available private channel before disclosing exploit details. Do not include secrets or real private prompts in public issues. See [support](SUPPORT.md).
