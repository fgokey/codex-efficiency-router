# Codex Efficiency Router

[English](README.md) · [架构](docs/ARCHITECTURE.md) · [质量协议](docs/QUALITY-PROTOCOL.md) · [实装验收](docs/ACCEPTANCE.md)

**v0.4.0 · 仅面向 Codex 的 Skill · MIT · Python 3.11+ · Windows / macOS / Linux**

强模型解决关键未决问题，明确施工交给足够的模型，只有收益值得才委派。质量和授权是约束。本项目不是 OpenAI 官方产品，不承诺任意任务都质量不变、token 更少或速度更快。

## Codex 内如何工作

当前主控读取精简 Skill，使用 Codex 原生子 Agent。不会切换主线程模型，不启动第二个 CLI/API 会话，不安装其他 Agent 平台，不额外调用分类模型。小任务直接做；先使用安全独立的工具并发，再考虑新模型上下文。默认一个执行者，多人并行需要独立验收、不冲突的写入范围和明确收益。

| 角色 | 模型 | 固定模式档位 |
| --- | --- | --- |
| `luna_worker` | `gpt-5.6-luna` | `medium` |
| `terra_executor` | `gpt-5.6-terra` | `medium` |
| `sol_engineer` | `gpt-5.6-sol` | `medium` |
| `astra_architect` | `gpt-6-astra` | `high` |

只有四个预设，不强制逐档尝试，不自动 `max`。Astra 提供只读决策支持；结论确定后重新评估剩余工作，不为短尾工作机械创建 Agent。相同模型及相同档位的委派必须有具体上下文价值和净收益。需求、权限、环境和证据缺失，先补前置条件。

实际可用性由 Codex 宿主和账号决定。角色文件中的固定设置优先于 spawn 参数；请求身份不等于实际身份，无运行时证据则为 UNKNOWN。[兼容性说明](docs/COMPATIBILITY.md)。

## v0.3 质量改进

执行者动手前检查需求完整性、方案冲突、关键假设和当前状态；高级模型的方案也不能覆盖用户要求。完成时逐项对应要求与当前证据，返回 **PASS / PARTIAL / BLOCKED**；披露遗漏不等于豁免要求。需求符合性和实现质量在一次有边界的检查中处理，不固定增加审核 Agent。

重试历史属于任务/工作单元/失败特征，跨模型、跨执行者、上下文压缩后仍保留。仅长任务或恢复时使用一个允许写入的任务级检查点；续接先核对文件、活跃执行者和可能发生过的副作用，不能重做已完成工作。四份短参考按需读取，整体文本预算包括全部参考和单个角色指令。

Python 质量辅助函数与验收用例是**离线开发工具**，不安装进运行时 Skill、不每轮执行，也不是强制执行器、安全边界或模型质量证明。[设计与借鉴来源](docs/QUALITY-PROTOCOL.md) · [本次验证](docs/VALIDATION-v0.4.0.md)。

## 自适应思考档位（v0.4）

仍是四个角色；父 Agent 在有意义的任务边界联合选择**模型＋思考档位**。新安装默认 **fixed 固定模式**以兼容旧宿主；更新保留原模式和 low 开关，不悄悄切换。在 **adaptive 自适应模式**中，角色模型及权限约束不变，但不再固定思考档位，父代理必须通过宿主真实工具参数明确传入。不是所有 Codex 宿主都保证开放该能力。

在保留的仓库目录中，明确启用自适应模式：

```powershell
git pull --ff-only
py -3 scripts/install.py --scope user --mode adaptive --dry-run
py -3 scripts/install.py --scope user --mode adaptive
py -3 scripts/doctor.py --scope user
```

macOS/Linux 使用 `python3`；项目级沿用 `--scope project --project-root ...`。更新后重新加载 Codex，避免旧对话指令或旧角色覆盖新配置。只安装一套四个角色，不改变认证、全局配置和主线程模型。

