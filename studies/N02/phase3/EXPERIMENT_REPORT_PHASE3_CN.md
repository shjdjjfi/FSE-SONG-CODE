# N02 第三阶段实验报告：外部正例、原生强基线与工程师式审查

**项目：** Recovering Configuration Intent Across Helm Chart Upgrades（CID）  
**目标场次：** FSE 2027 Industry Track  
**研究日期：** 2026-11-15  
**实验等级：** 真实历史 Helm Chart + 原生 Helm 渲染 + 原生 helm-diff（本机合成 Release）；**没有真实 Kubernetes Pod/真实人工受试者**。

## 1. 最关键结论

1. **已填补此前独立测试集完全没有正例的缺口。** 在事先写明合同和修复方式的文档引导外部挑战集中，10 个候选中有 **6 个经旧版→新版→修复后三路确认的清单级失效正例**，来自 **Loki、Kong、Vault 三个 Chart 家族**；另有 3 个确认负控和 1 个不能渲染的无效候选。
2. **冻结 CID 在该外部测试上召回 3/6=50.0%。** Wilson 95% 区间约 18.8%–81.2%。Loki 的 3 个键迁移全部检出；Kong 的旧默认 PDB 约束变化和 Vault 的 2 个模板回归均漏检。按家族宏平均召回是 (100%+0%+0%)/3 = **33.3%**，注意同一家族例子相关。
3. 与“仅检查新版 values.yaml 是否缺少原键”的简单基线相比，CID 在这些正例上同为 3/6；简单基线对 3 个负控误报 1 个（Traefik），CID 为 0 个。**召回改善为 0 pp，而不是所追求的 ≥15 pp。**
4. **已实际执行原生 helm-diff v3.12.0**，对 9 个有效案例均成功生成差异文本，总计 **6110 行**。上游官方迁移/修复资料对六个正例均提供直接线索，diff 也显示六个对应的字段/资源变化。必须区分“证据可见”与“真实人工检出”；由于没有人类观察，不能得到文档+diff 的人工召回率或分钟成本。
5. **无真人，无法完成真实人工分钟试验。** AI 进行了逐案定性复核（见 `AI_EXPERT_DESK_AUDIT_CN.md`），但是模型模拟不能冒充真实受试者，故真人数为 0，人工分钟结果为 `null`，≥15 pp 的真实工业收益**没有被验证**。
6. 额外运行了一组**不读取官方升级说明**的自动化配置键扫描：9 组 Chart 升级，共 6 个移除的旧字符串值路径，成功观察 4 个旧版清单中可见的值在升级后消失；其中 2 个与先前案例重复，另 **2 个新案例**（Loki Canary 更新策略、镜像 registry）在随后使用有效值和修复值的实验中确认。它们是**探索性、扫描后挑选**的增量材料，**没有混入上述冻结挑战集的 6 个正例**。

## 2. 事前固定规则与研究设计

- `PREDECLARED_CHALLENGE.md` 是实验执行前写入的挑战清单，确定了 10 个候选（包含负控与可能失败的候选）、历史 Chart、用户值、必要的渲染上下文、提议的修复和合同字段。
- CID 核心代码 `scripts/run_study.py` 保持完全不变，SHA-256 `64381bae392d703b7fbc20159dbaa02cf9cb6591412eb8249e6bf1f55fbf2b2e`，报警阈值 **5.0**。不根据新标签修改评分或参数。
- 通过“三方证据链”确认清单正例：(i) 旧版原 values 正常渲染且合同成立；(ii) 将原值原封不动用于新版，能正常渲染但合同不再成立；(iii) 使用预先指定的键迁移或者 Chart 修复版本恢复合同。
- Chart 包来自实际历史官方 Helm Chart 发布渠道，版本和各包 SHA-256 记录于 `results/challenge_summary.json`。
- 模板调用通过 Helm v3.17.0 `helm template --is-upgrade --kube-version 1.30.0`；Loki v6 的清单使用 `loki.useTestSchema=true` 作为**一致的测试专用存储上下文**，不能代表生产 Loki 的可靠运行配置。
- 研究者先看了官方升级/变更文档再挑选候选，所以这是**文档引导的阳性富集外部挑战集**，不是随机独立未知故障真实事故的总体抽样。原始 5 家族未被重训，新 CID 仍是原代码。

## 3. 结果总表

