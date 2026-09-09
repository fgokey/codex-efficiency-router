# v0.7.0-rc.1 本地验证记录

验证日期：2026-09-09。运行环境：Linux / Python 3.13.5。
源基线：`a1ca29d69d8fcf32499ea8062c05316004489692`。候选修改未 commit、未推送、未创建 tag。
准确分发字节由包内 RELEASE-MANIFEST.json 标识，不能把基线 commit 当成候选内容。

## 实际完成的验证

| 项目 | 结果 |
| --- | --- |
| 上传 v0.6.0 原始基线 | 278 项单测通过 |
| 更新后完整回归 | 339 项通过，新增 61 项，0 失败 / 0 错误 / 0 跳过 |
| 原有规则/质量/档位/写边界变异测试 | 12 + 12 + 27 + 12 = 63 项，全部捕获（KILLED） |
| source doctor | STATIC PASS，源配置 fixed / automatic low=false，enforcement NOT_VERIFIED |
| portable Plugin schema、版本与 bundle 摘要一致性 | PASS |
| Python compileall、git diff --check | PASS |
| 从上传的真实 v0.6.0 执行安装→候选升级→Guard 卸载 | PASS，仅在一次性临时项目验证 |
| dry-run 不写文件、第三方 Hook/AGENTS/config 保留 | PASS；还覆盖自定义冲突与同期外部修改保护 |
| Skill core 字节 | 6082 / 6500 |
| Skill + 全部 references（含连接换行）字节 | 11404 / 12000 |

字节预算没有放宽，不等于真实模型 Token 计量。原有日期后缀 Sol 放行测试改为拒绝，
因为新规则只允许审查过的精确模型 ID；不是为了测试通过而移除边界检查。

[机器可读本地摘要](validation/local-summary.json) ·
[真实 v0.6.0 临时项目升级证据](validation/actual-v060-upgrade.json)

原源码仓库 AGENTS.md 与 config/ 保持原字节。测试只使用临时配置，不接触用户的
Windows 文件系统，不改认证、全局模型设置或权限。第三方 Hook 只被诊断而不删除。

## 本地微基准，不是 Codex 加速承诺

每项 30 次，含 Python 冷启动与 Guard bundle 哈希检查；轮换执行次序。
结果仅代表本次 Linux 工具运行环境。Native Codex 调度、模型推理、账单、Windows
Python 启动行为均不在这组数据中。

| 路径 | 样本 | P50 ms | P95 ms |
| --- | --- | --- | --- |
| guard_deny | 30 | 629.48 | 787.53 |
| guard_passthrough | 30 | 636.88 | 748.49 |
| guard_read_rewrite | 30 | 622.07 | 745.47 |
| reader_four_processes | 30 | 2492.37 | 2779.83 |
| reader_one_batch | 30 | 650.34 | 717.06 |

本样本中“四次独立 reader 进程 → 一次四操作 batch”的 P50 降低 **73.9%**。
这是有限读取操作的本地进程开销对比，不是“Codex 总耗时下降 73.9%”，也不是
Token/费用下降证明。Guard 单次约数百毫秒在此环境并不便宜，应在目标 Windows
环境复测，再判断整体成本是否划算。本次没有为了这组数据引入常驻服务。

[原始微基准 JSON](validation/guard-benchmark-linux.json)

## 尚未完成，因此只交付 RC

- 目标 Windows / 原生 Codex / Plugin 加载与角色发现 / 用户审查后的真实 Canary：未运行。
- GitHub Windows、Linux、macOS CI：配置已更新，远端工作流未运行；本地 Linux 测试不是远端 CI。
- 固定 tiktoken 0.11.0 的历史文本 Token 审计：未运行，当前环境缺少该依赖；仅运行 --without-tokenizer。
- 真实模型三组价格、质量、端到端速度实验：未运行，没有可发布的收益结论。
- annotated Git tag / GitHub Release / 远端发布：未进行。

## 不可变分发包的复验

打包后使用 `python -B scripts/check_artifact.py ACTUAL_PACKAGE.zip` 校验包内所有文件
SHA-256、source_tree_sha256，并在重新解压的副本执行 schema、doctor 与完整单测。
最终分发 ZIP 的具体复验结果与 ZIP SHA-256 写在**包外交付验证报告**，不回写 ZIP，
避免“将 ZIP 自身校验结果写进 ZIP”造成字节/哈希循环改变。该命令也会在更新后的 CI
定义中执行；准备了 CI 定义不等于远端已通过。

## 复现命令

```powershell
python -B -m unittest discover -s tests -v
python -B scripts/doctor.py --source-tree . --json
python -B scripts/release_package.py --check --schema
python -m compileall -q scripts hooks tests evaluation
```

schema 校验额外需要 jsonschema==4.26.0；安装与运行 Skill/Guard 不需要该库。
有完整 Git 历史的仓库可运行 `python -B evaluation/offline_audit.py --without-tokenizer`
及 `python -B evaluation/write_audit.py`。前者完整 Token 审计还需要 pinned tiktoken；
分发 ZIP 不含 .git，历史比较应在保留原仓库历史的工作树执行，不假装可从无历史
源码恢复旧版本证据。所有命令都不替代 [原生 Canary](CANARY.md)。
