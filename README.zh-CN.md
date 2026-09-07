# Codex Efficiency Router

[English](README.md) · [架构设计](docs/ARCHITECTURE.md) · [本次体检报告](docs/AUDIT-2026-09-07.md) · [官方资料与业界经验](docs/PRIOR-ART.md)

面向 Codex 的轻量模型路由 Skill：把 GPT-6 Astra 用在真正需要强推理的未决问题上；方案确定后，仅在收益足够时，把有边界的实现交给合适模型。

**v0.2.0 · MIT · Python 3.11+ · Windows / macOS / Linux**

这是独立社区项目，并非 OpenAI 官方产品。目标是在保留必要验收的前提下，减少无效 token、交接与等待；不承诺所有任务都省 token、都变快或质量绝对不变。路由回归测试不是实际模型编码能力评测。

## 工作方式

```text
当前主控：保留你选定的模型
  ├─ 当前能力足够、任务很小或主要是工具操作 → 直接完成
  ├─ 安全、互不依赖的工具操作              → 有界并发
  └─ 能力确有需要或收益足以覆盖交接成本    → 一个有边界的子 Agent
       Luna  → 低风险、机械、容易验证的工作
       Terra → 方案明确后的正常开发
       Sol   → 复杂集成、未决问题、较难 Review
       Astra → 极难或高后果的未决推理，只读决策支持
                    ↓ 决策完成
           重新判断剩余工作；值得交接才降级，不为短尾任务强行开 Agent
```

没有额外 Router 模型调用、常驻服务、每轮强制记账，也没有固定的 Planner→Worker→Reviewer 套娃。不会自动使用 `max`，不会暗中启动第二个 Codex 进程或修改主线程模型。

| 角色 | 模型 | 默认推理档位 |
| --- | --- | --- |
| `luna_worker` | `gpt-5.6-luna` | `medium` |
| `terra_executor` | `gpt-5.6-terra` | `medium` |
| `sol_engineer` | `gpt-5.6-sol` | `medium` |
| `astra_architect` | `gpt-6-astra` | `high` |

模型标识和配置方式已按 **2026-09-07** 的官方资料核对；你的账号目录、Codex 宿主能力、权限和实际执行元数据才决定是否可用。自定义 Agent 文件中的模型及档位可能优先于 spawn 参数，不能把“请求 Astra”当作“实际运行 Astra”。详见[兼容性说明](docs/COMPATIBILITY.md)。

## 安装

前提：Git、**Python 3.11 或更新版本**，以及支持本地 Skills 和自定义 agents 的 Codex。克隆后安装器不联网、不读取密钥、不改认证。

### Windows / PowerShell

```powershell
git clone https://github.com/fgokey/codex-efficiency-router.git
cd codex-efficiency-router
py -3 scripts/install.py --scope user --dry-run
py -3 scripts/install.py --scope user
py -3 scripts/doctor.py --scope user
```

使用 `python` 命令管理 Python 3.11+ 的环境，可把 `py -3` 换成 `python`。直接运行 Python 不需要修改 PowerShell 执行策略。

### macOS / Linux

```sh
git clone https://github.com/fgokey/codex-efficiency-router.git
cd codex-efficiency-router
python3 scripts/install.py --scope user --dry-run
python3 scripts/install.py --scope user
python3 scripts/doctor.py --scope user
```

也可使用 `sh install.sh --scope user`；不依赖脚本预先带有可执行权限。

### 仅安装到某个项目

建议用户级和项目级**二选一**，避免同时加载同名 Skill。从本仓库目录运行，并替换为实际存在的项目目录：

```powershell
py -3 scripts/install.py --scope project --project-root "C:/Work/my-project" --dry-run
py -3 scripts/install.py --scope project --project-root "C:/Work/my-project"
py -3 scripts/doctor.py --scope project --project-root "C:/Work/my-project"
```

macOS/Linux 把 `py -3` 换成 `python3`，并使用实际绝对路径。项目配置是否加载仍受 Codex 信任与管理员策略约束。

| 范围 | Skill 路径 | 四个 Agent 配置 | 备份 |
| --- | --- | --- | --- |
| 用户级 | `~/.agents/skills/codex-efficiency-router/` | `$CODEX_HOME/agents/`，未设置时为 `~/.codex/agents/` | `$CODEX_HOME/backups/codex-efficiency-router/` |
| 项目级 | `<项目>/.agents/skills/codex-efficiency-router/` | `<项目>/.codex/agents/` | `<项目>/.codex-router-local/backups/` |

安装器不修改 `config.toml`、`AGENTS.md`、MCP、provider、权限和其他 Skill/Agent。遇到不属于本项目的同名文件会拒绝覆盖；安装清单记录受管理文件的哈希，升级和卸载先检查用户改动。

`doctor` 的 **STATIC PASS** 仅代表静态检查通过，同时会显示 **live model execution: NOT VERIFIED**，不会偷偷调用模型。新 Skill 或角色没有出现时，重新加载或重启 Codex。只让其他 Skill 安装器复制 `SKILL.md` 不会部署四个角色，完整安装应使用本仓库脚本。

## 使用

