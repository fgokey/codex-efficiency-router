# Codex Efficiency Router

[English](README.md) · [自动适配设计](docs/ADAPTIVE-EFFORT.md) · [质量协议](docs/QUALITY-PROTOCOL.md) · [实装验收](docs/ACCEPTANCE.md)

**v0.7.0-rc.8 · 仅面向 Codex · MIT · Python 3.11+ · Windows / macOS / Linux**

按子任务联合选择模型和思考档位。普通安装和更新默认自动适配，无需判断 fixed/adaptive 或反复重装。质量与授权优先；不承诺任意任务都更省、更快或质量完全不变。这是独立社区项目。


## Windows 解释器预检与验收边界

下方统一使用 `cer.ps1`；install/uninstall 包装脚本也复用它。入口实际检查 Python
版本及 `tomllib`，尝试 PATH 中可用解释器和 `py -0p` 列出的已安装版本，**在调用
安装器前拒绝 3.10**。`python` 或 `py -3` 不代表一定满足 3.11+。不下载运行时，
不改 PATH，不修改全局配置。

已有可用解释器（包括你确认可用的应用内置 Python）时，在当前 PowerShell 会话
显式指定它的**真实完整路径**：

```powershell
$env:CER_PYTHON = 'C:\实际目录\Python312\python.exe'
.\cer.ps1 doctor --scope user --json
```

显式路径无效就停止，不静默换解释器。选中的路径和版本输出到 stderr，JSON stdout
不混入提示。应用更新可能移动内置 Python；独立 Guard 会绑定安装时解释器绝对路径，
路径变化后要重新检查/更新 Guard 并审查定义。Portable Plugin 的解释器发现另行验收，
本入口不证明其生效。

**安装 Skill 仍不等于启用 Guard。** 未显式安装并现场验证时，仍是 policy-only；
CI 全绿也不等于原生 Canary 通过或真实任务已经更省、更快。没有对应宿主证据时，
`enforcement=NOT_VERIFIED`、加载版本 `UNKNOWN` 继续保留。
见[显式启用 Guard 与 Canary](docs/UPGRADE-v0.7.0-rc.1.md)。

## v0.7.0-rc.8：限制读取输出并避免重复前缀

强制规则文件分别读取；其他大小未知的文件先看索引，再读取相关范围；只有已知较小且
合计不超输出预算的片段才能批量读取。输出被截断后，只续读缺失范围，不再重复已取得
的前缀。所有角色都携带同一约束，并增加了可执行的离线决策测试，现有指令预算不变。
这是策略行为，不证明旧任务已经加载。

## v0.7.0-rc.7：处理档位不匹配并保留关键上下文

发现实际模型或档位不匹配后，在安全边界核对配置、副作用并复核受影响的验收结果；
保留有效修改和尝试记录，后续一次匹配记录不能自动清除待复核问题。UNKNOWN 本身
不等于已确认配置错误。精简交接必须保留适用规则路径、关键决定及理由；所有角色
读取项目规则，关键上下文缺失时暂停受影响的工作。
独占所有权的父 Astra 可以继续同一合格修复单元，其他写入者仍会阻止例外。
需要对比费用和质量时复用既有任务日志，不增加探测或轮询。

## v0.7.0-rc.6：修复边界与按任务显式调档

父 Astra 修复例外和执行者复用都必须通过前置条件、能力/档位、安全边界及绝对重试上限
检查。一个受限修复单元可包含代码、测试等多次补丁；仅给理由不能续期。
Sol/Terra 可在父代理明确移交已有用户授权、仓库/分支/目标及必要检查后负责交付。

自动联合选择模型与档位：实现 Terra/medium，诊断 Sol/medium，耦合或高后果推理
Sol/high，特别困难的判断 Astra/high。显式传入自动角色、思考档位和 `fork_turns="none"`，
通过精简完整的契约交接，避免继承父代理 max。优先复用足够能力的空闲执行者，
保留 fixed/low 偏好。离线测试不能证明运行时已加载或节省。原生修改文件徽标以宿主
归属证据为准，不能凭模型名称或 Review 入口断言生效。这取代 rc.4 的模型限制和
rc.5 的单补丁限制；严格 Guard 仍禁止 Astra 写入。

