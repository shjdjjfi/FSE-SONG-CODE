# N04 新增研究实验（2026-11-15）

**题目：Recovering Flaky Test History Across Test Identity Changes**  
**目的：回应原研究 STOP-1（真实隔离动作）、STOP-2（强基线）、STOP-3（跨仓库拆分/语义变化）。**  
**结论：已完成公开真实 CI 决策证据审计、独立重命名压力实验、跨仓库真实版本执行。仍不能诚实宣称三个投稿门槛全部通过：缺失真实 CI 的逐测试后续结果；新的方法虽比简单基线高，但为事后探索，项目层面优势不显著；真实错误继承的生产后果尚未观察到。**

## 1. 证据分级（避免将模拟误称为真实）

| 证据等级 | 本轮获得内容 | 可以证明 | 不能证明 |
|---|---|---|---|
| A：已合并公开 CI 管理源码 | 6 个 GitLab 合并 MR、3 个 Aspire 合并 PR，逐文件审计 `quarantine` 改动 | 项目实际提交了隔离/解除隔离决策；单一 GitLab 测试完整添加—移除闭环 | 真实 CI 执行每次是否失败、失败次数降低、历史映射产生收益 |
| B：维护者对 CI 历史的公开陈述 | Aspire PR #13874 声称 25 个稳定测试、159 次运行零失败；#14040 声称 11 个稳定测试、215 次运行零失败 | 开发者依据重复运行结果采取解除隔离行动 | 我们独立重算了每一个 CI job 的 159/215 次结果 |
| C：真实 Git 历史版本在本机执行 | Click、MarkupSafe：4 个独立历史变更，8 个源版本，80 次 pytest 调用，4,990 条 JUnit case 行 | 变更在真实工程确实能执行，拆分/移动/扩充语义可观察 | 这些运行就是当年原项目的 CI；观察到了真实偶发失败 |
| D：公开真实重命名标签 | ICPC 2021 CC BY 4.0 的 Excel：293 个独立方法重命名 ID | 用不同于原基准的重命名数据检验名称算法 | 可以证明跨时间 *flaky quarantine state* 可以安全继承 |
| E：可控反事实 | 新旧 `pytest` 缓存测试、FTW 真正结果上的人工缓存重置（前次包） | 机制失败/反事实代价及相关边界 | 生产 CI 部署中的因果收益 |

所有结果从公开代码与数据下载；没有访问、修改或部署到他人的 CI 环境。访问 GitHub issue API 的 HTTP 403 和 GitLab note 的 HTTP 401 作为**不可得证据**处理，没有规避权限限制。

## 2. RQ1：真实隔离/解除隔离决策与后续处理

### 2.1 GitLab：同一个 RSpec 的三步连续历史

从 GitLab 公开 REST API 获取 MR 元数据和文件 diff，记录原始响应 SHA-256、MR 编号、合并时间、添加/删除的隔离语法，以及测试名称。

