# N22 实验结论与投稿可行性审计

研究日期：2026-11-18（UTC）。性质：**事后探索性实证与复现包，不是预注册验证；原假设门槛未通过。**

## 一、研究对象与独立故障来源

N22 的出发点来自用户提供的四个 idea 中的第二题：**Checking Data Contracts Across Converging Database Migration Paths**。其事先写出的停止规则是：至少两个独立真实迁移故障、同等回放预算下相对*完整*基线召回增加 ≥15 个百分点，误报率 ≤5%。

| 编号 | 真实公开故障来源 | 实际测试对象 | 迁移后用户可见失效 | 维护者独立证据 |
|---|---|---|---|---|
| D1 | [Django ticket #36843](https://code.djangoproject.com/ticket/36843) | PyPI Django **6.0.0** 的真实迁移与权限管理 signal | 原本拥有 `n22_perm_app.view_songprofile` 的用户执行分步迁移后无法通过 `User.has_perm` 校验，错误得到 `view_son` | 维护者修复，Django **6.0.1** 对照消失；历史修复提交 `030c63d329c4814da221528e823a4aaaaa40e4f1` |
| D2 | [OpenCode issue #52226](https://github.com/anomalyco/opencode/issues/52226) | OpenCode **v2.0.19**，`1fd016ef32286de9489b7b24f1029f52c49a27b3`；原版 `V1Migration.run` | 有效旧格式 assistant message 缺少 `agent`，2 条源 message 只写入 1 条到 V2，但标记 `completed` | 独立用户报告实际历史迁移跳过 **6,238** 条旧 message；该数量是工单证据，**不是本实验测量值** |

两类执行路径均采用真实上游代码和 SQLite 实例，不修改被测迁移逻辑。Django fixture 只新增具有共享字串 `Son`/`SongProfile` 的业务模型及两个普通迁移。OpenCode 使用上游原样的 48 个数据库迁移 + `V1Migration.run()`，只合成最小历史 V1 数据。

### Django D1 的可核对证据

在 Django 6.0.0，`fresh`（最终迁移后设置授权）与 `staged`（停在 0001，授权，再升至 0002）均执行成功，且最终结构哈希均为：

`5dac277d566103ee43e44d40dfbeb2401dd316ee7df39f543f57f84c0536c115`

迁移账本哈希均为：

`c6e4620b6459bb38f3984bac4f277a56a4964021b4a284cbb0e133c3e65e1bc2`

但 `fresh` 的授权连接行为 `(n22_perm_app, songprofile, view_songprofile)`，`User.has_perm('n22_perm_app.view_songprofile') == True`；`staged` 的授权变成 `(n22_perm_app, songprofile, view_son)`，对应权限校验为 `False`。**这不只是表中的行数差：用户实际权限发生了变化。** 同样的 staged fixture 在 Django 6.0.1 中校验通过。

这里“路径会聚”限定为最终 schema 和 migration ledger 相同，**不**声称业务数据或某些引用值应逐字节相同。升级前存在合法历史授权，正是条件差异。

### OpenCode D2 的可核对证据

OpenCode 五个最小场景都创建新的 in-memory SQLite，执行原版 48 层迁移与 V1→V2 转换。两条 V1 源 message 中，一条旧 assistant row（`mode: build` 但不含后来必需的 `agent`）在真实上游 decoder 中被跳过，只有 1 条进入 `session_message`；迁移返回 `completed`，`kv['migration.v1-v2'] == '{"phase":"completed"}'`。给该 row 添加当前格式 `agent: build` 后则转换 2/2。五个场景的 schema 与 version-ledger 哈希一致。

另一场景在已完成 checkpoint 之后由遗留客户端写入 V1 新 session，导致 2 个旧 session 中仅 1 个投影到 V2；它与公开 [#50130](https://github.com/anomalyco/opencode/issues/50130) 相关，但混用新旧写入器是否属于受支持的业务操作尚无权威政策，故**仅列条件示例，完全排除主指标分母**。

## 二、覆盖与阴性对照

- **主评估：15 个独特输入**，即 D1、D2 两个独立正例，加 13 个阴性场景。阴性场景跨 Django 6.0.0/6.0.1、Django 5.1.8 sites/redirects/flatpages、OpenCode v2.0.19 三种用例家族（实际上仍只有 Django/OpenCode 两个上游项目）。
- **压力测试：30 个相关合法用户值**（30 种不同的站点域名、带引号及中英文 Unicode 站点名），均要求保留为合法值，不能将其与 clean install 的默认值比较后称为故障。
- **条件案例：1 个**，OpenCode 迁移 checkpoint 之后的新旧写入并存，不计入主指标。
- **运行数量：46 个独特 case × 3 次隔离重复 = 138 条观测**。其中 Django 41 × 3 = 123 个新进程和 SQLite 文件；OpenCode 5 × 3 产生 15 个隔离 in-memory DB/观测，分别由 3 个 Bun 测试进程执行。总 **126 个测试进程**。
- **基线额外 9 次**：Django helper 6 次（6.0.0/6.0.1 各 3 次）；OpenCode 项目已有 `v1-migration.test.ts` 整组 **26/26 通过**，重复 3 次。
- 任何重复都不是独立新故障；30 种站点修改也不能独立估计跨项目误报率。

## 三、主评估（每个 case 计一次，不把重复当独立样本）

| 检测方式 | TP | FN | FP | TN | 本样本召回 | 本样本误报率 |
|---|---:|---:|---:|---:|---:|---:|
| 数据合同检测（SQL 行关系 + 必需集合） | 2 | 0 | 0 | 13 | 100% | 0% |
| **完整人工/测试基线：相同回放 + 相同业务断言** | **2** | **0** | **0** | **13** | **100%** | **0%** |
| 只比较最终 schema | 0 | 2 | 0 | 13 | 0% | 0% |
| 只比较最终迁移账本 | 0 | 2 | 0 | 13 | 0% | 0% |
| 只看迁移完成状态 | 0 | 2 | 0 | 13 | 0% | 0% |
| 原始无语义行比较 | 2 | 0 | 5 | 8 | 100% | 38.46% |
| 只看行数 | 2 | 0 | 4 | 9 | 100% | 30.77% |

计算源：`runs/full/observations.jsonl` 和 `benchmarks/labels.json`；独立的 `code/analyze.py` 聚合、验证三次一致性，输出 `reports/case_table.csv`、`reports/metrics.json`。不把 `business_oracle.contract_violation` 用作合同检测器的预测特征，合同使用 SQL 行与预先写出的特定必需键；完整人工基线另从 Django 应用 API 与 OpenCode 迁移后 source/target ID 断言直接得到。

**对照解释：** schema-only/ledger-only/status-only 是有价值的消融，但不是 FSE 应对比的最强工业基线。`django-test-migrations` 1.7.0 的默认引擎会静默迁移 signal，因此在受测例中没有触发该 Django signal 缺陷；如果工业团队使用真正的 `manage.py migrate` 和同样的业务断言，**他们也能查出故障**。OpenCode 原自带 26 条测试均通过，但没有覆盖旧 `agent` 缺失格式。以上不能被写成“新方法优于所有现有测试”。

## 四、统计不确定性与门槛判定

- 两个正例 2/2 命中；即使把它们当作独立伯努利试验，召回率精确单侧 95% 下限仅约 **22.36%**。
- 十三个阴性 0/13 误报；同样乐观地按独立个案假定，误报率精确单侧 95% 上限约 **20.58%**。**不能证明未来误报率 ≤5%。**
- 两个真实阳性来自两个公开报告的历史缺陷，事后选择，不能将这两例宣传为无偏随机抽样。13 个阴性也按项目聚类。上述二项区间本身因此**过于乐观**。
- 完整基线的 2/2 命中率与合同检测相同，提升 **0 个百分点**；未达到原停止规则要求的 **≥15 个百分点**。强基线与方法没有不一致的正例，无法主张统计显著的改进。
- 本机命令运行时间记录在 `case_table.csv`，仅描述实验环境执行开销；不代表工业数据库负载、规模、机会成本或风险。

**决策：原 N22 的工业 track 贡献门槛未通过。** 现成实验具有独立真实故障复现价值，但不足以支撑“新检测方法工业效果显著改善”的 claim。不应为投稿隐去失败的对照结果。

## 五、需要正式投稿前补齐（当前没有证据）

1. **工业实践可追溯性。** 至少一个真实组织或公开可复核的大型维护流程（使用频率、迁移体量、升级窗口、审查成本），否则工业实用价值只能推测。
2. **前瞻、预注册评估。** 在冻结合同定义、选择算法和阈值后，再用未见过的新历史故障及新项目执行；不要在已知 bug 上做调参再复算命中率。
3. **完整公平基线。** 现有项目 DB migrator、`django-test-migrations` 配独立业务断言、Artemis 风格的 fresh-vs-upgrade 测试，以及等回放预算策略；统一比较人为合同编写/维护成本、独立覆盖与成本。
4. **误报风险与召回不确定度。** 需要远多于 13 个高独立性阴性项目才能对 ≤5% 提供有说服力的边界；路径数不等于项目数。
5. **运行环境迁移广度。** 目前两项目、Django 主要 SQLite、OpenCode in-memory SQLite，无 PostgreSQL/MySQL/分布式上线、回滚、真实并发写入验证。
6. **操作价值。** 无真实 CI 历史、工程师处置时间、迁移事故成本或项目维护者反馈。不能据 11 秒左右的实验声称投入产出比。
7. **已知先例差异。** [Artemis migration consolidation 指南](https://docs.artemis.tum.de/developer/guidelines/database-migration-consolidation/) 明确具备 fresh-vs-upgrade 检查；[django-test-migrations](https://github.com/wemake-services/django-test-migrations) 已能插入业务断言。若没有可验证的新自动合同抽取、路径覆盖或维护成本收益，贡献与既有实践重复的风险很高。

## 六、复现与不可变性审计

复现来源锁定 `Django==6.0`, `6.0.1`, `5.1.8`, `django-test-migrations==1.7.0`, Bun 1.3.1 和 OpenCode SHA `1fd016ef32286de9489b7b24f1029f52c49a27b3`。代码在每个 Django 场景中创建新的 SQLite 文件，拒绝覆盖已存在数据库；分析器在每个 `case_id` 的三次独立重复之间检查预测一致性。

`observations.jsonl` 的 SHA256：`36ae5b4ce853c68634a8acaf6ea129f1d53028b62b1ef3b945b805813f4b3d15`。原 OpenCode 检测 harness SHA256：`c898aecfef9ae7060151b90d2c3f7349f504b6460c47736a98f94dd12e345026`。

原始用户附件 `FSE2027_4_ideas(1).zip` SHA256 为 `5175044ab3af196fdcbad0bd361fbbf89b48c922844211e4335628fc880e981d`；另附总览 `FINAL_4_IDEAS(1).md` 为 `515a38803e0e9dda383dd1288831c61a7cb3d5cf55f600958a1275f251a99986`。两份原始文件未修改。

本包不含原始第三方源码 checkout 或装好依赖的环境，读者需通过明确 commit/version 取回，不含真实用户数据。
