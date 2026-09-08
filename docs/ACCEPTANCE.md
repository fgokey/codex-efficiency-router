# 实装验收：一次安装，无需切模式

## 静态检查（不调用模型）

```powershell
git pull --ff-only
py -3 scripts/install.py --scope user --dry-run
py -3 scripts/install.py --scope user
py -3 scripts/doctor.py --scope user
```

macOS/Linux 使用 python3。v0.4 及更早的普通更新会提示迁移到 auto；明确的 v0.5+ 高级模式覆盖保留。核对只修改清单拥有的文件，auto 为四个固定角色＋四个 cer_auto 别名；模型/权限一致，别名不固定档位。STATIC PASS 不证明真实模型运行。重载 Codex，以新任务验收。

## 实际宿主检查（使用 Codex 才会执行模型任务）

先用正常任务验证开关：禁用路由/禁止子 Agent 时不能新建子线程，能力不足不能假装完成。能力检查从已有原生工具与元数据读取，不能为了探测逐个运行高级模型。

可选只读冒烟提示词：

```text
$codex-efficiency-router
本次允许一次只读委派，验证自动适配。核对 README 安装/卸载命令与 Python CLI 是否一致。
有显式档位能力且 cer_auto_terra_executor 可用时请求 Terra/medium；否则仅在 terra_executor 固定配置正好匹配时用兼容绑定。
不修改文件、配置、提交或发布，不访问凭据，不创建额外会话，不自动重试。
报告选择的绑定、请求的模型/档位、可观测的实际值及核对证据；实际信息缺失标 UNKNOWN。
```

观察：只创建一个子任务；不能同时派发两条路径来“比较”；兼容绑定不能报告为动态调档成功。未开放动态参数而需要 Sol/high 时，不能靠 Sol/medium 通过验收。充分的父代理可继续，否则报告必要能力缺失，无需让用户反复切模式。

## 质量与恢复

既定方案不能覆盖原始要求；每个必要结果要有当前代码/测试/环境的证据。披露缺失不等于豁免，子任务 PASS 不等于项目 PASS。旧验证过期要重验受影响部分，不全部重跑。跨模型、档位、绑定和压缩共享尝试预算；未知活跃写入者或外部副作用先核对，不能回退后重复执行。

使用现有 [行为场景](../evaluation/behavior_cases.json)与[思考档位场景](../evaluation/effort_cases.json)，只给被测 Agent 任务和环境，不给评分答案。它们是待实装用例，不是已通过的模型实验。auto 的故障/兼容矩阵由离线测试覆盖，真实工具仍须独立观察。

## 用量和记录

记录版本、宿主、请求绑定、实际模型/档位、参考文件、所有父子线程 usage、重试及开始到验收完成时间。UNKNOWN 留空，不读或公开凭据、私人配置、完整敏感会话；累计 usage 去重，不重复加已计入输出的推理 token。别名只是配置，不意味着同时跑八个代理，但发现元数据可能增加上下文。严格比较按[配对评估](BENCHMARKING.md)执行；不把文本分词当实际计费。

## 卸载/恢复

```powershell
py -3 scripts/uninstall.py --scope user --dry-run
py -3 scripts/uninstall.py --scope user
```

检查只移除所有受管理绑定和 Skill、保留其他配置和备份。使用相同 scope/CODEX_HOME 显式恢复：

```powershell
py -3 scripts/install.py --scope user --restore "ACTUAL-BACKUP-PATH" --dry-run
py -3 scripts/install.py --scope user --restore "ACTUAL-BACKUP-PATH"
```

恢复是还原原文件/模式，不顺便迁移；普通后续更新才适用迁移策略。定制冲突先审查，不能默认强制覆盖。