| ID | 历史版本 | 迁移合同 | 旧版 | 原值升新版 | 修复后 | 判定 | CID |
|---|---|---|:---:|:---:|:---:|---|---|
| L01 | Loki 5.47.2→6.0.0 | 禁用 Canary | 模板失败 | 未满足 | 模板失败 | **无效候选** | 不计 |
| L02 | Loki 5.47.2→6.0.0 | 自定义 Canary 标签 | ✓ | ✗ | ✓ | 正例 | ✓ |
| L03 | Loki 5.47.2→6.0.0 | 自定义 Canary 镜像路径 | ✓ | ✗ | ✓ | 正例 | ✓ |
| L04 | Loki 5.47.2→6.0.0 | 外部 Loki 配置引用 | ✓ | ✗ | ✓ | 正例 | ✓ |
| G01 | Kong 2.1.0→2.2.0 | PDB `maxUnavailable: 50%` | ✓ | ✗ | ✓ | 正例 | **✗** |
| G02 | Kong 2.1.0→2.2.0 | 关闭 PDB | ✓ | ✓ | ✓ | 负控 | 无报警 |
| V01 | Vault 0.25.0→0.26.0 | HA StatefulSet 2 副本 | ✓ | ✗(变 3) | ✓(0.26.1) | 正例 | **✗** |
| V02 | Vault 0.25.0→0.26.0 | HA StatefulSet 3 副本 | ✓ | ✓ | ✓ | 负控 | 无报警 |
| V03 | Vault 0.28.1→0.29.0 | HCL 的 Helm 模板展开 | ✓ | ✗ | ✓(0.29.1) | 正例 | **✗** |
| T01 | Traefik 24.0.0→25.0.0 | 未生效的旧 Gateway 字段 | ✓ | ✓ | ✓ | 负控 | 无报警 |

`✓`、`✗` 只表示事先定义的**清单合同判据**，不是 Pod 健康或生产故障。

**分层问题：** L02–L04 是旧路径到新路径的迁移；G01 是删除旧默认值导致的部署合同变化；V01/V03 是上游 Chart 模板回归并由其补丁版本修复。不要将这些异质错误表述成一种“统一的键重命名”故障。

## 4. 基线和统计

### 4.1 相同清单挑战中的自动方法

| 方法 | 6 个正例检出 | 3 个负控误报 | 正例召回 | 相对简单基线 |
|---|---:|---:|---:|---:|
| 冻结 CID | **3** | **0** | **50.0%** | **+0.0 pp** |
| 新版 `values.yaml` 缺键扫描 | 3 | 1 | 50.0% | 基准 |

零误报要结合样本数解释：先前 72 个外部稳定配置负控 + 本次 3 个外部配置负控，共 **75 个负控，CID 0 次报警**；对真实负控总体的特殊性没有把握，Wilson 95% 特异度区间 **[95.13%,100%]**，且样本不是概率抽样。此前 72 个与此处 3 个并非独立的真实生产部署。

### 4.2 真正的插件和官方文档基线

- `native_diff_external.py` 基于本机合成 Helm v3 Secret 模拟**同一个已经安装的旧 Release**。原生 `helm diff upgrade n02 <newchart> --reset-then-reuse-values --normalize-manifests --context 3` 从只读 loopback Kubernetes API 拉取 Release Secret，9/9 有效案例返回 0 并写出真实插件输出。**没有真实 Kubernetes API server、Pod 或成功安装的 Release。**
- 9 个实际 diff 文件总共 6110 行；Loki 3 个正例分别有 1750、1749、1846 行。Kong/Vault 漏检案例仅 141、157、105 行，而且关键损失字段清晰出现在差异中。
- 上游文档对 6 个正例全部直接记载或对应修复：Grafana 的 Loki 6 升级说明明确说明键迁移；Kong 2.2.0 升级说明明确提到 PDB 50% 默认移除；Vault 0.26.1/0.29.1 变更日志直接描述回归和修复。
- 故“docs+diff 的**证据覆盖**”为 **6/6**。与之相比 CID 3/6，是在不同度量上的直观警示，不能把文档证据覆盖 100% 当作**真人检出率 100%** 再统计做差。如果仅比较自动 CID 与文档静态证据**可见性**，差为 **−50 pp**，这不是经过人类实验估计的增益。
- 采用 Chart 家族为聚类单位的 10,000 次重抽样，CID 与文档**可见性**的差值粗略区间为 **[−100 pp, 0 pp]**；只有 3 个正例家族，此区间非常不稳健。

### 4.3 审阅时间能测什么、不能测什么

