<div align="center">

# Codex Efficiency Router

**Quality-gated model routing for OpenAI Codex — use GPT-6 Astra only when the decision truly needs it, then de-escalate execution to GPT-5.6 Sol, Terra, or Luna.**

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/fgokey/codex-efficiency-router/actions/workflows/validate.yml/badge.svg)](https://github.com/fgokey/codex-efficiency-router/actions/workflows/validate.yml)
[![GPT-6 Astra](https://img.shields.io/badge/GPT--6-Astra-111111)](https://developers.openai.com/api/docs/models/gpt-6-astra)
[![Codex Skill](https://img.shields.io/badge/Codex-Skill-10a37f)](https://learn.chatgpt.com/zh-Hans/docs/build-skills)

**English** · [简体中文](README.zh-CN.md)

*Spend frontier reasoning on uncertainty, not on typing.*

</div>

---

## Why

GPT-6 Astra is OpenAI's most capable model for the hardest end-to-end work, but running the strongest model through every deterministic coding, build, test, migration, and cleanup step can waste expensive reasoning tokens and increase latency.

The opposite extreme—routing everything to a cheap model—can also be inefficient when it creates failed loops, rework, or missed correctness issues.

`codex-efficiency-router` uses a different objective:

> **Minimize expensive-model tokens and wall-clock time subject to a verified-quality constraint.**

The Skill routes by the **marginal value of stronger reasoning**: reducible uncertainty, failure cost/reversibility, coupling, verifiability, novelty, evidence conflict, and qualified prior failure — never by file count or task length alone.

## Model ladder

| Lane | Default preset | Use for |
|---|---|---|
| L0 | GPT-5.6 Luna / medium | Mechanical, repetitive, narrow, strongly verifiable work |
| L1 | GPT-5.6 Terra / medium | Default bounded coding executor |
| L2 | GPT-5.6 Sol / medium | Complex debugging, cross-module reasoning, difficult integration/review |
| L3 | GPT-6 Astra / high | Exceptional reasoning: commitment boundaries, consequential ambiguity, evidence arbitration, novel design, costly migration strategy, proven Sol capability failure |

Astra `max` is **never automatic**.

## The key transition

```text
material unresolved decision
            |
            v
       Sol or Astra
            |
       decision frozen
            |
            v
     Execution Contract
            |
       de-escalate
            v
    Terra or Luna
            |
      code / tests / build
            |
            v
     cheapest valid verification
```

Astra is a reasoning resource for the few decisions where additional intelligence has high marginal value, not the default construction crew.

## What makes this router efficient

- **No router LLM call.** The current coordinator makes one cheap policy decision from existing context.
- **One agent by default.** A child agent is created only when model-switch benefit clearly exceeds context/startup/aggregation overhead.
- **Tool concurrency before model concurrency.** Parallelize safe reads/searches/checks without multiplying model contexts.
- **Mandatory de-escalation.** As soon as the hard decision is resolved, deterministic work goes back to Terra/Luna.
- **Compact handoffs.** Pass a frozen decision/execution contract, not the entire exploration transcript.
- **Bounded escalation.** Ordinary implementation mistakes stay with the executor; unexplained repeated failures move up one lane.
- **Evidence-driven optimization.** Performance/memory/stability changes require measurement, not speculative edits.
- **Verification is the quality gate.** Token savings do not count when acceptance fails or human repair increases.

## Quick start

### Ask Codex to install it

```text
Install the `codex-efficiency-router` Skill from
https://github.com/fgokey/codex-efficiency-router
and validate the installation. Do not overwrite unrelated Codex settings.
```

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

The default installer **does not modify `config.toml`**.

See [docs/INSTALL.md](docs/INSTALL.md) for repository-scoped install, dry-run, optional defaults, and uninstall.

## Use

Explicit invocation:

```text
$codex-efficiency-router implement this change end to end
```

Typical behavior:

```text
Task: redesign a long-lived public contract and implement the selected option

1. Sol maps requirements, constraints, compatibility obligations, and evidence.
2. Several viable designs remain; the choice is a costly-to-reverse commitment boundary.
3. Astra/high compares the tradeoffs and freezes the decision.
4. Astra emits a compact Execution Contract and stops.
5. Terra implements the approved design.
6. Luna handles mechanical migrations/check matrices where appropriate.
7. Focused verification passes; Astra is not added as a ceremonial final reviewer.
```

Useful overrides:

```text
$codex-efficiency-router auto route this task
$codex-efficiency-router save tokens but keep the quality gate
$codex-efficiency-router no subagents
$codex-efficiency-router use Astra for the architecture decision, then downgrade
```

## Repository layout

```text
codex-efficiency-router/
├── skills/codex-efficiency-router/SKILL.md
├── agents/
│   ├── astra-architect.toml
│   ├── sol-engineer.toml
│   ├── terra-executor.toml
│   └── luna-worker.toml
├── policy/routing-policy.json
├── scripts/
│   ├── install.py
│   ├── uninstall.py
│   ├── doctor.py
│   └── policy_reference.py
├── tests/
├── config/optional-defaults.toml
├── docs/
└── .github/
```

## Design docs

- [Architecture](docs/ARCHITECTURE.md)
- [Routing decision tree](docs/ROUTING.md)
- [Token and latency efficiency](docs/TOKEN-EFFICIENCY.md)
- [Quality gates](docs/QUALITY-GATES.md)
- [Benchmarking methodology](docs/BENCHMARKING.md)
- [Compatibility](docs/COMPATIBILITY.md)
- [Installation](docs/INSTALL.md)

## Compatibility

v0.1.0 was checked against OpenAI documentation on **2026-09-07**.

Expected model identifiers:

- `gpt-6-astra`
- `gpt-5.6-sol`
- `gpt-5.6-terra`
- `gpt-5.6-luna`

OpenAI currently documents GPT-6 Astra as the highest-capability model for the hardest end-to-end work and lists `low`, `medium`, `high`, `xhigh`, and `max` reasoning efforts. Codex custom agents support per-agent `model` and `model_reasoning_effort` settings. See [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) for source links.

> This is an independent community project. It is not created by, affiliated with, or endorsed by OpenAI.

## Safety of installation

The default installer:

- copies only this Skill and its four named agent files;
- backs up previously installed files owned by this project;
- preserves unrelated custom agents;
- does not edit `config.toml`;
- does not read API keys or auth tokens;
- does not change Git remotes;
- does not commit, push, deploy, or upload code.

Run a preview first with `--dry-run` if desired.

## Development

Python 3.11+; no third-party runtime dependencies.

```bash
python -m unittest discover -s tests -v
python scripts/doctor.py --source-tree .
```

The synthetic route cases test policy consistency only; they are not a model-quality benchmark.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Routing and efficiency changes should include reproducible evidence or regression cases where practical.

## Security

See [SECURITY.md](SECURITY.md). Do not post credentials, private source code, proprietary logs, or sensitive configuration in public issues.

## License

MIT — see [LICENSE](LICENSE).
