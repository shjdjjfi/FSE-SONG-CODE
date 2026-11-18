# 第四个 Idea（N04）初版实验报告与投稿适格性审计

> **更新提醒（2026-11-15）：**本文件保留第一次实验审计及其初版数据口径；后续已取得与真实文件级测试拆分相配对的 Fusion quarantine 决策、GitHub Actions 前后运行元数据、4 个独立项目的新目标重构 oracle 和 Git Riptide 文件改名核验。请先阅读 **[ADDENDUM_20261115_ZH.md](ADDENDUM_20261115_ZH.md)**。因此本文件中“无任何配对隔离案例”和“独立项目无新目标”的叙述只适用于**第一次实验数据范围**，不代表扩展后的全包证据。原始 4/9 不安全继承和 ≤2% 未认证结论保持不变。

**题目：Recovering Flaky Test History Across Test Identity Changes**  
**版本：初版基线 2026-11-15；实验性质：公开证据、真实代码回放与有限人工审计；本章没有真实生产 quarantine 决策回放，新附录另有 1 个公开源码配对案例。**

## 0. 结论先行

**初版完成可复现的技术机制实验、7 项主要 Java 数据对照、2 个真实 Git 版本的 JUnit 回放、公开 CI 数据审计、三种种子与迁移事件聚类不确定性分析。新附录另行覆盖真实 quarantine 及独立后继目标。全部证据合并后，仍不能证明原构思规定的 FSE 2027 Industry Track 安全和工业收益门槛。**

这是由实测结果和证据可得性决定的 stop/go 结论，并非实验未执行：

1. 与固定 Git 文件路径/方法名基线相比，基于方法体与上下文的保护性策略在 **34 个有来源推断目标的独立方法候选**中从 **14/34（41.2%）** 提高到 **26/34（76.5%）**，表面增益 **35.3 个百分点**；但是对应 **9 个 IDoFT `Deleted` 标签中仍有 4 次错误继承（44.4%）**，无法达到预先规定的 ≤2% 风险上限。
2. 这 4 个 `Deleted` 案例均在源码上出现“类路径移动、方法名相同、方法体相同”的矛盾迹象，故又报告了 **未争议标签 0/5**，但这个子集太小：95% 双侧 Clopper–Pearson 上界为 **52.18%**，绝不能宣称达到 ≤2% 安全率。
3. **初版采用的 Test Flare CI 故障数据**没有 test quarantine 状态；新增附录已从别的真实项目找到一例隔离身份迁移及前后 CI 运行元数据，但尚无法估计因果意义的误重跑或 CI 成本收益。真实历史上的 6 个初版手工检查边界，迁移前均无可观察的 flaky 失败信号。
4. Java-WebSocket **前后各 3 次本地真实运行**观察了 240 条结果，研究代码在 27 个 IDoFT 旧测试身份与新参数化运行实例之间产生了 27 个一一对应的**候选链接**，但该特定 Java-WebSocket 实例仍无独立维护者认可的新实例 oracle，结果都是通过/跳过，不能证明继承 flaky 历史能够改善生产隔离决策。

**执行本构思自己的 stop-loss：在没有独立 quarantine 决策证据时，论文主张限于测试身份映射与 pytest cache 行为；不应把它包装为已完成的 Industry Track 论文。**

## 1. 研究问题、预注册规则与指标

| RQ | 询问 | 指标 | 当前可识别性 |
|---|---|---|---|
| RQ1 | 改名或迁移使多少历史 ID 失联？ | 独立身份继承成功率、ID churn | 可以探索性测量 |
| RQ2 | 源码、上下文、参数 ID 与图约束能否安全继承？ | 唯一目标恢复率、Deleted 继承率、组内误合并 | 可有限评估；FQN 目标不独立 |
| RQ3 | 多对一、拆分和语义改变如何影响误继承？ | 保守拒绝比例、实例碰撞数、负控 | 可测试机制与有限真实案例 |
| RQ4 | 在生产 CI 下能否减少无效 quarantine/重跑？ | 真实隔离错误、构建/时延成本、修复前后 | **初版不能**；扩展研究有单例真实动作，但无法估计方法的成本效益 |

