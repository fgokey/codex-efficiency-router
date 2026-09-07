# Security Policy

## Supported versions

Security fixes are applied to the latest released minor version.

## What this project changes

The default installer copies only:

- the Skill into a Codex Skill discovery directory;
- the project's named agent presets into a Codex agent directory.

It does **not** modify `config.toml` by default, does not read credentials, does not change Git remotes, and does not commit or push user repositories.

## Reporting a vulnerability

Do not open a public issue for vulnerabilities that could expose credentials, execute unintended commands, overwrite unrelated Codex configuration, or escape the intended installation scope.

Contact the maintainer privately through the GitHub account associated with this repository. Include:

- affected version;
- operating system;
- reproduction steps;
- expected vs actual behavior;
- impact;
- a minimal sanitized proof of concept.

Do not include API keys, access tokens, private repository contents, or unrelated personal data.