## v0.7.0-rc.5（历史）：父 Astra 的受限修复

Astra 继续负责困难诊断和裁决。Astra 子代理及只读角色始终禁止写入。父 Astra 仅在
执行者经过合格尝试仍失败，或移交会实质丢失修复所需的关键推理时，才可直接完成一次
范围明确的本地代码修改；同时必须已确认用户授权、精确范围、当前任务工作区、独占
所有权、安全边界和验证方法，且没有活跃写入者、既往例外或已观察到的活跃严格 Guard。
未知 Hook 层仍可能在运行时拒绝写入，成功前不能声称已经修改。
Shell、构建、有副作用测试及发布仍由 Sol/Terra 执行。证据不完整就委派、等待或阻塞。
可选原生 Guard 有意保持更严格，会禁止所有 Astra 写入。

## v0.7.0-rc.4（历史）：原生修改汇总预检

写入派发前，Router 现在会检查目标 Git 仓库是否属于当前任务工作区，以及修改是否
由同一个具备写权限的父线程完成，避免再把 Review 入口描述成原生“修改文件”徽标的
修复。必须保留徽标的写任务应在目标仓库中使用 Sol/Terra 父线程，Astra 只承担困难
判断的只读子任务。

## v0.7.0-rc.3：显式自动档位派发

自动生成的角色现在会在宿主角色发现信息中标明自己是自动档位绑定。宿主同时暴露
匹配的 `cer_auto_<角色名>` 和显式档位字段时，父 Agent 必须使用该别名并传入选定
档位。固定角色只作有证据的兼容回退；自动路径可用时仍选择固定角色会报告为不匹配。
本次仍是 policy-only，不增加模型调用或常驻进程。

## v0.7.0-rc.2：精简指令

本候选版压缩核心 Skill、按需 references 和独立角色指令，不改变路由与写权限。
引用文件仅在对应条件触发且尚未加载、失效或压缩后丢失时读取，避免逐工具重读。
详见[体积与验证记录](docs/VALIDATION-v0.7.0-rc.2.md)。保留 fixed/low 设置和底层安装参数；Windows 入口见上方预检说明。


## v0.7.0-rc.1：可验证状态，不冒充运行时已生效

源码仍是基于 v0.6.0 的**候选版本，不是稳定正式版**；尚未完成全部发布门槛。
保留已安装的 fixed 模式与 automatic low 关闭状态；不增加 Write Lease、
常驻进程或强制并发状态账本。Astra 遇到复杂问题仍亲自诊断和验收，但不直接写入。

`policy-only` 只代表规则；`guarded` 只代表已注册，不代表已信任或已拦截；
`live-verified` 需要与当前环境绑定且未过期的**操作者见证原生 Canary**。
磁盘版本、静态测试和“哨兵文件不存在”都不能单独证明现场生效。
Hosted tools、已有执行会话的 `write_stdin` 仍不在完整覆盖范围内。

新增状态 JSON、版本/哈希诊断、显式 Guard 更新、受限 batch 读取、三组逐调用
费用统计，以及可复现 Plugin/源码打包。Plugin manifest 已有离线校验；插件角色发现、
信任与 Windows 原生执行仍需实装验收。现有用户优先沿用 Skill 安装器加显式独立
Guard 的路径，不要同时安装两套重复 Hook。

Git 工作区可按下方命令快进更新，并记录实际 commit。下载 ZIP 的用户解压审查后，
按[候选版升级说明](docs/UPGRADE-v0.7.0-rc.1.md)执行。
详见 [Canary](docs/CANARY.md)、[对比数据格式](docs/BENCHMARKING-v0.7.md)、
[验证状态](docs/VALIDATION-v0.7.0-rc.1.md)和[优化计划评审](docs/REVIEW-v0.7.0.md)。

## v0.6 历史规则：Astra 不亲自写，但必须参与难题

写入资格现在优先于“小任务本地完成”：Astra 根/子代理只读，不能 patch、写检查点、格式化、构建或运行有副作用的测试。它仍直接分析源码/diff、裁决架构和诊断反复失败；两次有质量尝试仍无法解释时，停止盲改、交 Astra 分析，结论由现有 Sol/Terra 实施。重试预算不重置。已有修改保留并移交独立复核；两个写入者忙时等待，不再开第三个。rc.5 已用上方受限例外取代这条历史规则中仅针对父 Astra 的部分。

