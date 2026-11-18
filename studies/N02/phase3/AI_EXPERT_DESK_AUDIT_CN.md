# N02 第三阶段：工程师式逐案桌面审查（AI 模拟，非人类实验）

审查对象：真实原生 `helm-diff` 插件通过本机只读 Kubernetes API 模拟器读取**合成 Helm Release Secret** 得到的差异；上游官方升级说明；旧版用户 values。所有差异均保存在 `results/helm_diff_transcripts/`。

**审查主体是 AI 助手，不是人类受试者。** 模型已接触过配置合同、候选标签和预声明信息，属于**非盲、非独立的定性核查**，不能用作人类检测召回率、人工分钟或随机对照试验。即便刻意让模型较慢输出，也不会产生真实人类时间数据。没有为人类参与者伪造记录。

## 审查所依据的工作流

1. 打开旧版 values 和两版本信息，确认用户实际想固定的行为。
2. 浏览原生 `helm-diff` 差异的资源/字段语义；忽略无风险的版本标签、镜像版本等正常变动。
3. 与官方迁移说明或已知 Chart 修复版本核对，给出风险、修复动作和验证点。
4. 单独检查冻结 CID 信号是否指向了这项风险；CID 未报警时不改写结果。
5. 通过旧版→新版→修复后三路真实 `helm template` 验证清单合同，保留不满足条件的无效案例。

## 9 个有效案例的专家式结论

| ID | 差异行数 | 专家式结论 | 关键差异证据（.diff） | 可操作的修复 | 冻结 CID |
|---|---:|---|---|---|---|
| L02 | 1750 | **有风险** | 原 `-labelname=n02_canary_contract`，新 `-labelname=pod` | `monitoring.lokiCanary.labelname` → `lokiCanary.labelname` | 检出 |
| L03 | 1749 | **有风险** | 自定义 Canary 镜像路径被默认 `docker.io/grafana/loki-canary` 取代 | 将 `image.repository` 配置迁到 `lokiCanary.image.repository` | 检出 |
| L04 | 1846 | **有风险** | 原引用 `n02-config-external`，新版引用 `loki` | `loki.externalConfigSecretName` → `loki.configObjectName` | 检出 |
| G01 | 141 | **有风险** | PodDisruptionBudget 原 `maxUnavailable: 50%` 被删除 | 明确设 `podDisruptionBudget.maxUnavailable: "50%"` | **漏检** |
| G02 | 120 | 无本合同风险 | 用户关闭 PDB，两版均未创建该资源 | 不需要本项修复 | 未报警 |
| V01 | 157 | **有风险** | Vault StatefulSet 的 `replicas: 2` 改为 `replicas: 3` | 升级至修复后的 Chart 0.26.1，重新验证 replicas | **漏检** |
| V02 | 148 | 无本合同风险 | 用户本来要求 3 副本，两版均渲染 3 | 不需要本项修复 | 未报警 |
| V03 | 105 | **有风险** | 已解析的 `/vault/data/n02` 变成字面量 `{{ .Release.Name }}` | 使用 Chart 0.29.1 修复模板插值 | **漏检** |
| T01 | 94 | 无本合同风险 | 被移除的旧 Gateway 值在旧版也没有产生 Gateway 资源 | 无可观察部署合同丢失 | 未报警 |

### 不计分的候选

- **L01**：旧版禁用 Canary 就被 Chart 的验证模板阻止，迁移后仍无法通过测试条件下的模板检查，因而**不能称为静默配置失效**；它在候选清单和完整失败日志中保留，不从实验轨迹中抹去。

### 边界与审查风险

- 在 L03 中使用的自定义镜像地址是诊断性哨兵，不保证镜像可以被实际拉取。因此它验证的是“用户指定的仓库被 Chart 使用”，不是“旧 Pod 已实际健康启动”。
- 在 G01 中，PDB 的缺失约束可能导致真实 Kubernetes API 对对象的校验失败；尚未进行 API server 验证，**不应把该案例称为已证实的生产静默故障**。
- 在 V01/V03 中，修复需要更换 Chart 补丁版本，并非仅靠修正 values 就能完成。这类**模板回归**应在正式论文中与“配置键重命名”分层报告。
- 三个 Loki 正例共享同一个升级事件，不能按三个独立部署或三个独立工程师统计。
- 官方升级说明对 6 个正例都有直接线索，原生 diff 对 6 个正例都有可见字段证据。因此**从可用证据不能论证 CID 比 `helm-diff + docs` 更强**；实际人类会不会发现、花费多少分钟仍需要真实受试者。

## 参考材料（原厂）

- Grafana Loki v6 升级：<https://grafana.com/docs/loki/latest/setup/upgrade/upgrade-to-6x/>
- Kong Helm Chart 升级：<https://github.com/Kong/charts/blob/main/charts/kong/UPGRADE.md>
- HashiCorp Vault Chart CHANGELOG：<https://github.com/hashicorp/vault-helm/blob/main/CHANGELOG.md>

## 时间与主体真实性声明

`results/native_diff_external.json` 的 `plugin_wall_seconds` 记录的是**机器执行 Helm 插件的秒数**，不包含人工判断。此处没有声称任何虚构的“工程师用时 X 分钟”；在独立招募真实工程师之前，人类分钟指标记为 `null`，人类受试者数为 0。模型可以帮助生成指导语、审查清单和模拟推理，却不能转换为真实参与者。
