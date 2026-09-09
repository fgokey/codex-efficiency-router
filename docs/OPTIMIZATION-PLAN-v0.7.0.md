# codex-efficiency-router v0.7.0 优化计划

## 1. 背景

v0.6.0 已经补齐 Astra 根代理的写入边界：Astra 负责高难度判断和只读诊断，Sol/Terra 负责修改、构建和有副作用的验证；可选的同步 `PreToolUse` Hook 会在受支持的工具路径上拦截 Astra 和未知模型的写操作。

当前主要问题已经从“规则是否正确”转为“用户能否确认规则正在当前任务中生效”：

- 普通 Skill 安装不会注册 Hook，因此默认只有提示词约束。
- Guard 状态只有 `PRESENT/ABSENT`，不能识别版本过期、解释器失效和现场验证状态。
- Skill、Guard 和正在运行的任务可能使用不同版本。
- 离线测试不能证明 Codex 已加载、信任并实际调用 Hook。
- `write_stdin`、Hosted tools 和部分特殊工具路径不在完整拦截范围内。
- 每次 Guard 和 `cer-read` 调用都会产生进程启动与上下文成本，目前没有实际延迟数据。
- 仓库还没有正式 Git tag，安装来源和发布版本缺少固定锚点。

相关边界见 [WRITE-GATE.md](WRITE-GATE.md) 和 [VALIDATION-v0.6.0.md](VALIDATION-v0.6.0.md)。

## 2. v0.7.0 目标

v0.7.0 的目标是让 Router 的安装状态、执行状态和收益能够被验证：

1. 用户能区分“仅加载策略”“已注册 Guard”“已通过现场验证”。
2. Skill、Hook、安装清单和发布版本保持一致，版本漂移可以被发现。
3. 不修改现有 `AGENTS.md`、`config.toml`、认证信息或其他 Hook。
4. Astra 在受支持的工具路径上不能写入，Sol/Terra 的正常执行不受阻断。
5. 现场 Canary 能以很小的模型消耗验证真实拦截行为。
6. 对比测试分别报告价格、Token、质量和墙钟时间，不用 Token 数量代替价格。
7. Guard 与只读检查的额外延迟可测量，批量只读路径减少重复调用。

## 3. 非目标

v0.7.0 不承诺：

- 完整的操作系统级隔离或对恶意本地进程的防护。
- 自动信任 Hook、绕过 Codex 审查或修改全局权限。
- 拦截 Codex 官方未接入 Hook 的 Hosted tools 或特殊工具路径。
- 仅凭离线测试证明模型质量、真实价格下降或执行速度提升。
- 在没有权威子代理状态接口时，用复杂的本地状态机强制管理所有并发写者。

## 4. 交付方案

### 4.1 推荐发布 Codex Plugin

将 Skill、Hook 和版本清单打包为同一个可版本化 Plugin：

```text
plugin.json
skills/codex-efficiency-router/SKILL.md
hooks/hooks.json
hooks/astra_write_guard.py
hooks/readonly_reader.py
scripts/
```

保留现有纯 Skill 安装方式以兼容已有用户，但明确区分三种状态：

| 状态 | 含义 |
| --- | --- |
| `policy-only` | 仅有 Skill 规则，没有运行时拦截证明 |
| `guarded` | Guard 已注册，信任或现场拦截尚未验证 |
| `live-verified` | 当前 Guard 定义已经过用户审查，并在当前环境通过 Canary |

要求：

- Plugin manifest、Skill 和 Hook 使用同一个版本号。
- Hook 使用 `${PLUGIN_ROOT}` 定位脚本，避免安装路径和 Python 脚本版本漂移。
- Hook 定义变化后必须重新审查；安装器不自动声明已信任。
- 默认推荐项目级启用，用户级启用必须明确说明影响范围。
- 纯 Skill 安装不得宣称提供运行时保护。

### 4.2 完善 Guard 状态诊断

扩展 `scripts/write_guard.py`，支持：

```text
install
update
remove
status
doctor
```

`status --json` 和 `doctor --json` 至少输出：

- Router 版本、Git commit 和安装模式。
- Guard 注册位置、版本和文件哈希。
- Hook 配置是否存在、能否解析、是否与当前发布一致。
- Hook 命令引用的解释器和脚本是否存在。
- 同一配置层是否有重复或重叠的 `PreToolUse` 匹配项。
- 注册状态：`ABSENT`、`PRESENT`、`OUTDATED` 或 `BROKEN`。
- 信任状态：不能可靠读取时必须为 `UNKNOWN`。
- 现场验证状态：`NOT_RUN`、`PASS`、`FAIL` 或 `STALE`。

状态命令只读取配置，不改变任何文件。`update` 必须支持 `--dry-run`，并继续保留其他 Hook、`AGENTS.md` 和 `config.toml`。

### 4.3 增加低成本现场 Canary

新增显式运行的现场验收流程，使用一次性目录和哨兵文件验证当前 Codex 环境：