| 日期（UTC） | 合并 MR | 真实已合并行动 | 证据 |
|---|---|---|---|
| 2024-08-19 | [!162803](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/162803) | 在 `user_reverts_merge_request_spec.rb` 中给 `reverts a merge request in a new merge request` 添加 `quarantine` | 原始差异 1 行添加，关联 [issue #457549](https://gitlab.com/gitlab-org/gitlab/-/issues/457549) |
| 2024-08-26 | [!163832](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/163832) | 修改 Sidekiq 在 JS/feature spec 中“事务内入队”检查；开发者解释这类场景会产生假阳性 | 3 个受影响文件，代码和相应规范测试；属于问题修复，不是身份迁移 |
| 2024-08-27 | [!164022](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/164022) | 移除**同一个测试**上的 `quarantine`，MR 明确说明基于 !163832 的修复解除隔离 | 同一路径、同一测试描述、源代码注解删除 1 行 |

这是一条真实工程中的 **add-quarantine → fix cause → unquarantine** 事件链，而不是人工安排的测试。自动隔离 MR !162803 的正文称该测试故障数量达到 flakiness 95 百分位附近的自动触发标准；!164022 解释了具体 `EnqueueFromTransactionError` 症状。

**严格结论：**合并差异证明了源仓库隔离状态变化与技术上的补救动作；我们没有拿到该 RSpec 在解除隔离后逐个流水线的执行结果，不能计算“失败率下降多少”或归因于 N04 的身份迁移。

### 2.2 额外真实隔离案例与第二个独立 CI 工程

GitLab 的另外 4 个合并事件（加上上述 2 个共 **6**）：

- [!149942](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/149942)：移除 2 行自动合并测试的隔离标记。
- [!155883](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/155883)：增加 1 行长期隔离标记。
- [!195179](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/195179)：在修正 foreign-key 测试期望时移除 1 行隔离标记。
- [!228726](https://gitlab.com/gitlab-org/gitlab/-/merge_requests/228726)：修正 `new_project_spec.rb` 的上下文定位并移除 3 行隔离标记。

第二个独立真实工程是 Microsoft Aspire，其仓库以 `[QuarantinedTest(...)]` 表示隔离，并有自动/周期性运行相关工作流。

| 已合并 PR | 开发者公开运行证据 | 从实际 diff 确认的注解删除 | 证据约束 |
|---|---|---:|---|
| [#13874](https://github.com/microsoft/aspire/pull/13874)，2026-01-13 | PR 标题称 **25 个测试、159 次运行中零失败**；正文还包含 150 次的其他上下文 | 17 行 | 一个注解可对应多个参数化测试；“25 个测试”与“17 行注解”不是同一计数单位 |
| [#14040](https://github.com/microsoft/aspire/pull/14040)，2026-01-21 | 标题称 **11 个测试、215 次运行中零失败**；正文包含 180 次等其他说明 | 11 行 | 尚未获取全部逐次 CI 原始记录 |
| [#9023](https://github.com/microsoft/aspire/pull/9023)，2025-04-29 | 解除若干测试隔离，正文出现 100 次的上下文 | 4 行 | 不把 100 次简单视为全 4 个测试共同的完整样本 |

共审计 **9 个已合并、公开可核验的源码层面的隔离/解除隔离动作**（GitLab 6、Aspire 3），但这些行动均没有直接应用 N04 的历史转移方案。它们主要证明**工业场景真实存在、时序可追踪**，不构成方法因果实验。

技术结果存档：`results/real_ci_events/public_event_ledger.json` 和 `gitlab_fix_action_chain.json`。前者记录公开 API 请求 URL、响应 SHA-256、时间及失败权限状态；后者确证具体三步闭环。

## 3. RQ2：超强简单基线下，是否还有可验证的改进空间？

### 3.1 原先方法的定量约束

原始独立整理的 Python 测试迁移基准：875 对清洗后迁移，其中 842 对有同提交候选干扰，13 个项目，种子 17、29、43；每种方法评测 2,526 次“目标存在”与等量“目标不存在”判定。候选来自**同一真实开发者提交中的其他目标测试**；target-absent 是人工移走真正候选的控制构造。

| 策略 | 恢复率 | 错误转移率（合并在场错误与缺失目标错误） | 单位代价 C5¹ | 类型 |
|---|---:|---:|---:|---|
| 精确方法名 `method_name` | 96.44% | 0.71% | 0.107 | 冻结原基线 |
| 精确方法名＋源码同名打破歧义 | **97.39%** | **0.71%** | **0.097** | 新增的更强、仍很简单的基线 |
| 条件式名字规范化回退 `hierarchical_case` | **98.22%** | **0.71%** | **0.089** | 本轮事后设计的探索方法 |
| 条件式规范化＋严格源码回退 | 98.34% | 0.93% | 0.110 | 探索性消融；更高恢复率但成本变差 |
| 原探索 `guarded_fallback` | 97.86% | 1.27% | 0.148 | 更多错误继承，不能称为更优 |

¹ `C5 = (未正确恢复数 + 5 × 错误转移数) / N`，其中错误转移数合并目标在场与缺失目标两种情况；只作**敏感性代价**，并非实测工程师工时。

`hierarchical_case` 的两阶段规则是：(i) 用源码相似度打破**完全相同方法名**间的歧义，阈值从其他 12 个项目留一校准；(ii) 仅当第一阶段拒绝时，允许对确实只是大小写/下划线不同、且源码序列相似度 ≥0.75、token Jaccard ≥0.60 的候选做安全回退。`hierarchical_case_content` 又允许近乎逐 token 相同的其他改名，但错误率上升。

与原方法名基线比较，`hierarchical_case` 多正确恢复 **45 / 2,526**，提升 **+1.78 个百分点**；与新的**最强简单基线**比较，只多正确恢复 **21 / 2,526**，即 **+0.83 个百分点**。在 13 个**项目级**配对 bootstrap 下，对最强简单基线的 95% 区间为 **[0.00, +5.69] 个百分点**，包含零。种子是相同项目的候选再采样，不是独立样本数。

**预注册警告：**新增规则是在看过原始项目结果后设计的。即使每个留一折的阈值只用其他项目数据，此处的模型族选择依然**事后探索**，不得作外部独立验证。方法还是朴素字符串、源码匹配，并没有与真正的 `TestRefactoringMiner` 等已发表强工具直接跑同一个 Java 评价任务；目前也不能提出令人信服的新颖性主张。原目标“提高 ≥15 个百分点”在基线已经 96.44% 的样本上，理论上最高也只有 **+3.56 个百分点**，不可达。

### 3.2 真正不同的公开重命名数据集（ICPC 2021）

另从 [Peruma 等人，ICPC 2021 公开数据，Zenodo DOI 10.5281/zenodo.4608143](https://zenodo.org/records/4608143) 读取 `ICPC2021-Public.xlsx`，下载 SHA-256 为 `029c7c46c56bdb157076b67a91f7505b718d5e75216e30418ca0b294b64e4969`，CC BY 4.0。原表跨 7 个 Pattern Sheet 有 **398 行**，同一 refactoring ID 在不同 sheet 重复，正确去重后为 **293 个不同改名事件**；不应虚增为 398 个独立个案。

用旧测试名和真实新测试名构建 16 候选名的**名称专项压力测试**：每个事件有自己的正确后名、来自其他真实改名事件的困难干扰名，另外用删除正确候选模拟目标缺失；种子 17/29/43，5 折按 refactoring ID 拆分。样本含旧、新名，没有可运行的测试 body、项目时间线或真实 quarantine label。

| 名称策略 | 真实改名关联恢复率 | 合成缺失+在场综合错误关联率 | 解释 |
|---|---:|---:|---|
| 旧名严格等于新名 | 0.00% | 0.34% | 所有样本都是重命名 |
| 忽略 `test` 前缀与下划线大小写 | 20.82% | 0.68% | 可以覆盖形式改名，但仍很有限 |
| 模糊编辑相似度 | 55.97% | 2.56% | 超出 2% 错误目标 |
| 词集合 Jaccard | 39.25% | 2.22% | 同样超出 |
| 编辑＋词汇混合 | 55.29% | 2.05% | 接近但仍略高于门槛 |
| 混合＋否定极性警告门控 | 56.66% | 2.05% | 同样未通过风险门槛 |

记录中检测到 **15 个仅基于名字的否定极性变化警告**，如 `shouldFailIfFieldTypeIsNotValid` → `shouldNotFailIfFieldTypeIsNotValid`，或 `stringConverterNotCalledForString` → `stringConverterCalledForString`。此类变化可能改变历史失败的意义，但**不能仅凭名字就宣称行为已反转**；这正是必须保守处理和进一步动态验证的边界。

**不能把该 293 项结果称为留项目验证**：公共 Excel 只给出 refactoring ID 与名字，项目级身份/可执行 Git 修订保存在 1.8 GB SQLite 文件中，未下载解析。5 折按 ID，可能存在同项目跨折泄漏。它属于独立数据源上的**命名规则压力诊断**，而非新方法性能的项目级确认。

## 4. RQ3：真正的仓库版本、测试拆分与语义变化

### 4.1 四组全真实 Git 源码对比

用 `git worktree` 固定开发者历史提交前后版本，`PYTHONPATH` 指向各自仓库 `src`（杜绝错误地使用系统安装的同名包），同一 `pytest==8.4.2`/Python 3.12 环境、关闭自动外部 pytest 插件，局部执行指定测试。**每个版本重复 10 次**，JUnit 测试行及结果全部保存。

| 仓库与历史提交 | 对应实际变更 | 旧版每轮结果 | 新版每轮结果 | 次数与结果 |
|---|---|---:|---:|---|
| [pallets/click@7c7ec36](https://github.com/pallets/click/commit/7c7ec36354f49d1a092cb077fa4881ea4d70ba01)，2025-09 | 原 `test_with_resource_exception` 同时处理普通与 nested resource，开发者把后者抽成新的 `test_with_resource_nested_exception`；**单个测试方法 1→2** | 1 passed | 2 passed | 各 10 次 |
| [pallets/click@7ecc8d7](https://github.com/pallets/click/commit/7ecc8d7ee4a2e5c0732d6551baeb7597b7a73ade)，2026-09 | `tests/test_types.py` 拆进多个模块，**模块拆分 ≠ 单用例拆分** | 75 passed | 67 passed | 各 10 次；执行范围仅分别为旧 `test_types.py` 和新 `test_types/` |
| [pallets/click@9ab346f](https://github.com/pallets/click/commit/9ab346f6b57f2c99388b4e9db58a0961bc3027c8)，2026-07 | `tests/test_utils.py` 拆进 13 个测试源文件（外加 `__init__.py`） | 148 passed | 148 passed | 各 10 次；32 个源码测试函数有唯一相同 AST-body 的 1:1 搬迁 |
| [pallets/markupsafe@e49d257](https://github.com/pallets/markupsafe/commit/e49d257126d09937b1bf5e2b2173238df729fb13)，2022-06 | 同名 `test_escaping` 新增多行 HTML 注释、标签内换行的覆盖；**逻辑改变但名字不变** | 24 passed + 5 skipped | 24 passed + 5 skipped | 各 10 次 |

共计：**4 组真实历史变更 × 前后两版 × 10 次 = 80 次 pytest 调用、4,990 行真实 JUnit case 执行记录**，所有调用正常结束，记录中除了预期跳过没有失败。这些都是本机从真正历史源码执行的结果；不是从原项目当年 CI 下载的日志。

`click-case-split-2025` 的解析器使用 AST 独立检查了 `base_val_nested` 逻辑：旧版位于一个 `test_with_resource_exception`，新版该逻辑**从旧名测试中移走**，进入新增 `test_with_resource_nested_exception`。严格 1:1 历史继承应**拒绝/人工审查**，否则原测试的旧隔离含义可能被错误地全部赋予其中一个新子测试。这里**展示的是安全性风险与避免转移的规则**，不是当年 CI 已经发生的错误转移。

`markupsafe-semantic-extension-2022` 展示另一种风险：测试名、路径完全不变，但断言覆盖的输入范围已经扩展。仅依赖名称匹配的工具会无条件继承历史；严格工具应要求差异审查。不过“覆盖扩展”**不等于**旧失败历史失效：我们没有真值标签证明继承一定错误，因此该条没有被标成真实错误转移。

Click `utils` 拆分的源码证明：前后各 32 个函数，**32 个均具有唯一同 body AST 指纹映射，且文件路径发生迁移**，这是正面的跨版本身份连通性证据。`types` 拆分中旧 20/新 21 个解析函数、11 个唯一同 body AST 的跨文件映射，另有增删改，需要拒绝不确定部分。

此外，前版包中独立的 [TooTallNate/Java-WebSocket](https://github.com/TooTallNate/Java-WebSocket) 已真实执行 2018 年一个版本转换前后 **30×40 + 30×40 = 2,400 次** JUnit case，40 个 source-derived 映射以及 27 个 IDoFT 标注核对。本轮新增加的 Python 结果，使总计可审计的真实本地执行次数达到 **7,390 条逐测试观察**，跨 **3 个不同源码仓库**，但并非 7,390 条相互独立的迁移案例。

## 5. 可复现性、统计与安全边界

- 真实 CI 事件：`src/ci_event_audit.py`、`src/ci_event_chain.py`，生成 `results/real_ci_events/*.json`。若 GitHub public API 限流或受保护，程序留存 HTTP 状态，不调用其他账户、不伪造后续测试结果。
- 真实 Python 仓库运行：`src/cross_repo_real_replay.py`，`results/cross_repo_pytest/` 包含所有进程和逐测试 CSV、源 AST 指纹、固定 revision、摘要。需要本地克隆原项目并按脚本的 `CASES` 建立对应 worktrees；ZIP 不重新分发第三方源码。
- 新基线：`src/strong_baseline_extension.py` 和 `src/hierarchical_history_linker.py`；输出每条预测、阈值、方法分组和按项目 bootstrap。
- 公开重命名数据：`src/external_rename_probe.py`；输出全部 879×6 种方法预测、5 折阈值与 15 个潜在极性变化的匿名名字记录。原 XLSX 版权归研究作者，需从 Zenodo 自行下载；本包只归档衍生分析。
- 独立离线核验：`python3 src/verify_frozen.py` 将实际 CSV 重新核对统计，并验证 **151** 个文件 SHA-256；`python3 -m unittest discover -s tests -v` 含新增回归测试。无 GPU、大型服务器和付费 API。

所有程序用公开观察数据，不向任何 GitLab/Aspire CI 写入、更不触发商业 CI。相对于真实历史流，不够充分的推断都明确标记为**反事实、开发者自述、探索式算法或缺失**。

## 6. FSE 2027 Industry Track 最终判定（本轮）

| 原定问题 | 本轮成果 | 投稿主张状态 |
|---|---|---|
| (1) 没有真实 CI 隔离/解除隔离记录 | **动作记录已补上**：两个真实工程、9 个合并变更，GitLab 有三阶段闭环；Aspire 有可引用的运行次数据述 | **仍缺关键因果证据**：测试级生产运行轨迹与解除隔离后的真实错误率/工时；只能声称动作真实存在 |
| (2) 未战胜最强简单基线、+15pp 不可能 | **改善了基线**：97.39% vs 96.44% 同错误率；事后分层策略 98.22% vs 97.39% 同错误率；新增 293 个独立真实改名压力点 | **仍不可称稳健战胜最强基线**：+0.83pp 的项目区间包含零，且规则选择事后化、缺 published TestRefactoringMiner 同场比较 |
| (3) 无独立跨仓库真实执行案例及拆分/语义变化 | **完成实际源码执行**：4 组 Click/MarkupSafe 历史变更、80 次、4,990 行，加前版 Java WebSocket 2,400 行；观察方法级 1→2 拆分和同名语义扩展 | **仍欠缺**：现实生产中“错误隔离历史被继承”后的观察结果；目前只有源码风险与政策性拒绝迁移，无现场因果数据 |

### 最适合论文的真实、可辩护主张

> We investigated test-history lineage under real test-identity changes using 9 merged quarantine-management changes from two independent CI-hosted projects, historical Python and Java test executions, and a name-evolution corpus. We found that an exact-name baseline is much stronger than anticipated, and that simple context-aware tie-breaking and conservative case-format normalization yield only modest exploratory gains; one-to-many splits and semantic extensions expose unresolved safety risks.

**不允许写成已证实的主张：**“我们提升了生产 CI 15pp”“本方法减少 159 次 CI 中的失败”“所有真实拆分均实现无错继承”“方法在工业强基线上显著领先”“原项目 CI 的真实错误继承已经发生”。若以“新的上线隔离工具显著改进工业成本”为核心的 Industry 长文，判定仍是 **NO-GO**；下一轮必须获得合法、可审计的测试级生产时间序列和独立封存项目验证。