评价规则沿用 proposal：同一错误继承上限 **≤2%** 时，确证历史恢复率相对于强基线至少提高 **15pp**。必须有独立 source→target 标签与观测到的 quarantine 状态才可检验这一条件。种子固定 **17、29、43**；对 IDoFT 以唯一迁移事件为聚类单位 Bootstrap，而不把同一次参数化事件的 27 个实例当作 27 次独立重复。

### 对照设计

1. Exact ID：原始测试 node ID 必须不变；零错误时也无法恢复改名。
2. Git path + same-method：文件重命名证据与方法名不变。
3. Name similarity：按方法名相似度选择，不检查语义断言。
4. Exact normalized body：方法体标准化指纹相同。
5. Name + context：方法名与路径或实现上下文。
6. Guarded lineage：唯一方法体或名称/上下文证据；拒绝未消歧的多个旧 ID 指向同一个新方法。
7. 消融：移除 body guard；移除 N→1 group guard。
8. Java 参数实例机制：在真实 JUnit 源码改造与运行报告里，以行为家族 + `@Parameterized` 索引产生唯一候选实例身份；仅对已固定的真实变更评估。

所有基线共享同一个候选集；此处 **guarded 的阈值属于探索性实现，未在外部数据冻结或校准**，因此不得宣称公正独立的调参后测试。

## 2. 数据来源、覆盖与流程

### D1 — FTW：真实开源代码的重复测试执行

- 源：Zenodo `10.5281/zenodo.10639030`（Regression-Test History Data for Flaky Test-Research, CC BY 4.0）。已下载 510 MB 发布压缩包并校验 MD5 `00e3f51ddd8ae8f92b62ceafe1130cce`；原始压缩包不进入本交付。
- 已解析 **330 个 `.csv.xz` 文件、11 条历史 track、4,654,230 条单次测试状态观测**；track 不是相互独立的开源项目，存在相同项目的多次重放。
- 各 track 报告中“有多个结果状态的测试 ID”加总为 65，**不是 65 个彼此独立的 flaky 测试或 65 个项目**。
- 所有源码顺序由 **Git 祖先拓扑**重建，不使用 FTW 在 2023 年重放时生成的执行时间戳作为提交序列。
- 主要本地人工审计来源：`apereo/java-cas-client` 与 `javadelight/delight-nashorn-sandbox`，合计 6 个旧方法案例、3 次唯一源码事件。两项目部分历史 track 重复，不重复计入 gold 数量。

### D2 — IDoFT：独立旧测试状态 + 源码推断候选目标

- 源：Illinois `TestingResearchIllinois/idoft`，固定 Git 提交 `4903dc9233eead4e4191c66f9ed0b14eea091052`；使用 Java Maven/Gradle 的原始 `MovedOrRenamed` 与 `Deleted` 标签。状态是**原始标注**，但目标新 FQN 大多需要由源码启发式推断。
- 从 **7 个源代码项目、15 个 Git 迁移/删除事件**得到 **74 个旧测试案例**。
- 按标签与可证据化的目标拆分：**34 个**具有单一候选的正例、**27 个**映射到新参数方法而无法在方法层面区分实例的组正例、**9 个**删除负例，另 **4 个**正例缺少可靠目标 FQN。注意这并非对 IDoFT 的随机样本，而是可从 Notes 找到具体迁移 SHA 且本地能解析 Java 文件的子集。
- 为避免“检测 SHA 距离变更几个月”导致错误比较，保存 `SHA Detected` 与 `migration^` 两版本，并标注旧方法是否在真正的迁移父提交里存在。1 个正例在该父版本已失踪，属于非邻接历史，不可当作简单一次 rename。
- 另取 **4 个独立库**为跨项目留出，仅抽到 **4 个案例**，其中 **3 个正例无法给出独立确认的目标 FQN**，故不存在可证明的留出集恢复率。该限制被保留在 JSON，不补造标签。

