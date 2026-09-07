# 实装验收 / User-run acceptance

本版本先完成离线修复和回归；实际 Codex 宿主验收由使用者执行。**以下静态 Python 命令不会调用模型**。后面的可选 Codex 提示词会执行模型任务，不属于离线免费测试，不会由安装器或 CI 自动触发。

## 1. 静态安装检查

在保留的仓库克隆中执行。用户级 v0.2+ 更新：

```powershell
git pull --ff-only
py -3 scripts/install.py --scope user --dry-run
py -3 scripts/install.py --scope user
py -3 scripts/doctor.py --scope user
```

macOS/Linux 把 `py -3` 换成 `python3`。项目级沿用原来的 `--scope project --project-root ...`；仅原始 v0.1 安装需要 `--adopt-v01`。定制文件冲突先核对，不要直接追加 `--force`。

静态通过条件：doctor 为 STATIC PASS；现有配置未被替换；仅安装本 Skill 和四个角色。预设为 Luna/Terra/Sol 的 medium、Astra 的 high，没有独立第五层。STATIC PASS 不证明运行时模型可用。重启或重新加载 Codex，避免用已载入旧指令的长对话验收新版。

## 2. 先验收开关，不要求四模型全部启动

在正常任务中明确“本次禁用路由”或“不要子 Agent”。检查没有新增子线程、没有隐藏 CLI/API 调用；当前能力不足时应报告阻塞，不能声称换了更强模型。不要为了检查开关额外启动批量测试。

## 3. 可选：一个只读委派冒烟任务

在实际本地 Codex 中自行提交：

```text
$codex-efficiency-router
本次仅做安装验收，允许为验证目的进行一次有边界的只读委派。
若宿主已发现 terra_executor，则让它核对当前仓库 README 中安装/卸载命令与 Python CLI 参数是否一致。
不得改文件、配置、提交、推送、部署、访问凭据或再创建子 Agent；禁止隐藏 codex exec/API 回退。
最多一个子任务，不自动重试；角色不存在立即说明。
报告请求角色、宿主可观测的实际模型/effort、读取结果及未知项，不用模型自述证明身份。
```

通过条件：工具和角色真实存在；子任务只读；最终集成结果准确；元数据能确认实际模型/档位。若宿主不暴露身份，记录 UNKNOWN，此项未通过而不是假定成功。角色配置文件优先于矛盾的 spawn 参数；父线程权限可能影响子线程，不能把只读指令当作操作系统沙箱的证明。

## 4. 随正常开发验证行为

已定方案的有边界实现应倾向足够的便宜模型，但短尾工具工作不强制开子 Agent。实质未决且通过三项门槛的决策才自动升级 Astra；问题解决后重新评估剩余任务。普通编译错误不应逐次升级；需求/环境/权限/观测缺口先修前置条件。同档重试必须说明为何新上下文或独立判断能解决当前阻塞，并有明确验收和停止条件。

质量验收由既定行为检查、回归和必要集成测试决定。不要把模型自评、路由日志或新生成的测试单独当成充分证据。不要为省 token 降低既定验收要求。

## 5. 用量与速度（可复用已有日志）

记录版本、宿主版本、实际模型/档位、任务/验收、已加载参考文件、全部父子线程 usage、重试、开始到验收完成时间。无法取得的值留空/UNKNOWN，累计 usage 只取最终值或去重增量；推理若已包含在输出中不要再加一次。不要公开 auth.json、密钥、Cookie、私人配置或完整私有会话。

配对对照需相同代码起点、隔离工作区、同验收、多次试验；普通开发日志只能提供观察证据，不等同严格 A/B。详见 [BENCHMARKING](BENCHMARKING.md)。参考编码文本 token、API 价格、Codex 套餐额度与完整任务 token 不可混为一谈。

## 6. 卸载与显式恢复

```powershell
py -3 scripts/uninstall.py --scope user --dry-run
py -3 scripts/uninstall.py --scope user
```

默认不自动恢复旧版本；保留备份和未跟踪文件。确需恢复时使用脚本实际打印的备份目录：

```powershell
py -3 scripts/install.py --scope user --restore "ACTUAL-BACKUP-PATH" --dry-run
py -3 scripts/install.py --scope user --restore "ACTUAL-BACKUP-PATH"
```

范围与 CODEX_HOME 应与原操作一致。没有 `--no-restore` 参数；恢复成功也不表示它恢复的是最新版，应重新检查安装版本。