原生插件总耗时可以从 `results/native_diff_external.json` 计算；这些是软件运行秒数，**绝非工程师阅读秒数**。`phase2/human_review_study.py` 已有真实受试者计时、知情同意和逐条记录；本研究没有拿到受试者。AI 已逐案写定性工程师式审查（专文件），但因为既非人类又非盲审，**不能补上真人分钟数据**。也不能通过人工等待、改变输出速度或虚构参与者来替代。

至少 15 个百分点的工业获益（相对于 `helm-diff + 官方升级文档`）当前**不成立为可宣称的实验结论**；现有证据甚至提示应该缩小主张、改善方法设计并使用新的真正锁定的未来数据集重新验证。

## 5. 非文档引导的自动扫描与增量发现

`schema_blind_probe.py` 对 9 个 Chart 升级对的旧版字符串型配置叶节点和新版 `values.yaml` 做结构比较，不读取 CHANGELOG。自动找出 6 个“旧有新无”的字符串路径：Loki 5 个、Kong 1 个。只有 4 个 Loki 路径在旧 Chart 真正渲染出诊断性值且在新 Chart 丢失。其余未通过旧版渲染暴露判定，不算故障。完整结果包括失败候选保存在 `results/blind_schema_selection_all_attempts.jsonl`。

随后对其中两个非重复路径进行了**扫描后**真实可用值和迁移修复验证：

| 探索性 ID | 原配置与迁移 | 合同变化 | 三路检查 | CID |
|---|---|---|---|---|
| E01 | `monitoring.lokiCanary.updateStrategy.type` → `lokiCanary.updateStrategy.type` | `OnDelete` → `RollingUpdate` → `OnDelete` | 全通过 | 检出 |
| E02 | `monitoring.lokiCanary.image.registry` → `lokiCanary.image.registry` | `quay.io` → `docker.io` → `quay.io` | 全通过 | 检出 |

E02 的替代仓库并未证明有镜像可拉取；其合同仅是镜像名称中的 registry 被保留。E01 为合法 DaemonSet 更新类型。这两例是**探索性发现**，不得统计进原先确定的 6/10 主研究；它们也和 L02–L04 高度相关，不能当成两个新的独立家族。

## 6. 当前能否直接写成 FSE Industry Track 的成功论文？

**不能宣称全部实验完成或达到 ≥15 pp。** 现已完成的核心科学改进是：正例存在性、跨 Chart 家族外部挑战、修复反事实、真实插件强基线的可见性、系统性负控与保存完整的失败证据。

仍须补齐的、不能由本环境中的 AI 主观冒充的证据：

1. **真实工程师参与**：至少数名独立从业者，盲化分配同等历史 release/官方文档/原生 diff，比较 `docs+diff` 与 `docs+diff+CID` 的准确率和人工分钟，用真人亲自操作计时程序。
2. **真实 Kubernetes 工作负载**：目前只有 Helm 模板和合成 Secret；需真正安装、升级并观测 Pod 状态、PDB API 接纳、Canary CLI 行为和 Vault/配置加载，特别是 G01 可能的安装校验失败。
3. **泛化强度**：未来先冻结扩展方法与阈值，盲化选择更多不同升级事件，覆盖真正部署成功的正例。现有阳性富集候选、按文档选例和同升级事件多合同不能支持总体敏感度推广。
4. **创新与优势**：如目标确为“比官方 docs + helm-diff 少错/省时间 ≥15 pp”，应在独立工程师数据上先证明；本次结果不能支持。可以改为研究“显式配置合同的自动化回归检测，以及与人工审阅的互补”，但需要新的设计与评估。

## 7. 复现

从 `N02_experiments` 根目录执行，Python ≥3.11，安装 `requirements.txt`，必要工具请见 `toolchain/` 和 `phase2/bootstrap_diff_plugin.sh`。原始源码和历史归档均已保留。

```bash
python phase3/run_external_challenge.py
python phase3/native_diff_external.py
python phase3/analyze_external.py
python phase3/schema_blind_probe.py
python phase3/validate_blind_discoveries.py
```

`run_external_challenge.py` 会写入每个候选实际合同值和渲染失败信息；原生 diff 需要其已记录的本地插件（**不连接集群**）；分析代码会输出统计 JSON。`results/challenge_cases.jsonl`、`results/challenge_summary.json`、`results/native_diff_external.json`、`results/helm_diff_transcripts/*.diff`、`results/challenge_statistical_audit.json`、`results/blind_schema_selection_all_attempts.jsonl`、`results/exploratory_validated_discoveries.json` 是本文对应的审计材料。

外部验证均未用 GPU。真实容器/Kubernetes 集群、真人受试者和独立产业用户数据均未在该阶段发生。