普通实现默认 medium；深层逻辑、假设和边界分析可选同模型 high，能力不足则重新选模型，不强制逐档试错。Astra 自动使用 high。自动 low **默认关闭**，只允许显式开启后的严格机械 Luna 任务；xhigh/max 仅用户明确要求且宿主支持时使用。“不要升级”同时禁止升模型和升档位；“模型不变”可单独允许调档。运行中的回合不强行热切换，换档不重置任务重试预算。

```powershell
# 可选：严格限定的自动 low；首次验收建议暂不启用
py -3 scripts/install.py --scope user --mode adaptive --allow-low
# 关闭自动 low，保留 adaptive
py -3 scripts/install.py --scope user --no-allow-low
# 回退到固定档位兼容模式
py -3 scripts/install.py --scope user --mode fixed
```

固定角色文件会覆盖矛盾的请求；自适应必须确认已加载角色未固定档位、工具能传档位。档位不支持或配置不符时不静默降级，不把“请求 high”当“实际 high”。UNKNOWN/MISMATCH 停止该任务后续自动 low。`doctor` 只证明静态安装和模式一致性，不证明模型实际执行。[设计和配置优先级](docs/ADAPTIVE-EFFORT.md) · [实装验收](docs/ACCEPTANCE.md)。

## 安装

需要 Git、**Python 3.11+**。克隆后安装离线执行，不改 `config.toml`、`AGENTS.md`、认证、provider、权限或其他 Skill/Agent。先审查文件，保留克隆目录用于更新卸载。

### Windows / PowerShell

```powershell
git clone https://github.com/fgokey/codex-efficiency-router.git
cd codex-efficiency-router
py -3 scripts/install.py --scope user --dry-run
py -3 scripts/install.py --scope user
py -3 scripts/doctor.py --scope user
```

环境使用 `python` 时可替换 `py -3`，确保版本正确。直接 Python 不需要修改 PowerShell 执行策略。PowerShell 包装脚本透传 `--scope`、`--dry-run`，不是 `-Scope`、`-DryRun` 别名。

### macOS / Linux

```sh
git clone https://github.com/fgokey/codex-efficiency-router.git
cd codex-efficiency-router
python3 scripts/install.py --scope user --dry-run
python3 scripts/install.py --scope user
python3 scripts/doctor.py --scope user
```

也可使用 `sh install.sh --scope user` 或 `sh uninstall.sh --scope user`，不依赖可执行位。

### 仅安装到项目

用户级/项目级二选一，避免同名 Skill 重复。替换为实际存在的项目路径：

```powershell
py -3 scripts/install.py --scope project --project-root "C:/Work/my-project" --dry-run
py -3 scripts/install.py --scope project --project-root "C:/Work/my-project"
py -3 scripts/doctor.py --scope project --project-root "C:/Work/my-project"
```

macOS/Linux 用 `python3` 和实际绝对路径。项目配置仍受 Codex 信任与管理员策略限制。

| 范围 | Skill | 四个角色文件 | 备份 |
| --- | --- | --- | --- |
| 用户级 | `~/.agents/skills/codex-efficiency-router/` | `$CODEX_HOME/agents/`，默认 `~/.codex/agents/` | `$CODEX_HOME/backups/codex-efficiency-router/` |
| 项目级 | `<项目>/.agents/skills/codex-efficiency-router/` | `<项目>/.codex/agents/` | `<项目>/.codex-router-local/backups/` |

安装清单只管理本项目文件。无关同名文件拒绝覆盖；本地定制文件先核对，不直接 `--force`。仅复制 Skill 的第三方安装器不会部署四个角色，完整使用应运行本仓库安装器。`doctor: STATIC PASS` 不代表实际模型路由成功。加载未刷新时重新加载 Codex，已有长对话可能仍含旧指令。

## 使用

```text
$codex-efficiency-router
完成当前任务并保留必要验收。关键未决问题使用足够的推理能力，
避免无收益委派；逐项核对需求与实际证据，诚实报告未完成和阻塞项。
```