```text
$codex-efficiency-router
完成当前任务，保留必要验收与已有设计约束。
普通实现使用足够的模型，重大未决推理才升级 Astra，避免无收益的子 Agent 和重复验证。
```

已启用相关工程任务的隐式触发，但显式写 `$codex-efficiency-router` 更直接。可明确要求“不要子 Agent”“不要升级”“本次禁用路由”；这些约束不等于当前模型一定够用。不要在同一任务叠加多个 Router。

首次使用可安排一个小型**只读**子任务，通过宿主或会话元数据检查实际角色、模型、推理档位与结果。模型自述不是验证证据。安装成功、目录检查成功，也不代表实际多模型委派已经成功。

## 更新及 v0.1.0 迁移

```powershell
git pull --ff-only
# 已有 v0.2+ 安装清单：
py -3 scripts/install.py --scope user --dry-run
py -3 scripts/install.py --scope user
# 仅限原始 v0.1.0、尚无安装清单的旧安装：
py -3 scripts/install.py --scope user --adopt-v01 --dry-run
py -3 scripts/install.py --scope user --adopt-v01
```

两组是不同升级路径，不需要全执行。macOS/Linux 使用 `python3`；项目级安装沿用原来的 `--scope project --project-root ...`。

旧版迁移只认已发布 v0.1.0 的已知内容，兼容 CRLF 换行。未知或已修改的旧文件会保留，需先人工核对。`--force` 也不能把无关同名文件强行认领。相同版本未发生变化时，重装不重复写入或制造备份。

## 卸载

在保留的本仓库克隆目录中执行，**scope、项目路径及 CODEX_HOME 必须与安装时一致**。不要用旧 v0.1.0 的卸载器处理定制过的配置。

### Windows / PowerShell

```powershell
py -3 scripts/uninstall.py --scope user --dry-run
py -3 scripts/uninstall.py --scope user
# 项目级安装则改用：
py -3 scripts/uninstall.py --scope project --project-root "C:/Work/my-project"
```

### macOS / Linux

```sh
python3 scripts/uninstall.py --scope user --dry-run
python3 scripts/uninstall.py --scope user
# 项目级安装则改用：
python3 scripts/uninstall.py --scope project --project-root "/path/to/my-project"
```

只删除安装清单确认属于本项目的文件。保留其他 Skill/Agent、现有配置、未跟踪文件及备份；发现用户修改过的受管理文件时，默认停止。确认内容并保留需要的定制后，可追加 `--force`：先备份，再删除受管理文件，不进行全目录清理。旧版安装须先通过 `--adopt-v01` 迁移。

卸载后重新加载 Codex；当前已加载的对话仍可能带有旧指令。备份可能含私人配置，确认不再需要后再自行清理，不要公开上传。

### 回滚安装或恢复卸载

使用脚本实际打印的备份目录，不要照抄一个不存在的时间戳：

```powershell
py -3 scripts/install.py --scope user --restore "C:/Users/you/.codex/backups/codex-efficiency-router/ACTUAL-BACKUP" --dry-run
py -3 scripts/install.py --scope user --restore "C:/Users/you/.codex/backups/codex-efficiency-router/ACTUAL-BACKUP"
```

macOS/Linux 改用 `python3` 和实际备份路径；项目级补上原安装范围。恢复会检查原目标、备份完整性和之后发生的本地改动，避免回滚覆盖新工作。恢复操作自身也保留备份。

用户手工合并到 `config.toml` 的[可选默认值](config/optional-defaults.toml)不会自动移除，卸载后需按实际需要自行保留或删除。[完整安装与恢复说明](docs/INSTALL.md)包含故障处理和安全边界。

## 验证与效果评估

```sh
python3 -m unittest discover -s tests -v
python3 scripts/doctor.py --source-tree .
python3 -m compileall -q scripts tests
# 可选：比较自己采集的完整任务配对数据，不调用 API
python3 scripts/compare_runs.py runs.json
```

测试覆盖路由边界、真正委派的准入条件、安装/升级/卸载/恢复、包完整性及统计结果的诚实表达。CI 配置包含 Windows、macOS、Linux，哪些平台实际通过应以对应提交的 Actions 结果为准。

v0.2.0 通过按需加载参考资料缩小核心 Skill，而不是删除验收规则。体检报告中的压缩量是**指令字节数**，不是实测任务总 token 节省率。目前不声称已完成 Astra/Terra/Sol/Luna 实际编码质量、token 或耗时对照实验。[评估方案](docs/BENCHMARKING.md)说明了如何进行同任务、多次试验、全链路计费和耗时比较。

## 项目资料

[架构](docs/ARCHITECTURE.md) · [路由](docs/ROUTING.md) · [Astra 升级](docs/ASTRA-ESCALATION.md) · [Token 与耗时](docs/TOKEN-EFFICIENCY.md) · [质量门](docs/QUALITY-GATES.md) · [兼容性](docs/COMPATIBILITY.md) · [体检报告](docs/AUDIT-2026-09-07.md) · [参考资料](docs/PRIOR-ART.md)

[贡献指南](CONTRIBUTING.md) · [安全](SECURITY.md) · [支持](SUPPORT.md) · [行为准则](CODE_OF_CONDUCT.md) · [更新记录](CHANGELOG.md) · [MIT 许可](LICENSE)
