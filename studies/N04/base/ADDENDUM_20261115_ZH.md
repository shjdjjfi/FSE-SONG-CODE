# N04 后续实验：真实隔离决策、原始标签审计与跨项目独立测试

**更新时间：2026-11-15。证据状态：可重复核验的公开软件源码、版本化 quarantine 清单、公开 GitHub Actions API 记录、第三方重构标签。**

本附录补充先前 N04 数据包，针对三个阻塞问题进行新的实证研究。保留原来的 `4/9` 原始 `Deleted` 错误继承数值；本附录没有将没有数据的效益冒充真实测量，也没有重新训练模型以取得预设结论。

## 1. 第一个问题：找到了身份变化所对应的真实 quarantine 决策

### 1.1 公开 quarantine 历史挖掘

从 `Runfusion/Fusion` 的 `scripts/lib/test-quarantine.json` 的有效 Git 历史中重建隔离记录的新增、撤销和证据链接（源代码在 `src/mine_quarantine_ledger.py`）。这不是由我们生成的隔离策略；它是项目维护者实际提交的 CI 隔离名单。

| 统计项 | Fusion | trycua/cua |
|---|---:|---:|
| 解析成功的隔离清单版本 | 145 | 4 |
| 新增隔离记录的变更次数 | 264 | 3 |
| 从名单移除的变更次数 | 261 | 0 |
| 曾新增的不同隔离标识 | 215 | 3 |
| 新增记录附有 GitHub Actions 运行链接 | 104 | 0 |
| 同一次变更中，旧新标识共享失败运行证据的候选 | 1 | 0 |
| 无法解析的 Fusion JSON 历史版本 | 2 | 0 |

**重要区别：**名单移除不等于测试成功解除隔离。测试删除、过期、修复或政策变更都可能删除清单项，261 次不能说成 261 次恢复。104 次是带运行链接的*新增清单记录*，不能说成 104 次独立失败或被挽救的 CI。

数据：`results/fusion_quarantine_ledger.json`、`results/trycua_quarantine_ledger.json`。

### 1.2 与测试身份变化准确配对的 Fusion 真实案例