### D3 — Test Flare：真实 GitHub Actions 失败候选

- 数据来源：`test-flare/flaky-test-dataset`，固定 `b872ed937b7b811938e58b1a13bb3144882fda21`，Prefect 与 Home Assistant 两项目、四个快照文件。
- 按仓库 + `(run_id, run_attempt)` 去重：**62 次真实 CI 失败候选运行**；各仓库测试 ID 合计 **212 个**，其中 **4 个**存在本地复现阶段的 pass/fail 混合现象。快照之间有 **4 次重复 run**，已去重。
- 全部 **62 次**运行缺乏 quarantine 状态字段，而且表结构主要收集**失败候选**，不能把“未出现”解释为执行成功，更不能把本地复现成功当作历史 CI 通过记录。

### D4 — 真实运行的 JUnit 4 参数化迁移

- Java-WebSocket 迁移：`TooTallNate/Java-WebSocket@2ce6e6149d0ef44f4919e75326265c64c144a00f`，对 commit 的**直接父版本**及该版本分别执行 `Issue256Test` 和 `Issue580Test`；每个版本每个类重复 **3 次**。
- 老版本实际收集 20+20 个方法级实例/轮；新版本实际收集 20+20 个参数化实例/轮；**总计 240 条**真实 Surefire 结果：**迁移前 120 pass；迁移后 119 pass + 1 skip**。
- 对 IDoFT 标出的 27 个旧方法，根据 `runReconnectScenarioN → runReconnectSocketClose[N]`、`runReconnectBlockingScenarioN → runReconnectCloseBlocking[N]` 与 `runNoCloseBlockingTestScenarioN → runNoCloseBlockingTestScenario[N]`，得到 **27/27 唯一源和运行时可检查的候选实例**。Exact ID 为 0/27；只传递到新方法级标识会把 27 条历史混入 3 个组，不是合法的测试实例迁移。
- 本地 JDK 21 无法原样编译旧 `-source 1.6` 代码。临时构建目录将编译级别改为 Java 8，并排除 3 个无关的 CORBA 依赖测试/套件汇总文件以让目标类运行；**原仓库未修改，测试自身源码未修改**。此回放不能被描述为“未经修改的原环境”。

## 3. 主实验量化结果

下表是 **IDoFT 目标 FQN 由源码推断** 的探索性评估；某正例若无法可靠推断目标就不进入 34 个 positive 分母。原始 9 个 `Deleted` 标签始终保留作完整负例集，不在主表悄悄删除。

| 策略 | 34 个单目标正例找回 | 9 个 Deleted 中继承 | 在 27 个组例上误做“实例”继承 |
|---|---:|---:|---:|
| Exact ID | 0/34（0%） | 0/9 | 0/27 |
| Git path + same method | 14/34（41.2%） | 4/9 | 0/27 |
| Name only | 33/34（97.1%） | 8/9 | 27/27 |
| Body hash | 11/34（32.4%） | 2/9 | 27/27 |
| Name + context | 25/34（73.5%） | 4/9 | 0/27 |
| **Guarded lineage** | **26/34（76.5%）** | **4/9** | **0/27** |
| 消融：去掉 body | 33/34（97.1%） | 8/9 | 27/27 |
| 消融：去掉 group gate | 26/34（76.5%） | 4/9 | 27/27 |

对于 guard vs Git path + method 的正例恢复率差异，点估计为 **+35.29pp**；按**拥有正例的 7 个唯一迁移事件**执行 3 种种子、每种 3000 次有放回聚类抽样，95% 描述性区间 **[+10.81pp, +66.67pp]**。对于更强的 name+context，同样比较只有 **+2.94pp**、区间 **[0, +14.29pp]**。且 guard 和两种对应方法的原始 `Deleted` 继承率都是 **4/9**，所以不能利用高恢复率绕过 ≤2% 安全约束。