相关复杂工程任务支持隐式触发，显式调用更清楚。“禁用路由”“不要子 Agent”“不要升级”优先，但不代表当前能力一定足够。不要叠加多个 Router。主线程仍是你选择的模型。

## 更新

已有带安装清单的 v0.2+：

```powershell
git pull --ff-only
py -3 scripts/install.py --scope user --dry-run
py -3 scripts/install.py --scope user
py -3 scripts/doctor.py --scope user
```

macOS/Linux 用 `python3`；项目级沿用原来的 scope/root。**只有原始 v0.1 无清单安装**需要为安装命令追加 `--adopt-v01`。迁移只认已知旧版内容及等价 CRLF，不认领任意定制文件。相同内容重装不重复写入。发现冲突先核对。

## 卸载

使用安装时相同的 scope、项目和 `CODEX_HOME`。不要用最初 v0.1 卸载器处理定制文件。

```powershell
# Windows 用户级
py -3 scripts/uninstall.py --scope user --dry-run
py -3 scripts/uninstall.py --scope user
# 项目级则改用
py -3 scripts/uninstall.py --scope project --project-root "C:/Work/my-project"
```

```sh
# macOS/Linux 用户级
python3 scripts/uninstall.py --scope user --dry-run
python3 scripts/uninstall.py --scope user
# 项目级则改用
python3 scripts/uninstall.py --scope project --project-root "/path/to/my-project"
```

只删除清单管理的文件。保留未跟踪文件、其他配置/Agent 和备份。本地修改默认阻止删除，确认后 `--force` 也只会先备份再处理受管理文件。旧版先迁移。默认卸载**不自动恢复旧版本**，没有 `--no-restore` 参数。

### 显式恢复

使用操作实际打印的备份目录：

```powershell
py -3 scripts/install.py --scope user --restore "ACTUAL-BACKUP-PATH" --dry-run
py -3 scripts/install.py --scope user --restore "ACTUAL-BACKUP-PATH"
```

macOS/Linux 用 `python3`；项目级补原来的范围。恢复校验原目标和校验和，默认拒绝覆盖之后的本地改动；恢复操作自身也备份。手动合并到 `config.toml` 的可选默认值不归安装器管理，不自动撤销。备份可能含私人指令，不要上传。[生命周期与恢复说明](docs/INSTALL.md)。

## 验证与效果边界

```sh
python3 -m unittest discover -s tests -v
python3 scripts/doctor.py --source-tree .
python3 -m compileall -q scripts tests evaluation
python3 evaluation/offline_audit.py --without-tokenizer
```

可选文本审计需要完整 Git 历史和 `tiktoken==0.11.0`，运行 `python3 evaluation/offline_audit.py`。初次依赖/词表下载联网，但不调用模型。CI 包含普通 Python 测试、选定的路由/质量变异，以及参考编码文本预算；通过情况以对应提交的结果为准。保留历史失败证据。

[20 个真实提示词验收场景](evaluation/behavior_cases.json)已准备，**CI 不执行模型任务**。结构检查不是实际回复评分。你实装时核对真实模型身份、需求覆盖、交接/恢复，以及父子线程与返工合计用量。[验收清单](docs/ACCEPTANCE.md) · [评估方法](docs/BENCHMARKING.md)。

`scripts/compare_runs.py runs.json` 比较配对数据；即使两组都失败而没有相对退化，Router 验收未完成也不能成功退出。缺失数据保持未知。退出码为零或文本变短，都不是质量无损或实际省额度证明。安装和 CI 不触发付费模型测试。

## 开源资料

[架构](docs/ARCHITECTURE.md) · [路由](docs/ROUTING.md) · [质量门](docs/QUALITY-GATES.md) · [Token](docs/TOKEN-EFFICIENCY.md) · [参考来源](docs/PRIOR-ART.md) · [更新记录](CHANGELOG.md)

[贡献指南](CONTRIBUTING.md) · [安全](SECURITY.md) · [支持](SUPPORT.md) · [行为准则](CODE_OF_CONDUCT.md) · [MIT 许可](LICENSE)
