# Codex Efficiency Router

[English](README.md) · [本轮修复范围](docs/REPAIR-2026-10-22.md) · [实装验收](docs/ACCEPTANCE.md)

**v0.8.5 纠错更新 · 仅 Codex · MIT · Python 3.11+**

按子任务选择原生 Codex 执行者的模型和思考档位，明确写入范围和验收证据。严格执行路径下 Astra 只读分析，困难问题直接参与判断；实现交给适当执行者。默认一个实现者，必要时增加复核者，同一问题优先复用原负责人。

这是社区项目，不会切换父模型。安装成功、单测通过、指令文本变短，都不能直接证明实际质量、速度或套餐额度收益。

## Sol 只保留 6.1

Sol 路由只使用 **`gpt-6.1-sol`**。`gpt-6-sol` 和 `gpt-5.6-sol` 已从模型选择、显式指定、回退及任务准入中移除。新 Sol 任务使用 `cer_auto_sol61_engineer` 并明确选择思考档位；缺少 6.1 支持不会重新启用旧 Sol，也不会偷偷改写用户指定的模型。

为平滑升级，原有 `sol_engineer` / `cer_auto_sol_engineer` 文件名保留为兼容别名，但绑定同样是 6.1，不是另一款 Sol。普通重装会备份并更新未被修改的自有文件，发现用户定制则停止并提示。历史测试夹具和用量记录不是可选择模型。现有任务到安全边界后更新 Skill 及单独注册的 Guard，再重新加载 Codex，不在运行中热切换代理。

## 本轮解决的问题

Reader 和派发门禁共用模型/档位支持范围，Luna、Terra、Sol61 都有完整的任务准入路径。已知执行者的 medium/high 身份 HOLD 不再重复申请业务任务准入；实际身份核验与写入前 RELEASE 仍然必需。

同任务的精确 continue/status/stop 控制消息复用原有当前策略凭据和范围，不必重建子代理，也不授予新任务权限。夹带新工作、改变范围或身份仍拒绝。可选定制宿主必须使用 Reader 返回的 `admitted_dispatch_arguments`，显式传递接收者模型和档位，不能沿用默认 Sol61/high。

Windows 验证覆盖 UTF-8 BOM、原样 CRLF、包含中文和空格的 CODEX_HOME、PowerShell 7/5.1 启动器、错误解释器拒绝，以及安装、打包和卸载。是否通过以对应提交的 CI 为准，不以这段功能说明代替测试结果。

## 角色配置

| 角色 | 模型 | 固定档位 |
| --- | --- | --- |
| `luna_worker` | `gpt-6-luna` | `high` |
| `terra_executor` | `gpt-5.6-terra` | `medium` |
| `sol_engineer` | `gpt-6.1-sol` | `medium`（兼容名称） |
| `sol61_engineer` | `gpt-6.1-sol` | `high` |
| `astra_architect` | `gpt-6-astra` | `high` |

普通安装默认 `auto`：五个固定兼容入口加五个 `cer_auto_*` 自动入口，每项任务只选一个入口，并非启动十个代理。实际支持范围由宿主决定。自动 low 默认关闭。本次保留既有高档默认策略，先修通执行链路，不把模型调优与协议修复混在一起。

## 安装与更新

在仓库目录执行，保持与原安装相同的范围。先核对改动，正在执行的任务到安全边界后再更新。

```powershell
git switch main
git pull --ff-only
.\cer.ps1 install --scope user --dry-run
.\cer.ps1 install --scope user
.\cer.ps1 doctor --scope user --json
```

首次使用先克隆 `https://github.com/fgokey/codex-efficiency-router.git` 并进入目录。启动器实际检查 Python 3.11+，不下载 Python、不修改 PATH。指定已有解释器时，把 `$env:CER_PYTHON` 设置为真实 python.exe 完整路径；显式路径错误时直接失败，不偷偷换解释器。不需要为本项目全局关闭 PowerShell 执行策略。

macOS/Linux 使用 `python3 scripts/install.py --scope user --dry-run`，确认后去掉 `--dry-run`，再运行 `python3 scripts/doctor.py --scope user`。项目级使用 `--scope project --project-root` 和真实项目路径；不要双范围重复安装。保留仓库克隆以便卸载恢复。定制文件或同名非本项目文件发生冲突时先检查，不直接使用 `--force`。

更新后重新加载 Codex。验收时显式使用 `$codex-efficiency-router`；符合描述的复杂任务也允许自动发现。磁盘更新不代表旧长会话已经加载了新规则。

## 必须分清三层能力

**Skill/角色、可选写入/派发 Hook、实验性定制 Codex 宿主是三个独立层。** 普通安装不注册 Hook、不修改信任、不替换二进制。`policy-only` 只代表指令约束，不是运行时强制。doctor 静态通过不是实际 Canary 通过。

路由档位 `auto/fixed/adaptive` 与宿主选择 `full/compat` 不同。保留既有显式选择，full 仍为默认。full 的相关操作需要真实绑定和已有授权；本地 `doctor --startup` 无法认证运行中的身份，报告 BLOCKED 不等于代码坏了，不要把它变成每项任务重复执行的前置条件。显式 compat 只在现有权限内提供规划、精简上下文和复核，不承诺模型路由，不解除沙箱/Hook，也不自动替换已有 full 安装。切换前阅读[安装与恢复](docs/INSTALL.md)。

已注册 Guard 的用户，须按相应边界的生命周期更新，并在 `/hooks` 重新审查变化后的命令。单独更新 Skill 不会更新独立注册的 Hook。可选宿主补丁只打包明确允许的源文件，不包含自定义二进制；它的启用、V1/V2 及数据库兼容需要单独验收。本轮没有重编译或接管你正在运行的桌面宿主。

## 卸载与恢复

```powershell
.\cer.ps1 uninstall --scope user --dry-run
.\cer.ps1 uninstall --scope user
# 仅在确实需要恢复已核对的备份时使用：
.\cer.ps1 install --scope user --restore "ACTUAL-BACKUP-PATH" --dry-run
```

卸载只处理清单拥有的 Skill/角色文件，保留用户增加的文件和备份，只逆转明确拥有的子代理默认设置；不自动恢复旧版本。独立 Hook 和定制宿主必须分别处理。不要删除整个 `.codex`，不要回滚业务代码来修复 Router。[完整说明](docs/INSTALL.md)。

## 验证边界

CI 在 Windows/macOS/Linux 执行源码回归、静态检查、可复现打包，并从解压包重新跑全套测试。独立审计检查规则变异和参考编码的文本预算，不启动模型任务。真实模型行为及完整任务用量仍按[实装清单](docs/ACCEPTANCE.md)和[配对测量](docs/BENCHMARKING.md)验收。

[架构](docs/ARCHITECTURE.md) · [自动档位](docs/ADAPTIVE-EFFORT.md) · [写入门禁](docs/WRITE-GATE.md) · [参考资料](docs/PRIOR-ART.md) · [变更记录](CHANGELOG.md) · [贡献](CONTRIBUTING.md) · [安全](SECURITY.md) · [许可](LICENSE)
