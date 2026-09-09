# v0.7.0-rc.1 候选版升级与回退

## 版本与适用范围

此流程适用于 v0.7.0-rc 系列。rc.1/rc.2 分发包从 v0.6.0 修改得到；
ZIP 内容由 `RELEASE-MANIFEST.json` 的逐文件 SHA-256 和 source_tree_sha256 标识。
Git 检出使用实际 commit 标识，不能凭版本字符串把不同源码当成同一内容。
rc.2 已提交 GitHub；提交源码不等于创建正式 tag/Release，更不等于现场验收。
不要把磁盘升级解释为正在运行的任务已经加载新版本。

先等正在写入的 Sol/Terra 到安全边界，再升级、审查 Hook 并重新加载。不要为了升级
杀掉写者或回滚原有业务改动。以下命令在解压得到的 `codex-efficiency-router` 目录执行。
Python 3.11+；运行安装器无需第三方依赖。Windows 使用下方 `cer.ps1` 进行版本
和 tomllib 预检；默认 python/py 是 3.10 时不会盲目运行安装器。已有可用的内置
Python 3.12 时，将 `$env:CER_PYTHON` 设置为该解释器真实完整路径，不猜测应用安装目录。
macOS/Linux 使用已确认的 `python3 -B scripts/<script>.py` 代替对应入口。

## 1. 保留当前用户级 fixed Skill

```powershell
.\cer.ps1 install --scope user --mode fixed --no-allow-low --dry-run
.\cer.ps1 install --scope user --mode fixed --no-allow-low
.\cer.ps1 doctor --scope user --json
```

脚本只维护自身清单拥有的 Skill/角色文件，不注册 Guard、不修改 `AGENTS.md`、
`config.toml`、认证或第三方 Hook。已有自定义修改会阻止覆盖；先核对 diff，不直接
`--force`。普通 v0.5+ 清单更新会保留既有 fixed/low；这里显式写出参数，避免误选
历史迁移或全新安装的 auto 默认。不要只替换一份 SKILL.md。

项目级 Skill 安装应将 `--scope user` 改为 `--scope project --project-root $Project`，
两者择一；同一项目可能同时受用户、项目、Plugin、托管配置影响。

## 2. 显式处理项目 Guard

把下方路径替换为真实项目根目录。每个目标项目分别检查，不能用一个项目的 Canary
证明 V4/V5/用户级全部生效。

```powershell
$Project = "C:\Work\your-project"
.\cer.ps1 guard status --scope project --project-root $Project --json
```

`ABSENT` 时显式安装；`PRESENT/OUTDATED` 且需要更新时使用 update，二选一：

```powershell
# 尚未安装时：
.\cer.ps1 guard install --scope project --project-root $Project --dry-run --json
.\cer.ps1 guard install --scope project --project-root $Project --json

# 已有受本包管理的 Guard 时：
.\cer.ps1 guard update --scope project --project-root $Project --dry-run --json
.\cer.ps1 guard update --scope project --project-root $Project --json
```

`BROKEN` 或检测到自定义脚本、重复所有权、配置损坏时先处理冲突，不能强制吞掉错误。
第三方 matcher 即使重叠也只报告、不删除。随后在 Codex 中审查当前 `/hooks` 定义。
命令绑定脚本内容摘要；策略或 reader 更新会改变定义，不能沿用旧信任推断。
`guarded` 不代表信任成功。信任状态无法可靠读取时始终 `UNKNOWN`。

status/doctor 的 `registration_kind=standalone-native` 只描述选定层的独立注册。
Plugin/其他配置层仍可为 UNKNOWN；同层 `ABSENT` 不等于系统没有任何保护。
缺失解释器会报 BROKEN，但脚本不会为诊断执行任意配置中的解释器；其运行能力需现场
验证。不要把 `interpreter_exists` 当作已实际执行。launcher 的 Python 预检也不等于
Codex 实际调用 Hook。使用应用内置 Python 时，该应用升级可能改变绑定路径；出现
BROKEN 时先核对解释器，再显式 update 并重新审查，不能改成未知版本的裸 python。

## 3. 现场验收另行显式进行

见 [CANARY.md](CANARY.md)。prepare/verify 脚本本身不调用模型；由操作者在目标
原生 Codex 会话执行五项小探针会消耗少量实际模型额度。安装/更新/普通 CI 不自动运行。
本包没有附带伪造的 native PASS 证据。

## 4. Plugin 路线仍是候选

根 `plugin.json` 使用 portable schema，`extensions.com.openai.hooks` 指向 bundled
Hook，`${PLUGIN_ROOT}` 定位脚本，并提供 Windows command override。不要将本地
ZIP 当成已在市场发布/已信任/已加载的插件。

通过当前宿主实际支持的本地插件入口审查加载；不在此编造 install CLI。尤其
`agents/*.toml` 被打包不等于宿主自动注册其角色。现场尚未验证这条路径；已有用户使用
前述独立安装路径更可控。两个路径不要同时重复注册。

## 5. 回退

保留安装器打印的实际备份目录，不要把整个旧 hooks.json 覆盖到现有配置上。
Skill 可用 `.\cer.ps1 install --restore ACTUAL_BACKUP_PATH` 恢复该次安装，
仍会检查并发/后续修改。恢复命令不使用虚构的备份路径。

Guard 卸载只移除清单拥有且未被修改的条目和脚本，再由原 v0.6.0 包显式安装旧版本：

```powershell
.\cer.ps1 guard remove --scope project --project-root $Project --dry-run --json
.\cer.ps1 guard remove --scope project --project-root $Project --json
```

重新审查并加载旧定义；中间不宣称仍有运行时拦截。任何同期外部修改都应保留并人工
协调。本包对单个文件使用原子替换，不承诺多文件断电事务，也不是恶意本地进程隔离。
