# Installation

## Requirements

- OpenAI Codex version that supports local Skills and custom agents;
- Python 3.11+ for the installer/doctor scripts;
- access to the model lanes you intend to use.

The Skill still works when some models are unavailable, but routing must fall back to an available sufficient model rather than silently claiming a unavailable lane.

## User-wide install

### Windows PowerShell

```powershell
git clone https://github.com/fgokey/codex-efficiency-router.git
cd codex-efficiency-router
.\install.ps1 --scope user
python .\scripts\doctor.py --scope user
```

### macOS / Linux

```bash
git clone https://github.com/fgokey/codex-efficiency-router.git
cd codex-efficiency-router
./install.sh --scope user
python3 scripts/doctor.py --scope user
```

User Skill target: `$HOME/.agents/skills/codex-efficiency-router`.
User agent target: `$CODEX_HOME/agents` (defaults to `~/.codex/agents`).

## Repository-scoped install

Run from the target repository root:

```powershell
.\install.ps1 --scope project --project-root C:\path\to\repo
```

or:

```bash
./install.sh --scope project --project-root /path/to/repo
```

Repository Skill target: `.agents/skills/codex-efficiency-router`.
Repository agents target: `.codex/agents`.

## Preview

Add `--dry-run` to either installer.

## Optional Codex defaults

The default install deliberately does **not** edit `config.toml`.

If you want unnamed child agents to default to Terra/medium, manually review and merge `config/optional-defaults.toml` into your existing Codex config. Preserve all unrelated settings.

## Use

Start a new Codex session if discovery has not refreshed, then invoke:

```text
$codex-efficiency-router implement this change end to end
```

The Skill may also trigger automatically on substantial repository tasks when its description matches.

Useful overrides:

```text
$codex-efficiency-router auto route this task
$codex-efficiency-router save tokens but keep the quality gate
$codex-efficiency-router no subagents; do this in the current agent
$codex-efficiency-router use Astra for the architecture decision, then downgrade for implementation
```

## Uninstall

Windows:

```powershell
.\uninstall.ps1 --scope user
```

macOS/Linux:

```bash
./uninstall.sh --scope user
```

The uninstaller removes only files owned by this project. Existing unrelated Skills, custom agents, and `config.toml` remain untouched.