Skill 规则不能撤回根代理工具权限。仓库另提供可安装的 Codex 原生同步 PreToolUse 门禁，拦截已覆盖路径上的直接写入，并提供受限只读读取方式。**门禁必须显式注册并在 `/hooks` 中信任；普通 Skill 安装不改共享 hooks.json，也不等于硬拦截已生效。** 这是一项作用于配置范围的权限保护，不是又一个路由模式。优先按项目一次安装，详见[写入门禁、安装/卸载与验收](docs/WRITE-GATE.md)。

## 一次安装，运行时自动适配

父 Agent 先判断必要能力和委派收益，再依据实际工具、已加载角色和支持的模型/档位选择：

| 当前宿主条件 | 行为 |
| --- | --- |
| 可显式传档位，且自适应绑定正确加载 | 必须使用自适应绑定并明确传入选定档位 |
| 缺少上述能力，但固定角色恰好满足同一模型/档位 | 使用固定兼容绑定，并记录自动路径不可用的原因 |
| 两条路径均不满足 | 仅能力及权限均足够的本地工作可继续；Astra 通常交执行者，父线程受限例外完整成立时可本地修改，否则阻塞 |

只选择一个绑定、创建一个必要子任务。不会为了探测而调用模型，不修改运行中的配置；未知写入者或副作用未确认前不重新派发。兼容回退不代表动态调档成功，实际身份未知时仍标记 UNKNOWN。

| 角色职责 | 模型 | 固定兼容档位 |
| --- | --- | --- |
| `luna_worker` | `gpt-5.6-luna` | `medium` |
| `terra_executor` | `gpt-5.6-terra` | `medium` |
| `sol_engineer` | `gpt-5.6-sol` | `medium` |
| `astra_architect` | `gpt-6-astra` | `high` |

自动模式从这四份源定义生成四个 `cer_auto_<角色名>` 自适应别名，加上四个固定兼容角色，共 **8 个小型 TOML 文件、4 种职责**。这不是 8 个同时运行的代理，也不增加模型等级；别名增加一段简短的自动档位发现标记、改变名称并去掉档位固定，模型、指令及权限保持一致。新增发现文本会占用少量宿主上下文，不宣称零开销。

正常实现通常 medium，深层推理可用 high；Astra 自动使用 high。自动 low 默认关闭，已有显式选择会保留；xhigh/max 不自动选择。不强制逐档试错，也不因改档重置失败预算。**宿主不支持 Sol/high 时，不会用 Sol/medium 冒充它。**

## 安装与更新

先审查源码。安装器只操作清单拥有的文件，不改全局 `config.toml`、`AGENTS.md`、认证、权限或其他 Skill。用户级/项目级二选一，保留克隆用于更新卸载。

### Windows / PowerShell

```powershell
git clone https://github.com/fgokey/codex-efficiency-router.git
cd codex-efficiency-router
.\cer.ps1 install --scope user --dry-run
.\cer.ps1 install --scope user
.\cer.ps1 doctor --scope user
```

### macOS / Linux

```sh
git clone https://github.com/fgokey/codex-efficiency-router.git
cd codex-efficiency-router
python3 scripts/install.py --scope user --dry-run
python3 scripts/install.py --scope user
python3 scripts/doctor.py --scope user
```

### 已安装用户更新

```powershell
git pull --ff-only
.\cer.ps1 install --scope user --dry-run
.\cer.ps1 install --scope user
.\cer.ps1 doctor --scope user
```

macOS/Linux 将 `./cer.ps1 <action>` 换为 `python3 -B scripts/<action>.py`，并先确认版本为 3.11+。**不再需要 `--mode adaptive`。** v0.4 及更早带清单安装在普通更新时迁移到 auto，并打印迁移提示、备份原文件、保留 low 设置。旧清单没有选择来源，无法区分旧默认和用户当时的意图；确需保持旧模式的高级用户可显式指定旧参数，见[迁移与兼容](docs/INSTALL.md)。v0.5+ 明确设定的高级覆盖会在以后普通更新中保留。原始 v0.1 无清单安装仍需安全认领 `--adopt-v01`，不凭文件名覆盖。

