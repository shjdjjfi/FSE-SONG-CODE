# FSE 2027 Industry — 第六个 Idea（N08）实验执行报告

**研究题目**：Measuring Review Expertise After Cross-Team Code Moves  
**结果状态**：真实实验已执行、已验证、可复现；**论文投稿必需的独立专家真值与因果工业收益实验尚未完成**。  
**数据来源**：`bitwarden/clients`、`grafana/grafana`，GitHub 公开 PR、提交、历史 CODEOWNERS、评审及请求记录。  
**计算资源**：使用 CPU 和公开网络数据；没有使用大型服务器或 GPU。

## 一、研究对象和已执行规模

原始想法关注：代码跨团队迁移后，当前目录的 CODEOWNERS 路由是否遗漏了仍持有关键语义知识的旧团队专家？对高风险的早期后续 PR 增加限期旧/新团队评审，是否能以固定推荐预算提高真实专家覆盖率？

首先需要严格区分：**路径迁移、责任团队变更、真实评审者、真正懂该代码的专家**是四种不同事实，不能互相替代。本轮独立确认了前 3 类中的一部分，但还没有第四类的外部真值。

| 实验事实 | 数量 |
|---|---:|
| 已验证的真实仓库 | 2 |
| 迁移且责任团队发生减少/改变的事件 | 9 |
| 公开 Git patch 确认的跨路径 rename 映射 | 112 |
| 有人工 APPROVED / CHANGES_REQUESTED 的后续 PR（排除机器人提交） | 114 |
| 实际代码文件在目标模块有改动的后续 PR | 102 |
| 事后探索性筛选的聚焦代码 PR | 58 |
| 可见公开评审请求事件 | 369 |
| GitHub REST API 与网页评审标签交叉检查 | 9/9 相符 |
| 实际已合并的负控事件 | 6；未发生错误增配 |
| 控制单元测试 | 9/9 通过 |

### 可追查的迁移事件