1. Astra 请求写入哨兵文件，预期工具调用被拒绝且文件不存在。
2. Astra 使用原生读取工具，预期成功。
3. Astra 发起允许的协调操作，预期成功。
4. Sol 或 Terra 写入单独哨兵文件，预期成功。
5. 缺失或未知模型元数据的合成请求，预期拒绝。
6. 检查是否存在测试开始前已经打开的执行会话；存在时将结果标为 `UNKNOWN`，不声称已覆盖 `write_stdin`。
7. 删除测试产生的文件并输出机器可读结果。

结果记录只包含：

- Router/Guard 版本与哈希。
- Codex 版本和实际模型标识。
- 测试项、预期结果、实际结果和耗时。
- 已知未覆盖路径。

不得记录用户提示词、工具完整参数、文件内容或认证信息。Canary 不在安装、升级或普通 CI 中自动运行，避免未经用户选择消耗模型额度。

### 4.4 增加当前任务的版本握手

Router 在一个任务中首次实际启用时，只报告一次紧凑状态：

```text
CER v0.7.0 | adaptive | guard=live-verified | policy=<short-hash>
```

规则：

- 磁盘安装版本不能作为正在运行任务已加载该版本的证明。
- 升级时不得中断正在修改文件的执行代理。
- 旧任务在安全边界重新加载后才能报告新版本。
- 未知加载状态应显示 `UNKNOWN`，不能根据时间或安装清单推断。
- 版本握手每个任务只出现一次，避免增加重复上下文。

### 4.5 收紧已知覆盖缺口

在 Skill 和 Guard 文档中明确执行以下规则：

- Astra 不得继承、接管或继续输入已经存在的 shell 会话。
- 需要继续旧会话时，由原 Sol/Terra 所有者处理；所有者未知时先核对状态。
- Hosted tools 和未识别的特殊工具路径标记为 `UNPROTECTED` 或 `UNKNOWN`。
- 未知模型保持拒绝写入，不根据名称相似度自动放行。
- 多个匹配 Hook 会并发运行；`doctor` 必须报告可能重叠的定义。
- Guard 只称为 native write guardrail，不称为完整安全边界。

“父代理负责实现”统一改为：“父代理负责结果与集成，指定的 Sol/Terra 执行代理负责修改。”

### 4.6 批量只读协议

在现有 `cer-read` 协议中增加 `batch`：

```json
{
  "op": "batch",
  "requests": [
    {"op": "status", "path": "."},
    {"op": "search", "path": "src", "query": "Owner"},
    {"op": "read", "path": "src/component.cpp", "start": 1, "lines": 120}
  ]
}
```

约束：

- 每批最多 16 个操作。
- 只允许现有 `read/list/search/diff/status` 操作。
- 每个路径独立执行工作区和链接逃逸检查。
- 合计输入、输出和文件读取量必须有固定上限。
- 不接受任意命令、环境变量、重定向或额外 Git 参数。
- 批次中任一请求非法时整批拒绝，避免部分执行造成误判。

### 4.7 对比测试与性能测量

扩展 `scripts/compare_runs.py`，对以下三组进行比较：

| 组别 | 配置 |
| --- | --- |
| Baseline | 不加载 Router |
| Policy-only | 加载 Skill，不启用 Guard |
| Guarded | 加载 Skill，启用并验证 Guard |

每次运行记录：

- 父任务和所有子任务的实际模型、思考强度和尝试次数。
- 各模型输入、缓存输入、输出 Token 和实际价格。
- 总墙钟时间、关键路径时间和等待时间。
- Guard 调用次数、P50/P95 延迟、拒绝次数和异常次数。
- 测试结果、静态检查、验收项和代码审查结论。
- Astra 写入次数、重复写者和失败后重复执行次数。

计算规则：

- 总价格按每次调用的实际模型价格分别计算后求和。
- Token 和价格分别报告，不能将不同模型的 Token 视为相同成本。
- 并行子任务的 Token 与价格全部相加，时间按墙钟时间计算。
- 失败、重试和废弃子任务必须计入。
- 质量验收不通过时，不得给出“效率提升”结论。
- 缺少真实用量或价格时结果为 `UNKNOWN`，不能估算成零。

低成本发布前测试可选取三个短任务，每组各运行一次；形成正式效果结论前，每种条件至少重复三次并随机化执行顺序。

## 5. 实施阶段

### 阶段 A：打包与状态可见性

工作项：

- 增加 Plugin manifest 和 bundled Hook 配置。
- 增加统一版本来源和哈希校验。
- 实现 `status/doctor/update --json`。
- 增加旧 Guard、缺失解释器、冲突 Hook 的诊断。
- 修正文档中的状态名称和所有权表述。

完成标准：全新安装、v0.6.0 升级、卸载和失败回滚都不改变用户已有配置；旧 Guard 能被识别为 `OUTDATED`。

### 阶段 B：现场验证

工作项：

- 实现现场 Canary 流程和结果格式。
- 增加任务级版本握手。
- 增加 `write_stdin` 和特殊工具覆盖说明。
- 用当前 Windows Codex 环境执行一次项目级验收。