### 标签冲突不等于标签可擅自修正（新附录已增加独立 Git R94～R98 改名证据）

源码审计发现原始 9 个 `Deleted` 中有 4 个具备同方法名、相同标准化方法体和移动 Java 文件的强证据。按照 IDoFT 的标注说明，它们**可能**应被记为 moved，但新 fixture/运行环境也可能让逻辑身份变化。这里保留两种敏感性分析：

- 原始标签：guard 错误继承 **4/9 = 44.4%**，95% 双侧 Clopper–Pearson 区间 **[13.70%, 78.80%]**。
- 排除有源码冲突的标签：**0/5 = 0%**，但 95% 双侧确切区间 **[0%, 52.18%]**。这不是一个经过独立审计的新真值集。

甚至在理想的彼此独立、零错误情况下，要让双侧 95% 精确上界低于 2%，约需要 **183 个以上**独立的负例；若按迁移事件聚类、相关性明显，还需要更多。**本研究远未能统计认证 2%**。

### 两种额外现实检查

1. **手工 source diff gold（6 案例）**：3 个可安全继承，2 个删除，1 个语义不清楚的拆分。Body fingerprint 与 guard 是 **3/3 正确继承、0/3 负例误继承**；然而样本过小，且与简单 body fingerprint 持平，未显示新算法优势。
2. **pytest 8.4.2**：对三个不同测试名构造，每例缓存含一个失败节点；旧 ID 仍在时 `--lf` 收集 1 项；改名后旧缓存失效收集 3 项；明确修复缓存键后再收集 1 项。该实验展示真实工具行为，**未测量真实项目 flaky 迁移后隔离收益**。参见上游维护者问题 [`frankbria/codeframe#984`](https://github.com/frankbria/codeframe/issues/984)。

## 4. 初版工业效果回放为何仍无法成立（新配对案例见附录）

`src/replay_history_policy.py` 在 6 个手工 source gold 边界上，以冻结的**假设**规则回放“最近 5 个可观察源码版本失败比例 ≥5% 则建议隔离”。旧 ID 的历史窗口内 **0/6** 带有观察到的 flaky 先兆；因此历史继承与 exact-ID 的**假设隔离决策差异为 0/6**。这个零差异不说明方法无用，只说明实验缺少与真实 flaky 状态共时的可迁移身份事件。

可公开核验的工业隔离机制包括：

- Microsoft Aspire 的 `[QuarantinedTest(...)]` 标注，普通 CI 排除该属性，定期 quarantine workflow 分开运行；公开项目文档 [`microsoft/aspire/AGENTS.md`](https://github.com/microsoft/aspire/blob/main/AGENTS.md)。
- Apache Kafka 的 `@Flaky` 标签和 `KafkaPostDiscoveryFilter` 隔离机制；具体移除标签后的选择差异在公开变更记录中有说明；参见 [KIP-1090](https://cwiki.apache.org/confluence/spaces/KAFKA/pages/321719036/KIP-1090%2BFlaky%2BTest%2BManagement)。

在这一**初版数据范围**中，找得到隔离机制仍不等于拿到了在真实改名边界前后连续、可配对、可核验的隔离决策。新增 Fusion 案例已经取得可配对的文件级真实隔离动作，但不等于完成 N04 方法的工业效果测量；详见附录。

## 5. 统计与实现威胁

- **独立标签不足**：IDoFT 提供状态但未全量提供新实例标识；同一源码启发式既生成候选又参与评价，造成依赖性和选择偏差。
- **非随机抽样**：限定 Git Notes 可解出 SHA 的项目，而且 27 个组正例来自一组参数化事件；按行数做传统置信区间过窄。
- **语义等价难题**：方法体哈希相同不等于 fixture、配置、测试意图或 quarantine 约束相同；较高恢复率可能同时误继承。
- **重放与生产不同**：FTW 是后人离线重复跑历史版本；Maven 是现时 JDK21 兼容改造；pytests 是合成受控 fixture。都不是原始工业 CI 完整状态历史。
- **部分数据时间歧义**：FTW timestamp 不能替代 Git 提交顺序；IDoFT 检出 SHA 可能远早于修复 commit。
- **语义断言**：JUnit 参数 `[0]` 运行序号只是相似身份证据，不能保证旧 `Scenario0` 与新 `[0]` 在所有输入/fixture 上逻辑同一；手工 oracle 需要维护者或独立双人标注。
- **初版留出不足**：第一次 IDoFT 留出库仅 4 条且无确证正例目标。新附录另有 4 个独立项目、54 条人工验证的源码重构边，但只领先同名基线 1/54；更不能直接给出工业收益结论。

## 6. 需要哪些新证据才能改为 Go？

| 优先级 | 明确的实验交付 | 当前缺口 | 判定条件 |
|---|---|---|---|
| P0 | 两个以上真实项目中**同一测试**改名/迁移前后连续 CI 报告和隔离状态 | 无可独立核验的配对状态 | 公开 commit/CI run/annotation/owner 链接，旧新可配对 |
| P0 | 两名独立标注者审计旧→新测试实例、split/delete/语义改变 | 仅 6 个手工源码 gold | 盲化处理、分歧规则、可追溯审计 |
| P0 | 同一风险水平下测试/隔离策略比较：漏隔离、误隔离、时延、成本 | 实际处置动作缺失 | 原方案 ≤2% 误继承 + ≥15pp 恢复增益，含可靠区间 |
| P1 | 独立项目/时间留出及强基线 | 4 个 holdout 无可确证正例 | 多项目、跨时间、可回答的确证样本 |
| P1 | JUnit/Pytest 参数 ID、跨文件移动、1→N/ N→1 的真正实例级 oracle | 27 个候选为源码/运行时推断 | 维护者或人工独立核验，运行日志绑定 |
| P1 | 防错误继承的成本曲线、稳健性和大规模 CI 集成 | 未有工业持续运行 | 误继承损失、abstention coverage、实际 wall-clock/CPU |

以当前证据，推荐先写 **negative-result / reproduction package / empirical pilot**，不把它作为完整的 FSE 2027 Industry Track Long 稿结果。若能与现有使用 quarantine 属性的项目维护者协作，补齐 P0 后再重新计算与同风险上限的最强基线比较。

## 7. 再现方式与附件说明

- `results/idoft_evaluation.json`：**每条预测**、8 策略汇总、3-seed event bootstrap；`results/statistical_audit.json`：Clopper–Pearson 与配对差值。
- `results/idoft_migrations.json`：所有可选新 FQN、候选分数、前/后 SHA；`results/label_audit.json`：4 个原始标签冲突。
- `results/junit_parameter_migration.json`：27 个旧 ID 与新参数实例候选对应；`results/maven_replay*.json`：全部 240 个 Surefire 测试状态，完整编译回放状态。
- `results/ftw_histories.json`、`results/source_aligned.json`：重复执行数据、Git 来源顺序；`evidence/source_events_gold.json` 和 `results/source_gold_evaluation.json`：6 个手工案例及 baseline。
- `results/pytest_cache_replay.json`、`results/actual_history_policy.json`、`results/real_ci_audit.json`：隔离的机制、假设政策及真实 GitHub Actions 缺失标签审计。
- `results/idoft_heldout*.json`：留出项目不足的实际证据。`figures/` 保存 4 张 PDF/PNG 图。

本报告没有根据实验结果进行造假式“补齐”；凡“真实”“生产”“维护者确认”“显著改善”“满足 2%”之说，均附带可追溯的边界。研究结果可重跑并可被推翻。