| 迁移 PR | 代码子系统 | 确认的 rename 对 | 迁移性质 |
|---|---|---:|---|
| [Bitwarden #10818](https://github.com/bitwarden/clients/pull/10818) | Biometrics | 8 | Platform → Key Management |
| [Bitwarden #11709](https://github.com/bitwarden/clients/pull/11709) | Key rotation | 5 | Auth → Key Management |
| [Bitwarden #12407](https://github.com/bitwarden/clients/pull/12407) | Lock UI | 3 | Auth → Key Management |
| [Bitwarden #12927](https://github.com/bitwarden/clients/pull/12927) | Premium UI | 2 | Vault → Billing |
| [Bitwarden #13285](https://github.com/bitwarden/clients/pull/13285) | Cryptographic functions | 2 | Platform → Key Management |
| [Bitwarden #14571](https://github.com/bitwarden/clients/pull/14571) | Reporting | 52 | Tools → Data Insights & Reporting |
| [Bitwarden #14987](https://github.com/bitwarden/clients/pull/14987) | Card component | 9 | Tools → Data Insights & Reporting |
| [Bitwarden #15093](https://github.com/bitwarden/clients/pull/15093) | Layout components | 10 | Auth → UI Foundation |
| [Grafana #104424](https://github.com/grafana/grafana/pull/104424) | Alerting notifications | 21 | 原来同时由 App Platform 与 Alerting Backend 负责，迁移后仅由 Alerting Backend 负责 |

所有事件均检查迁移 PR 的 `merged_at`，以准确 SHA 取前后 CODEOWNERS，并验证至少一组明确的旧目录→新目录文件 rename。完整 112 对映射及快照哈希在 `data/events/`；事件选择不具有随机代表性。

## 二、已执行实验设计

### RQ1：哪些后续 PR 真正落在迁移边界？

- 对每个事件，以真实合并时间为边界，向前读取 365 天旧目录的提交历史、向后读取 365 天新目录提交历史。
- 取最多 12 个最近的旧路径 PR 作时间安全训练池、最多 20 个最早且满足条件的后续 PR 作评估池。仅使用 **在该 PR 开启前已完成合并**的历史 PR 的评审者。
- 实际 PR 作者不允许作为候选评审人；机器人作者 PR 不进入测试集。
- 原始样本包括后续路径命中；代码筛选要求目标目录源码中有真实 diff hunk；事后聚焦筛选进一步要求目标模块占整个 PR 改动文件的至少 10% 且整个 PR 不超过 100 个改动文件。

结果：114 个后续评估 PR 中，102 个具备目标代码改动。58 个满足事后聚焦条件。**“有源码改动”不等于“经专家确认的实质语义变更”**，后者还需人工标注。

### RQ2：固定 K=2 推荐预算下，能否覆盖更多历史上真实参与评审的人？

对照方法统一使用相同、时间安全的数据。最终评价标签是 GitHub 上在 PR 合并之前提交 `APPROVED` 或 `CHANGES_REQUESTED` 的真人账号；指标为对这个**观测集合**的 Recall@2，按迁移事件做宏平均。

| 方法 | Event-macro Recall@2 |
|---|---:|
| 采样历史评审者流行度 | 7.2% |
| 新路径历史（Current-path） | 30.1% |
| 旧路径历史（Source-only） | 16.5% |
| 永久路径继承（Git-follow） | 25.0% |
| 180 天半衰期历史继承（Recency-follow） | 28.4% |
| 采样工作负载惩罚历史继承 | 23.0% |
| **限期 180 天旧/新知识移交** | **33.3%** |

移交方法的事件级 bootstrap 95% 区间为 **[25.9%, 40.3%]**。相比 Current-path 提高 **3.2 个百分点**（双侧事件级精确符号翻转 p=0.539）；比永久 Git-follow 提高 **8.3 个百分点**（p=0.125）；比 recency-follow 提高 **4.9 个百分点**（p=0.188）。不作多重检验意义上的显著性声明。所有方法均排除了当前 PR 作者。

**研究判断**：预设的是相对于最强等预算基线提高至少 **10 个百分点的独立专家覆盖率**。这一目标并未被证明：主结果不仅缺少独立专家标签，对最强路径历史对照也只有 3.2 个百分点的观测评审者召回提升。

### RQ3：推荐人数、消融、样本定义是否稳健？

| 主样本推荐预算 | Current-path | 180 天移交 | 改善（百分点） |
|---:|---:|---:|---:|
| K=1 | 19.7% | 16.1% | **−3.6** |
| K=2 | 30.1% | 33.3% | +3.2 |
| K=3 | 32.9% | 35.6% | +2.7 |
| K=5 | 43.7% | 42.4% | **−1.3** |

| K=2 样本口径 | PR | 事件 | Current-path | 180 天移交 | 提升（百分点） |
|---|---:|---:|---:|---:|---:|
| 全部路径命中 | 114 | 9 | 30.1% | 33.3% | +3.2 |
| 确有目标源码改动 | 102 | 9 | 31.5% | 37.2% | +5.6 |
| 聚焦源码改动（**事后探索**） | 58 | 7 | 37.2% | 44.2% | +6.9 |

不同时长的移交窗口的 Recall@2：0 天 30.1%、30 天 32.7%、90 天 31.8%、180 天 33.3%、365 天 29.2%。这一时长扫描是对已经观测过的数据做的敏感性实验，**不能在同一批测试集上挑选最高分窗口再声称独立验证**。

K=1 和 K=5 均出现反向结果；因此不能概括为“移交方法在各种评审预算下稳定优于基线”。

### RQ4：实际评审请求是否断开了旧知识？

公开 PR 网页实际抽取出 **369 个评审请求事件**（包括重复请求）。在 114 个后续 PR 中：

- 110 个出现 GitHub 的匿名团队代码所有者请求；此类记录只显示“a team”，无法还原历史团队成员名单。
- 113 个存在具名个人评审请求。
- 60 个在 PR 开启后 72 小时内具名请求过某位旧路径历史评审者。
- 86 个确实收到过旧路径历史评审者的正式评审。
- 12 个既没有可见的旧路径历史评审者具名请求，也没有其正式评审。

**12 个“未观察到旧评审者接续”的 PR 不是 12 次专家漏评证据**：旧路径历史评审者未必具备该 PR 需要的独立专家资格，GitHub 匿名团队请求中也可能涵盖了这些人，且贡献人数、可用性、候选 PR 差异尚未控制。

观测到的首次正式人工评审时间中位数为 **2.75 天（111 个可用 PR）**。没有上线候选策略，也没有随机分组，因此不能由此估计减少评审延迟多少小时。

### RQ5：负控和来源质量是否过关？

独立使用 6 个真实已合并 PR：Grafana 的同团队目录迁移（#114006、#110257、#105548）、只涉及测试夹具的跨团队迁移（#100371）、仅改 CODEOWNERS 不迁移代码（#114837），以及 Bitwarden 仅改 CODEOWNERS（#16500）。资格门控在这 6 个场景均没有产生旧专家额外增配：**0/6 错误触发**。这只能检验门控行为，不能证明推荐准确性。

为检验网页解析没有捏造评审，抽样 9 个跨事件 PR 与独立 GitHub REST `/pulls/{id}/reviews` 核对，正式人工评审者集合 **9/9 完全一致**。用于研究的原始源链接、快照 SHA-256、程序和断言均已保留。

## 三、投稿完整度与不可回避的缺口

| 论文必需证据 | 状态 | 下一步的实际工作 |
|---|---|---|
| 真实团队代码迁移、历史 ownership 和可追溯 PR | **完成** | 已覆盖两仓库九事件 |
| Git 历史和正式人工评审时间安全回放 | **完成（观测性）** | 更大随机项目样本仍有必要 |
| 多基线、固定预算、窗口与 K 消融 | **完成（基于可见样本）** | 需要完整的组织级工作量与团队用户信息 |
| 负控、图表、统计检验、代码可复现 | **完成** | 加入后续独立验证项目 |
| 对 PR 所需旧/新领域知识的**独立专家真值** | <escape>未完成</escape> | 至少两位彼此独立的评审人，盲审并记录可证伪依据；模板已准备 228 个空白评价行 |
| 历史团队成员身份、真实 CODEOWNERS 分派基线 | <escape>未完成</escape> | 取得合法可验证的历史成员/请求事件；不能猜测私有团队成员 |
| 与完整 Git 历史、现有强 reviewer recommender 和工业负担模型对照 | <escape>部分完成</escape> | 目前为路径历史、时间衰减、采样工作量版本；不是完整组织级替代 |
| 可证实的工业节约、评审质量和延迟收益 | <escape>未完成</escape> | 企业合作方或未来前瞻性随机/分阶段部署，不能从当前回顾数据推出因果结论 |

**严谨结论**：研究已从 SCREENED 推进到真实、多事件、双项目、可复现的**探索性证据阶段**；但依据原始方案的止损规则，现有表现不足以支持正向论文核心主张。不应将该 Idea 直接包装成已经满足 FSE 2027 Industry Track Long Paper 审稿要求的完整实证论文。

如果继续推进，建议先冻结 `BLIND_EXPERT_ANNOTATION_QUEUE.csv` 的人工标签，并新增独立项目，再用相同脚本进行已预注册的测试；若仍无法相对强基线证明 ≥10 个百分点独立专家覆盖改善，应调整研究主张或放弃正向效果型投稿。

## 四、实验工件

- `metrics.json`、`predictions.json`：机器可读的主结果和各 PR 预测。
- `PAPER_TABLES_AND_LIMITATIONS.md`：事件级结果、事件级区间及精确检验。
- `ROBUSTNESS_TABLES.md`、`robustness.json`：K、工作量、路径筛选、时间窗与仓库分析。
- `request_audit.json`、`negative_controls.json`、`rest_review_validation.json`：来源核查、负控、实际请求。
- `figures/`：自动从真实观测生成的 SVG/PNG 科学图。
- `BLIND_EXPERT_ANNOTATION_QUEUE.csv`、`EXPERT_ANNOTATION_PROTOCOL.md`：两名独立评审人的**空白**专家真值任务单与编码规则。
- `../src/`、`../tests/`、`../data/`：全部可运行脚本、测试、标准化来源记录和哈希。

来源规则：[GitHub CODEOWNERS 官方文档](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)；[Bitwarden 官方评审流程](https://contributing.bitwarden.com/contributing/pull-requests/community-pr-process/)；每个真实迁移与负控均有具体原始 PR URL。