完成标准：Astra 哨兵写入被真实阻止、Sol/Terra 写入成功、Astra 读取和协调成功；未覆盖路径明确显示为 `UNKNOWN/UNPROTECTED`。

### 阶段 C：性能优化

工作项：

- 实现并测试 `cer-read batch`。
- 测量 Guard 和 reader 的 P50/P95 延迟。
- 扩展三组对比结果格式。
- 运行低成本样本，检查是否出现质量回退或明显延迟增加。

完成标准：批量协议不扩大写权限；有真实数据说明 Guard 的额外耗时，缺少显著收益时不引入常驻进程等复杂实现。

### 阶段 D：GitHub 发布

工作项：

- 增加 Windows、Linux CI 和 Plugin schema 检查。
- 校验版本、CHANGELOG、manifest、Skill 与 Hook 策略一致。
- 对打包产物重新执行安装和回归测试。
- 创建带注释的 `v0.7.0` tag 和 GitHub Release。
- 发布安装包 SHA-256、准确 commit、升级与回滚说明。

完成标准：用户能够从固定 tag 安装并复现 CI 结果；`main` 不是唯一安装锚点。

## 6. 必须覆盖的测试

### 安装与升级

- 纯 Skill 安装保持 `policy-only`。
- Plugin/Guard 安装需要显式操作和 Hook 审查。
- v0.6.0 升级到 v0.7.0 保留现有 `AGENTS.md`、`config.toml` 和第三方 Hook。
- 修改过的已安装 Guard 不被静默覆盖。
- `--dry-run` 不写入任何文件。
- 中途失败能够回滚自身文件，不覆盖同期外部修改。

### Guard 行为

- Astra 与未知模型的 patch、shell、构建和有副作用测试被拒绝。
- Sol/Terra 的写入不被 Router Guard 额外授权，也不被错误识别为 Astra。
- 工具参数中伪造模型不能改变宿主提供的模型身份。
- malformed JSON、重复键、超限输入和路径逃逸都拒绝。
- 原生只读和协调工具仍然可用。
- 多个匹配 Hook 的存在会被诊断，不被自动删除。

### Router 行为

- Astra 根代理和叶子代理遵守相同写边界。
- `fixed/adaptive` 只影响路由，不改变写权限。
- 最多两个活动写者；第三个写者等待。
- 已有修改被保留并交给 Sol/Terra 独立复核。
- Astra 可以继续只读诊断，不因无写权限而停止高难度判断。

### 效率和质量

- 三组运行使用相同任务输入和验收标准。
- 价格使用实际模型分别计算。
- 所有子任务、失败和重试进入统计。
- 质量不通过时效率结论不可发布。
- Hook 延迟和 instruction footprint 不超过发布时声明的预算。

## 7. 发布门槛

v0.7.0 只有同时满足以下条件才能发布：

- 全部现有回归测试和新增测试通过。
- Windows 和 Linux CI 通过，打包产物通过二次验证。
- 安装、升级和卸载均证明不会替换 `AGENTS.md`。
- Guard 状态能够识别 `ABSENT/PRESENT/OUTDATED/BROKEN`。
- 至少一个当前 Codex 版本完成项目级现场 Canary。
- 现场证据包含实际模型和 Guard 哈希。
- 覆盖缺口继续明确报告，没有使用“完整隔离”等超范围表述。
- Git tag、GitHub Release、manifest 和 commit 一致。
- 没有基于离线测试宣称 Token、价格或速度已经下降。

## 8. 风险与控制

| 风险 | 控制方式 |
| --- | --- |
| Plugin 改变现有安装习惯 | 保留纯 Skill 安装，并明确 `policy-only` |
| Hook 更新导致原信任失效 | 显示新哈希并要求重新审查，不自动信任 |
| Python 进程启动增加延迟 | 先测量 P50/P95，再决定是否优化运行形态 |
| 批量读取扩大攻击面 | 固定操作白名单、数量与字节上限，整批校验 |
| 旧任务错误报告新版本 | 使用任务级一次性版本握手，未知时报告 `UNKNOWN` |
| 多 Hook 并发造成行为冲突 | `doctor` 报告重叠 matcher，不修改第三方配置 |
| 对比结果受任务差异影响 | 使用相同验收、随机顺序和重复样本 |
| Token 降低但价格升高 | Token、模型单价和总价格分开统计 |

## 9. 建议的版本边界

v0.7.0 只交付以下主线：

1. Plugin 打包与兼容安装。
2. Guard 状态、版本过期和损坏诊断。
3. 当前环境现场 Canary。
4. 任务版本握手。
5. `cer-read batch` 与 Guard 延迟测量。
6. 三组对比结果格式。
7. 固定 Git tag 和 GitHub Release。

更复杂的强制并发所有权、跨进程状态服务或常驻 Guard 进程，应等待 v0.7.0 的现场数据证明有必要后再单独设计。