- **项目及真实提交：** [`Runfusion/Fusion@b545083`](https://github.com/Runfusion/Fusion/commit/b5450832494d24e4171acea606b4c022a5a8475b)，提交标题 `FN-7530: isolate flaky dist-barrel extension test`。
- **真实原始失败运行：** [GitHub Actions #28697507894](https://github.com/Runfusion/Fusion/actions/runs/28697507894)，提交者写明第 4/4 分片出现 5,000 ms 超时。
- **迁移前：**`packages/cli/src/__tests__/extension.test.ts` 在 quarantine 清单中，且实际 `packages/cli/vitest.config.ts` 将其列入排除名单；文件级排除连带阻止其他测试进入正常通道。
- **迁移后：** 一个 `it.skipIf` 测试被拆至 `extension-dist-barrel.test.ts`。清单随之指向新文件，配置仅排除新文件，原文件从排除名单释放。
- **独立源码核对：**旧新测试名称相同，相关 13 条断言源码行一致，新文件只有一个 `it` 测试声明。原文件源码测试声明数 **155→154**，新文件 **0→1**；这是静态声明数，并非 CI 运行时实际收集个数。提交维护者称约 68 项其他稳定测试恢复正常执行，**68 是维护者声明，未独立从 JUnit/Vitest 运行日志验证**。
- **原始失败证据连续：**前后 quarantine 原因均保留指向同一个 Actions 运行 #28697507894 的 URL。旧测试历史的文件名发生了变化，隔离动作随新的文件身份更新。

因此，前版“完全没有与身份迁移相配对的真实隔离决策”问题 **在实例层面得到解决**：我们获得了一个公开、可审计的文件级测试拆分与真实隔离身份迁移。但此案例是 **TypeScript/Vitest 文件级隔离**，不是 N04 Java 方法级工具的工业落地；也不是随机试验。不能用这 1 例估计通用方法减少多少隔离决策错误。

### 1.3 真实 CI 时长：有元数据，但不能归因

通过 GitHub 公开 API 下载两个真实 `Full Suite (non-blocking)` workflow 的运行与 7 个 jobs 元数据。后一次运行的 Git `head_sha` 是迁移提交的后代（源码历史已验证）；没有迁移提交**本身**的可下载运行。

| 观察 | 迁移之前、原始证据 #28697507894 | 迁移之后的后代提交 #28720367126 |
|---|---:|---:|
| 运行结论 | failure | failure |
| 工作流开始至最后更新 | 522 秒 | 529 秒 |
| 7 个 job 壁钟时间加总 | 1,609 秒 | 1,706 秒 |
| `run_attempt` | 1 | 1 |

后一次并非仅包含测试重命名的受控提交，前后也均有其他失败分片。`job_walltimes_sum_seconds` 是实际 job 观察时长之和，但不是云厂商结算费用或特定测试引起的浪费。GitHub Actions 的匿名 job logs 端点返回 HTTP 403，因此没有把无法观察到的每个测试运行结果或重跑次数填入数据。

**可判定的工业效果：**真实隔离粒度从包含许多稳定测试的旧文件缩至 1 个测试的新文件，旧文件重新有资格进入默认 CI。

**不可判定的效果：**N04 本身带来多少误隔离减少、重复运行次数减少、构建耗时和收费减少。不能根据前后 522/529 秒做因果推断。

机器证据：`results/fusion_identity_linked_quarantine.json`、`results/fusion_real_ci_runs.json`；脚本 `src/audit_fusion_quarantine_migration.py`、`src/fetch_fusion_ci_metadata.py`。

## 2. 第二个问题：4/9 标签冲突获得额外 Git 证据，但没有通过 2% 安全门槛

先前 4 个被 IDoFT 标为 `Deleted`、N04 又自动继承的测试，全来自 `zalando/riptide@cef45a1e325b`。新的独立 Git rename 检查在整个真实变更中，逐一找到同名文件的**文件重命名检测证据**（而非只依赖我们的方法体匹配）：

| 受争议测试类 | Git 的文件重命名相似度 |
|---|---:|
| AccessTokensDefaultCredentialsDirectoryTest | 98% |
| AccessTokensMissingTest | 96% |
| AccessTokensPropertiesTest | 94% |
| LogbookCompatibilityTest | 96% |

项目维护者提交 `Reorganized starter` 确实把相关测试文件从 `riptide-spring-boot-starter` 移入 `riptide-spring-boot-autoconfigure`。这加强了“原始 Deleted 标签与源码移动存在冲突”的证据；**仍不能由 Git 的 R98/R96/R94/R96 取代独立维护者对运行上下文、fixture 和测试语义的人工判定**。

| 风险口径 | 实测 | 含义 |
|---|---|---|
| 保留全部 IDoFT 原始 `Deleted` | **4/9 = 44.4%** | 必须保留的主要不安全继承数字 |
| 单独剔除 4 个原始标签有源码争议案例 | **0/5 = 0%** | 仅敏感性分析；95% 双侧精确上界 52.18% |
| 原设定的工业安全门槛 | **≤2%** | **目前没有证据可以认证达到** |

若在**相互独立**的负例中观测到 0 次错误，仍需至少约 183 次才能让双侧 95% 精确上界低于 2%；真实迁移事件成组关联，所需独立事件只会更多。不能把 4 个争议案例事后删除再宣布方法满足约束。

机器证据：`results/riptide_git_rename_audit.json`、`results/label_audit.json`、`results/statistical_audit.json`。

## 3. 第三个问题：新建跨项目独立后继目标 oracle 并执行真正的目标搜索

### 3.1 完全独立的第三方 oracle

从 `tsantalis/RefactoringMiner` 的版本化人工验证数据 `src/test/resources/oracle/data.json` 中，严格选出 Java 测试类的 `public test*()` 零参方法重命名/移动记录。原始人工验证是对**某个方法重构主张是否为 TP 或 FP**的判定；它不是“是否应将 flaky quarantine 历史移交”的标签。

完整独立筛选发现 **22 个项目、30 个提交、142 条旧→新重构候选关系（81 TP、61 FP）**。这 22 个项目未被用来训练/调整 N04 规则；其中有些项目源码没有在本次本地下载。

独立克隆并取得变更**前后源码**的 4 个项目：Apache Cassandra、Checkstyle、Google Closure Compiler、Infinispan。四个项目均不在先前的 7 个 IDoFT 正式实验项目名单中。可从源代码核验的候选配对为 **105 条（54 条经第三方确认 TP、51 条原重构主张 FP）**。

### 3.2 目标不是预先给定：Git 变更自动搜寻

为避免前版“新 FQN 由参与实验的启发式生成，因此可能标签泄漏”的问题，`src/evaluate_oracle_discovery.py` 只把旧测试 FQN、Git 提交及迁移前代码交给预测器；算法从**该提交真实发生变化的测试 Java 文件**中自行枚举变更后的方法，不接触 oracle 的目标 FQN 与 TP/FP 标记。计算结束后才用第三方标注的新 ID 评价预测结果。

| 算法 | 54 条独立确认的 TP 重构关系找到正确新 FQN | TP 恢复率 |
|---|---:|---:|
| Exact old FQN | 0 | 0% |
| 唯一同名方法 | **39** | **72.22%** |
| 唯一规范化方法体 | 17 | 31.48% |
| **Guarded lineage + group gate** | **40** | **74.07%** |

比较最强简单名称基线，Guarded 只多恢复 **1/54 = +1.85 个百分点**；按 6 个正例迁移事件的聚类 Bootstrap（17、29、43 三个种子，各 3,000 抽样），该增益的描述性 95% 区间为 **[0, +6.52pp]**，达不到原计划的 ≥15pp 优势。

54 条 TP **是重构关系边，不是 54 个独立测试**：实际有 53 个不同旧测试身份。其中 Checkstyle 一个旧测试经人工 oracle 确认为向**两个新测试类**的重构关系（1→2），guarded 正确拒绝了不唯一的目标；52 个唯一目标案例上为 **40/52 = 76.92%**，同名基线 **39/52 = 75.00%**。

各项目 guard 命中分别为 Cassandra **11/21**、Checkstyle **22/24**、Closure Compiler **7/7**、Infinispan **0/2**。按仅有的 4 个项目作为 bootstrap 聚类，增益区间仍为 **[0, +4.35pp]**；项目样本量很小。

特别强调：数据集中的 `FP` 意思是原 RefactoringMiner **方法移动重构提议**不成立，**不能**据此判断两个测试是否保持相同逻辑身份，或把匹配这些 FP 当作 quarantine 的误继承。尤其是在大规模类搬迁时，方法移动的归因与测试功能继承可能不同。新 oracle 证实了部分新目标映射的可信来源，但**未提供独立测试身份负例真值或生产安全真值**。

机器证据：`results/independent_refactoring_oracle.json`（142 条原始筛选关系）、`results/independent_source_validation.json`（105 条完整源码 pair 审计）、`results/independent_end_to_end_discovery.json`（真实后继搜寻逐条预测）、`results/independent_generalization_statistics.json`（跨事件及跨项目统计）。

## 4. 三个问题当前的诚实结论

| 原问题 | 新增可核验证据 | 仍无法成立的投稿主张 |
|---|---|---|
| 缺少真实、与迁移配对的 quarantine 决策 | **已找到 1 个真实文件级拆分决策**；另挖掘 145 个有效清单版本与 2 个真实 Actions 工作流记录 | 不能据此证明 N04 在多个工业项目减少重跑/费用；两个 workflow 都失败 |
| 4/9 错误继承，0/5 不能证明 ≤2% | 4 个冲突均得到独立 Git R94～R98 文件改名证据 | 原始风险仍 4/9；争议经人工复核且补充足量负例之前，不可声称 ≤2% |
| 跨项目缺少独立确认的目标 | **新增 4 项目、6 个 TP 迁移提交、54 条经第三方确认的目标重构边**，从 Git 自动搜索评估 | Guard 只领先同名方法 1/54，且没有跨项目 quarantine 实际收益证明 |

**最终 stop/go：**现在能研究“真实配置隔离如何随文件拆分迁移”、能在多个未知项目检验“源码后继搜索”，但工业安全约束与统计增益都尚未达到。建议以透明的负面/复现研究形式传播该工件；若投 FSE 2027 Industry Track，必须调整核心研究问题，或继续取得两个以上独立的真实工业身份迁移×隔离×运行成本纵向数据集，开展风险可控比较。不能将此 ZIP 标注为已完成全部投稿必要实验。
