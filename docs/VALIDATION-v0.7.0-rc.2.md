# v0.7.0-rc.2：Skill 指令精简与验证

本版基于已交付的 `v0.7.0-rc.1`，是尚未发布的候选版。修改集中在模型会读到的指令、按需读取规则和离线体积检查；没有新增长驻进程、运行时分类模型或逐工具统计脚本。

## 1. 实测范围

以下数据为 **UTF-8 源文本字节数**，不是 Token 数、模型上下文总量、账单或实际任务收益。核心包含 frontmatter，不重复计入 description；全量包含四个 reference，并保留原 doctor 的每文件一个分隔换行口径。每个角色按 TOML 解析后的 `developer_instructions` 单独计量，不假设四个角色都参与同一任务。

| 内容 | rc.1 | rc.2 | 减少 |
| --- | ---: | ---: | ---: |
| 核心 SKILL.md | 6,082 | 4,985 | 18.0% |
| 核心 + 全部 references | 11,404 | 9,262 | 18.8% |
| 核心 + effort + dispatch（同路径示例） | 9,340 | 7,481 | 19.9% |
| Astra 独立角色指令 | 1,071 | 819 | 23.5% |
| Luna 独立角色指令 | 1,034 | 794 | 23.2% |
| Sol 独立角色指令 | 1,173 | 890 | 24.1% |
| Terra 独立角色指令 | 1,046 | 810 | 22.6% |

发现阶段 description 从 217 字符缩短为 152 字符。字节数按 UTF-8 实测；description 另按字符计量，不把两者混为 Token。数据与基线 ZIP SHA-256 见 [逐文件记录](validation/instruction-footprint-rc2.json)。

本环境没有 tiktoken，尝试安装时包索引 DNS 不可用，因此没有用“字符数 / 4”等估算冒充精确 Token。也未测量真实模型质量、缓存、计费或端到端延迟。

## 2. 按需加载调整

核心明确列出四个读取触发点：首次派发需要 effort；Astra 准入需要 routing；派发或 guarded shell 需要 dispatch；checkpoint、恢复或证据争议需要 quality。只在首次需要、依据失效或压缩后相关约束丢失时重读。

不批量预读 docs/hooks，不要求每个子代理再复制完整 Router，不反复输出路由横幅。子代理保留自足的权限、重试和验收指令，不能假定它天然继承了父代理的安全规则。宿主是否继承历史仍由原生工具决定，本版没有声称它能清除历史或强制创造空上下文。

这些是指令约束，不是宿主级缓存、上下文去重或自动压缩 API。已进入旧线程的文本不会因磁盘文件变小而自动消失。

## 3. 保留的边界

Astra 根/子代理仍不得写入、格式化、构建或执行有副作用操作，但继续承担高难度诊断和失败恢复判断。最多两个写者、保留既有修改、跨代理共享尝试历史、UNKNOWN 不能充当 PASS、同模型派发收益门槛及最终验收全部保留。

角色模型、默认思考档位、sandbox 设置和安装/升级代码不变。保留既有 fixed 与 automatic-low 关闭设置。Guard 和 reader 仅同步 VERSION；去除版本文本后，与 rc.1 逐字节相同。没有增加 Write Lease 或削弱未知身份写入拒绝。

## 4. 自动体积门槛

| 门槛 | rc.1 | rc.2 |
| --- | ---: | ---: |
| 核心指令字节 | 6,500 | 5,200 |
| 核心及全部 references 字节 | 12,000 | 9,600 |
| description 字符 | 400 | 180 |
| 单角色 developer_instructions 字节 | 未单独限制 | 950 |

`doctor --json` 新增 `instruction_footprint`，明确把 Token 和任务总收益标为 `NOT_MEASURED`。该检查只由显式 doctor 调用，不在任务路由、派发或每次工具调用时自动运行。

## 5. 验证与限制

原 rc.1：339 项单测通过。rc.2 新增 9 项体积、独立角色、按需加载与边界保护检查，未修改或删除已有测试。最终源码的测试结果见 [源码测试记录](validation/rc2-source-tests.json)。12 项路由、12 项质量、27 项 effort 和 12 项写边界变异，共 63 项全部被捕获；见 [变异记录](validation/rc2-mutations.json)。

候选 ZIP 无 `.git`，故直接调用原有变异函数，没有把 Git 报告包装器称为运行成功。变异测试验证离线规则辅助代码，不证明自然语言指令在真实模型中的行为完全等价。

临时项目中实测 rc.1 → rc.2 升级，未指定新模式时保留 fixed/low 关闭；AGENTS.md、config.toml 与第三方 hooks.json 字节不变。见 [升级记录](validation/rc1-to-rc2-upgrade.json)。源码 doctor、Plugin schema/摘要一致性及 Python 编译检查通过。分发 ZIP 在生成后单独核验清单并重新运行完整测试；外部交付报告记录该最后一步的结果。

未执行：Windows/macOS 原生运行、真实 Codex Canary、原生角色/Hook 加载与信任、真实任务质量 A/B、精确 Token 和费用测量、GitHub 提交/tag/Release。

## 6. 更新

在解压后的 `codex-efficiency-router` 根目录执行，沿用 Python 3.11+：

```powershell
python -B scripts/install.py --scope user --mode fixed --no-allow-low --dry-run
python -B scripts/install.py --scope user --mode fixed --no-allow-low
python -B scripts/doctor.py --scope user --json
```

自定义文件仍阻止静默覆盖，不要为了安装通过直接使用 `--force`。普通 Skill 更新不注册或信任 Hook。版本与策略/脚本哈希已更新，旧 Canary 不能作为本版 `live-verified` 的证据；Guard 仍走显式升级、审查和验收流程，见 [已有升级流程](UPGRADE-v0.7.0-rc.1.md) 与 [Canary](CANARY.md)。这些文档中的 rc.1 是原候选版示例，本版版本号为 rc.2。

只更新了交付包，未操作用户本机安装目录。在写代理完成后的安全边界重新加载；旧线程不自动清除原有指令上下文。
