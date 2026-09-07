<div align="center">

# Codex Efficiency Router

**面向 OpenAI Codex 的质量门控模型路由 Skill：只有真正需要最高级推理时才使用 GPT‑6 Astra，决策完成后立即降级到 GPT‑5.6 Sol / Terra / Luna 执行。**

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GPT-6 Astra](https://img.shields.io/badge/GPT--6-Astra-111111)](https://developers.openai.com/api/docs/models/gpt-6-astra)
[![Codex Skill](https://img.shields.io/badge/Codex-Skill-10a37f)](https://learn.chatgpt.com/zh-Hans/docs/build-skills)

[English](README.md) · **简体中文**

*把最高级推理花在“不确定性”上，而不是花在机械施工上。*

</div>

---

## 目标

GPT‑6 Astra 适合最困难的端到端工作，但如果一个任务的架构、根因和实施方案已经确定，后续仍然让 Astra 长时间执行批量改代码、编译、测试、迁移和清理，会产生没有必要的高模型 token 与延迟。

反过来，如果为了省 token 把所有任务都丢给低成本模型，也可能因为误判、返工和多轮失败导致**总 token 更高、总时间更长、质量下降**。

这个项目采用的目标是：

> **在“验证后的任务质量不主动下降”这一硬约束下，尽量降低昂贵模型 token 和端到端执行时间。**

路由依据不是“文件多不多、任务长不长”，而是**更强推理的边际价值**：

- 当前不确定性是否能通过更强推理被真正降低；
- 错误决策的影响面、可逆性和返工成本；
- 耦合深度和决策影响的时间跨度；
- 是否能用便宜、确定性的证据直接证伪；
- 是否属于缺少成熟先例的全新机制；
- 多组可信证据/分析是否互相冲突；
- 是否已经出现经过正确分类的 Sol 能力失败。

## 四层模型梯度

| 层级 | 默认配置 | 主要用途 |
|---|---|---|
| L0 | GPT‑5.6 Luna / medium | 机械、重复、范围窄、强可验证任务 |
| L1 | GPT‑5.6 Terra / medium | 默认 Coding Executor，方案已明确的正常实现 |
| L2 | GPT‑5.6 Sol / medium | 复杂排查、跨模块推理、困难集成/Review |
| L3 | GPT‑6 Astra / high | 承诺边界、重大歧义、证据仲裁、全新机制、昂贵迁移策略、已证实的 Sol 能力不足 |

**Astra `max` 永不自动触发。**

## 最核心的机制：强制降级

```text
关键决策仍有实质不确定性
      │
      ▼
 Sol / Astra
      │
关键决策已经收敛
      │
      ▼
Execution Contract
      │
      ▼
强制降级
      │
      ▼
Terra / Luna
      │
编码 / 测试 / 构建 / 批量修改
      │
      ▼
最便宜但足够有效的验证
```

**Astra 用在“更强推理确实具有高边际价值”的少数关键决策上，不是默认施工队。**

## 为什么它同时针对 Token、速度和质量

- **没有额外 Router 模型调用**：当前 coordinator 直接按规则判断，避免先烧一轮 token 才决定用哪个模型。
- **默认单 Agent**：只有切模型的收益明显大于子 Agent 启动、上下文复制和汇总成本时才 spawn。
- **先并行 Tool，再并行模型**：独立文件读取、搜索、元数据查询、隔离测试优先直接并行，不复制额外模型上下文。
- **决策收敛立即降级**：Astra/Sol 不长期承担确定性的 coding。
- **紧凑 handoff**：只传 Execution Contract / Escalation Packet，不复制完整探索历史。
- **有界升级**：普通实现错误由执行模型自己修；连续、无法解释的实质性失败才升一级。
- **证据驱动优化**：性能、内存、稳定性优化必须先测量，不允许凭猜测直接改代码。
- **验证是质量门**：如果省 token 导致验收失败、返工增加，就不算优化成功。

## 快速安装

### 直接让 Codex 安装

```text
从 https://github.com/fgokey/codex-efficiency-router
安装 `codex-efficiency-router` Skill，并验证安装结果。
不要覆盖与该 Skill 无关的 Codex 配置。
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

默认安装器**不会修改 `config.toml`**。

项目级安装、dry-run、可选默认 subagent 配置和卸载方式见 [docs/INSTALL.md](docs/INSTALL.md)。

## 使用

显式调用：

```text
$codex-efficiency-router 完整分析并实现这个任务
```

典型流程：

```text
任务：重新设计一个长期公共契约，并完成最终实现

1. Sol 先整理需求、约束、兼容性义务和已有证据。
2. 仍存在多个可行方案，而且这是一个昂贵、难回滚的承诺边界。
3. 升级 Astra/high，只负责比较方案并冻结关键决策。
4. Astra 输出紧凑 Execution Contract 后停止。
5. Terra 按冻结方案实现。
6. 机械迁移、固定检查矩阵等工作交给 Luna。
7. 验证通过后结束，不把 Astra 当作仪式性的 Final Reviewer。
```

常用覆盖指令：

```text
$codex-efficiency-router 自动路由这个任务
$codex-efficiency-router 尽量省 token，但不能降低质量门槛
$codex-efficiency-router 不要使用 subagent
$codex-efficiency-router 架构决策使用 Astra，确定后降级执行
```

## 项目结构

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
├── tests/
├── config/optional-defaults.toml
├── docs/
└── .github/
```

## 设计文档

- [架构设计](docs/ARCHITECTURE.md)
- [路由决策树](docs/ROUTING.md)
- [Token 与延迟优化](docs/TOKEN-EFFICIENCY.md)
- [质量门控](docs/QUALITY-GATES.md)
- [Benchmark 方法](docs/BENCHMARKING.md)
- [兼容性](docs/COMPATIBILITY.md)
- [安装方式](docs/INSTALL.md)

## 兼容性

v0.1.0 于 **2026-09-07** 按 OpenAI 当前公开文档核对：

- `gpt-6-astra`
- `gpt-5.6-sol`
- `gpt-5.6-terra`
- `gpt-5.6-luna`

OpenAI 当前文档将 GPT‑6 Astra 定位为最困难端到端任务的最高能力模型，并支持 `low / medium / high / xhigh / max` reasoning effort；Codex 自定义 agent 支持独立设置 `model` 和 `model_reasoning_effort`。来源见 [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md)。

> 本项目是独立社区项目，与 OpenAI 无隶属、合作或官方背书关系。

## 安装安全性

默认安装器只会：

- 安装本项目 Skill；
- 安装 4 个本项目具名 agent；
- 更新前备份本项目已有安装文件；
- 保留其他自定义 Agent 和 Skill；
- 不修改 `config.toml`；
- 不读取 API Key / Token；
- 不改 Git remote；
- 不自动 commit / push / deploy / upload。

可以先执行 `--dry-run`。

## 开发与验证

仅要求 Python 3.11+，无第三方运行时依赖：

```bash
python -m unittest discover -s tests -v
python scripts/doctor.py --source-tree .
```

`tests/cases.json` 是路由规则回归用例，不代表模型质量 Benchmark。

## 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。涉及模型选择、token/延迟优化的修改，建议提供可复现数据或至少补充 routing regression case。

## License

MIT，见 [LICENSE](LICENSE)。