发现定制文件或同名冲突先核对，不直接 `--force`。`doctor: STATIC PASS` 仅表示静态安装一致，不是模型运行证据。更新后重新加载 Codex，新开任务可避免旧上下文混入。只复制 SKILL.md 不会部署角色，完整安装使用本仓库脚本。

### 项目级安装

```powershell
.\cer.ps1 install --scope project --project-root "C:/Work/my-project" --dry-run
.\cer.ps1 install --scope project --project-root "C:/Work/my-project"
.\cer.ps1 doctor --scope project --project-root "C:/Work/my-project"
```

macOS/Linux 使用 `python3 -B scripts/<action>.py` 和实际绝对路径。用户级 Skill 位于 `~/.agents/skills/codex-efficiency-router`，角色位于 `$CODEX_HOME/agents`（默认 `~/.codex/agents`）；项目级分别为 `.agents/skills`、`.codex/agents`。具体备份路径由安装器打印。

## 使用

```text
$codex-efficiency-router
完成当前任务，按任务需求选择模型与思考档位，保留必要验收。
```

支持相关任务的隐式触发；显式调用更明确。父线程模型不改变。简单且有权限的工作直接执行；Astra 写入通常交执行者，仅适用上述父线程受限例外。不默认多 Agent，不叠加 Router；“禁用路由”“不要子 Agent”“不要升级”仍有效。必要要求逐项对应当前证据，区分 PASS/PARTIAL/BLOCKED；换绑定、模型或上下文不重置重试次数。

原生“修改文件”徽标归属于任务工作区及该任务自己的文件变更事件。必须保留徽标时，目标仓库与写入父线程必须属于当前任务。通常使用 Sol/Terra 父线程；父 Astra 仅在受限本地修改例外完整成立时合格。任务工作区外仓库或不汇总子线程 `fileChange` 的宿主不能保证徽标。Router 必须在写入前识别这一点，不能把未暂存 Review 当成徽标修复。写入者仍返回仓库根目录和精确路径，父线程逐仓库核对并打开受支持的 Review。

## 卸载与恢复

使用与安装相同的 scope、项目路径和 CODEX_HOME。

```powershell
.\cer.ps1 uninstall --scope user --dry-run
.\cer.ps1 uninstall --scope user
```

```sh
python3 scripts/uninstall.py --scope user --dry-run
python3 scripts/uninstall.py --scope user
```

项目级使用 `--scope project --project-root ...`。只删除清单拥有的角色及 Skill，保留未跟踪文件、现有配置和备份；用户修改默认阻止卸载。默认不会恢复旧版，没有 `--no-restore` 参数。需要恢复时用真实备份目录：

```powershell
.\cer.ps1 install --scope user --restore "ACTUAL-BACKUP-PATH" --dry-run
.\cer.ps1 install --scope user --restore "ACTUAL-BACKUP-PATH"
```

恢复按备份原样还原，不顺便升级到 auto；卸载后重新加载 Codex。不要公开包含私人定制的备份。完整[安装与安全恢复说明](docs/INSTALL.md)。

## 验证和边界

```sh
python3 -m unittest discover -s tests -v
python3 scripts/doctor.py --source-tree .
python3 evaluation/offline_audit.py --without-tokenizer
```

以上不调用模型。CI 另使用固定 tokenizer 统计文本；离线函数检查声明的条件，不是强制执行器。真实角色加载、模型/档位、任务质量、完整父子线程 token 和耗时仍由[实装验收](docs/ACCEPTANCE.md)确认。历史失败报告保留，按[评估方法](docs/BENCHMARKING.md)解释结果，不把静态通过当作实际节省。

[架构](docs/ARCHITECTURE.md) · [参考资料](docs/PRIOR-ART.md) · [变更](CHANGELOG.md) · [贡献](CONTRIBUTING.md) · [安全](SECURITY.md) · [许可](LICENSE)

[Validation v0.6.0](docs/VALIDATION-v0.6.0.md)
