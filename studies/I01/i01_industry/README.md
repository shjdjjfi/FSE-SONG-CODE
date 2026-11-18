# I01 FSE 2027 Industrial Follow-up — CPU-only, auditable public evidence

本目录是原始 120 项目 × 12 目标环境实验的**独立增量研究**，2026-11-14 冻结。目的：把“上游固定版本 wheel 是否可用”推进到真实开源消费者约束、真实软件项目的有限测试、其他固定版本以及发行版 backport。请先读 `EXPERIMENT_PROTOCOL.md` 和 `I01_工业真实项目扩展实验报告.md`。

## 实验结果（均为实测或有来源的记录）

|证据层级|实际范围|
|---|---|
|公共消费者约束|7 个有唯一 commit SHA 的 GitHub 仓库，Pyfa 额外对比 2 个历史节点|
|原工程真实需求解析|15 个完整需求场景，附加 8 个单包对照；23 次 pip dry-run（14 成功）|
|实际安装与项目/包测试|10 个相互隔离的 CPU venv；9 组安装及对应检查通过；1 组安装失败|
|真实仓库 pytest|Mozilla Pyramid MultiAuth WebOb 1.8.10/1.8.11 各 43 通过；pypiserver 各 316 通过|
|额外上游修复事件|原始样本中 6 个 OSV 多 fixed 项目，新增 17 个版本 × 12 目标 = 204 次实际 uv 解析；**0 个净新增目标**|
|旧版厂商 backport|2 个 SUSE 公告中官方声明已修复的旧版 WebOb 二进制包；**未在 SUSE OS 安装或运行**|

请严格区分：`pip --dry-run` ≠ 安装；安装 ≠ 上游所有 CI；功能性 pytest 通过 ≠ CVE 已修；上游 PyPI 版本号 ≠ 发行版 backport 的安全状态。原始 120 个项目为分层抽样，7 个真实消费者是**有意选取的案例**，没有总体比例推断。

## 内容

```text
i01_industry/
  EXPERIMENT_PROTOCOL.md            # 结果形成之前冻结的实验协议
  source_manifest.json              # 公共 repo commit、文件哈希、OSV/PyPI 响应哈希
  snapshots/                       # 完整公开要求文件、官方 API JSON
  generated_requirements/          # 最小变更的真实清单实验条件
  consumer_probe_manifest.json     # 15 组完整需求 + 8 组根包对照
  consumer_pip_audit.jsonl         # 真正执行过的 pip dry-run 逐次记录
  dry_run_reports/                 # 成功解析的 pip --report JSON
  install_test_manifest.json       # 10 个逐版本安装/测试任务
  install_test_results.jsonl       # 逐任务、逐阶段退出码/哈希
  install_logs/                    # 完整命令+stdout+stderr，便于独立核对
  alternative_catalog_manifest.json
  alternative_metadata.json        # 23 个 OSV 固定版本 PyPI 原始数据索引
  alternative_preflight_276.json   # 23 × 12 wheel/Requires-Python 必要条件
  alternative_uv.jsonl             # 额外 17 × 12 实际解析结果
  alternative_results.json         # 72 个 first-vs-any target 的重算结果
  alternative_raw_pypi/            # 可查原始数据及 SHA-256
  vendor_backport_evidence.json    # SUSE/Debian 官方公告与证据边界
  figures/                         # 根据真实实验重绘的 PNG
  industry_summary.json
  I01_工业真实项目扩展实验报告.md
  collect_sources.py
  run_project_audit.py
  run_install_tests.py
  analyze_alternatives.py
  build_industry_report.py
  verify_industry.py
```

**刻意不包含** `sources/`（公开 Git 克隆，约 54 MB）、`venvs/`（本地环境，约 374 MB）、cache、`.git`、任何凭证、生产数据。运行 `collect_sources.py` 可重建 Git clones，按明确 commit 检出；**所有关键需求文件的 SHA-256 已在 snapshots 固定**，不依赖克隆即可审阅。

合并交付 ZIP 内还附原始不作修改的 `previous_offline_study.zip`（120×12 主研究）。原始 ZIP 文件的 SHA-256：

```
62950c93bbd3a830b9c05b6cf03857f48f0f3abb9e6fb6b8e149559abbc0b5e5
```

## 只复核已有结果（离线、无需安装数据库/GPU）

在已经解压的交付 ZIP 根目录运行：

```bash
python3 i01_industry/verify_industry.py
```

脚本检查 GitHub/OSV/PyPI 原始快照 SHA、依赖变更文件 SHA、每一条 pip/uv 唯一标识、真实安装日志字节及命令输出摘要、四组 pytest 成功记录、替代安全版 204 次结果和厂商公告条目。成功时输出 `industry_verification.json` 且 `all_pass=true`。这属于**工件一致性检查**，不是独立复跑全部实验。

欲检验原始 120×12 基线，可解压 `previous_offline_study.zip` 后运行其独立的 `verify.py`：

```bash
unzip -q previous_offline_study.zip
python3 I01_FSE2027_Full_CPU_Experiment/verify.py
```

要让后续脚本与原始代码的相对位置兼容，可以将已解压的 `I01_FSE2027_Full_CPU_Experiment/` 放到 `i01_industry/` 的**同级目录**，并命名为 `i01_full/`（仅是目录重命名，不改变任何文件）。

## 真正重跑 CPU 实验（需要公开互联网和 PyPI）

环境：Linux x86-64、CPython 3.12、`git`, `pip`, `uv`, `packaging`, `matplotlib`, `numpy`, `pytest`, `unzip`。另需 `requests` 等随相关仓库或脚本标明的依赖。系统网络必须能访问 GitHub、`api.osv.dev`、`pypi.org`；很多受限制环境不能复跑在线步骤。

```bash
cd i01_industry
python3 collect_sources.py
python3 run_project_audit.py
python3 run_install_tests.py
python3 analyze_alternatives.py
python3 build_industry_report.py
python3 verify_industry.py
```

**重要复跑细节：** 三个运行脚本把任务结果逐条追加到 JSONL，检测到已经完成的 ID 会跳过；**若要从头独立复跑，务必先复制一份整个目录作为新实验目录，且只从这份新副本中移走相应脚本生成的旧 JSONL、probe manifest 和虚拟环境**，避免同一实验中混杂新旧 PyPI 索引状态。不要删除已有原始日志。强制锁定真实 Python/依赖版本对完整再现非常关键——这里冻结了漏洞证据和需求文件，但 `pip` 仍会解析实时的其他 transitive 版本，故未来仍可能发生变化。源仓库 pytest 是特定选中子集；**不能说运行了 GitHub Actions 全套 CI**。

单独重算报告/作图不需要联网：

```bash
python3 i01_industry/build_industry_report.py
```

## 研究声明

- 所有案例仅使用公开 GitHub、PyPI、OSV、SUSE、Debian 数据和本地 CPU。没有私有企业数据、远程大模型、生产系统或 GPU。
- 用户可审阅 `install_test_manifest.json` 里的逐版本测试 Python、真实仓库 pytest 文件路径、以及 `install_logs/*__test.log` 的完整测试输出。
- `pypiserver` 中 WebOb 只在 WebTest 等测试链路被引入，**不代表 pypiserver 的生产服务必然受影响**。
- 未安装 RPM、未运行 OpenStack GUI/基础设施或 Apache Allura 全栈，不声称厂商二进制安全补丁被本地验证。
- 7 个目的性选取的消费者不是 7 家生产客户；全量投稿需扩大消费者样本、找可复现实际部署场景和评估真实维护成本。
