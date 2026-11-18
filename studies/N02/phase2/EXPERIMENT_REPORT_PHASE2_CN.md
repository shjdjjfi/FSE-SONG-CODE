# N02 第二阶段：六项投稿门槛的执行证据与阻塞审计

**论文方向**：Recovering Configuration Intent Across Helm Chart Upgrades  
**日期**：2026-11-15（北京时间）  
**状态**：**独立负控、原生 Helm-diff 基线、鲁棒性等 CPU 实验已执行；真实 Kubernetes Pod/升级和真实人工计时未执行，不能视为完成 FSE Industry 的全部论文实验。**

本报告严格区分：官方 Chart+实际 Helm 模板、原生插件+构造的 Helm 历史 Release Secret、真正 Kubernetes 部署、人类人工分钟。这四种证据不能混淆。

## 1. 六项要求完成度

| 要求 | 本轮完成的实际工作 | 结果 |
|---|---|---|
| 真实 Kubernetes 安装与升级 | 编写了可在自有隔离集群执行的安装→历史 Release→原生 diff→升级→探针脚本 | **未执行：缺真实集群** |
| ≥2 家族原生 Pod 行为 | Argo CD/KSM/Prometheus 的 API/指标测试脚本；KSM 有双命名空间指标 fixture | **未执行：0 个 Pod** |
| 真正 helm-diff+文档强基线 | 原版 helm-diff **27/27** 成功；精简规范化版本 **27/27** 成功，实读本机 Helm 编码 Release Secret | **插件真实执行；Secret 是构造的，人工判读未测** |
| 独立留出 | 预注册 8 新家族、最终 6 家族 72 配置状态；CID 代码/阈值预先冻结 | **完成独立负控，0 个正例使召回率未定义** |
| 真实工程师分钟 | 已实现两条件随机分配人工计时程序，完成 dry-run | **0 人、0 次判读** |
| 统计鲁棒性 | 原 5 家族 27 状态 + 新 6 家族 72 状态；新 72 项额外复用策略检查通过 | **负控覆盖扩展，正例泛化仍不足** |

## 2. 独立测试集：72 个稳定配置，无新正例

在下载新 Chart 之前冻结源文件 scripts/run_study.py SHA-256：

    64381bae392d703b7fbc20159dbaa02cf9cb6591412eb8249e6bf1f55fbf2b2e

CID 阈值维持 score≥5。按 PRE_REGISTRATION.md 中固定的规则，仅检查旧版 Chart，随机哈希排序旧默认值中的安全字符串键；改成唯一追踪值，旧版必须能够渲染并实际输出此值，取每家族前 12 个。**新版结果不能影响入选条件**。

| 预注册版本对 | 进入测试 | 新版保留的值 |
|---|---:|---:|
| Grafana 7.3.12 → 8.0.0 | 是 | 12/12 |
| ingress-nginx 4.10.0 → 4.11.0 | 是 | 12/12 |
| metrics-server 3.11.0 → 3.12.0 | 是 | 12/12 |
| Vault 0.27.0 → 0.28.0 | 是 | 12/12 |
| Traefik 24.0.0 → 25.0.0 | 是 | 12/12 |
| Grafana Loki 5.47.2 → 6.0.0 | 新版默认渲染失败，按协议跳过 | 未评价 |
| external-dns 1.14.4 → 1.15.0 | 是 | 12/12 |
| sealed-secrets 2.14.2 → 2.15.0 | 预注册仓库 HTTP 404，未换样本 | 未评价 |

**实测**：72/72 显式用户配置字符串保留；CID **0/72 误报**；missing-key 对照 0/72。72/72 采用手动“复用旧默认值”覆盖后再调用真正 Helm 渲染仍保留，0 个新模板硬失败。后一策略是 Helm 模板层的合并模拟，不是实际安装 Release 的 upgrade。

但新增样本有 **0 个字符串保留失败正例**，所以**未知故障召回率没有任何可计算的分母**。这些是 6 个家族、72 个配置状态，不能当作 72 次相互独立的真实升级。所有入选、拒绝、源 SHA 与数据完整保存。

## 3. 原生 helm-diff：54 次真正的插件调用

通过 helm_diff_historical_replay.py，从原 Chart/显式用户配置渲染旧 manifest，使用 Helm v3 标准 Release JSON→gzip→base64→Secret data 编码，创建一个**本机只读 Kubernetes API 替身**，让原版 helm-diff 从相同旧 Release 历史状态运行。

原生插件 v3.12.0 两组各 27 次全部成功，每次都请求了 Release Secret。记录了真正插件差异文本，而不是过去的 manifest-diff magnitude 代理。

| 插件输出模式 | 成功 | 差异文本中位数 |
|---|---:|---:|
| 默认输出 | 27/27 | 1,535 行 |
| normalized + context=3 | 27/27 | **628 行** |

精简版共 20,586 行，插件机器执行时间中位数 **0.521 秒/次**。各家族精简版中位数：Argo 628，Tempo 423，Prometheus 902，KSM 119，cert-manager 3,541.5 行。**这些数字不是工程师阅读分钟。**

开发集 8 例迁移问题中的 7 例已经被官方迁移说明明确指出。A04 未在特定迁移段落列出，但**实际的精简版 helm-diff 文本明确包含 “argocd-cm, ConfigMap (v1) has been added”**，见原生输出 A04_config_enabled.concise.diff 末段。能看见差异不保证工程师会识别风险，但不能再把 A04 当成工业 baseline 必然遗漏的迁移。**CID 相对 helm-diff+文档的召回优势完全尚未证明。**

注意：API Secret 是符合 Helm 读取格式的**构造历史数据**，并不是曾经实际安装在 Kubernetes 中的用户 Release；不满足“真实集群回放”要求。

## 4. 为什么真实原生部署还没有执行？

已保存 execution_prerequisites.json 的环境诊断：无 Docker/Podman/kind/k3s/minikube/kubectl、无 Docker Socket、无 cgroup v2 挂载、无 kubeconfig。这里没有启动任何 Pod、没有运行 helm install、没有执行真正的集群升级。

已写好实际集群脚本 k8s_actual_replay.py，需在**自有一次性 CPU Kubernetes**运行。它会：

1. 仅允许创建新的 n02-* 命名空间，并检查当前集群 Context；
2. 实际安装指定旧 Chart，取得 helm get values、helm get manifest；
3. 对现有 Release 执行原生 helm diff upgrade，随后原生 helm upgrade；
4. 记录 Pod phase/ready 和升级错误，同时提取真实 ConfigMap/Ingress/Deployment 参数；
5. KSM 在两个 namespace 创建可核验 fixture ConfigMap，查询 /metrics 的监控范围；
6. Prometheus 分别查询 **/api/v1/status/config 已配置的 jobs** 和 **/api/v1/targets 真实活跃 targets**，不将 11 个 jobs 误称 11 个活跃目标；
7. Argo 查询应用服务健康 API，但实际 RBAC 非管理员权限仍需授权测试用户，Ingress 可达性还需 Ingress Controller。

特别注意：A04 可能在新 Chart 想接管外部管理的 ConfigMap 时造成**Helm 资源所有权冲突硬错误**，而非 silent failure。必须以集群日志判定，不应继续将 8/8 当成 8 个运行时静默故障。

单案例命令示例（先在自有 disposable Kubernetes 安装 kubectl；在 N02_experiments 目录操作）：

    python3 phase2/k8s_actual_replay.py \
      --case K04_namespace \
      --policy reset-then-reuse \
      --namespace n02-ksm-replay1 \
      --kubeconfig /absolute/path/to/disposable-cluster-kubeconfig \
      --confirm-disposable-cluster \
      --cleanup-created-namespaces

支持 normal、reuse、reset-then-reuse、migrated 四种策略。每组需全新的 namespace。即使命名空间可删除，CRD/ClusterRole 等 cluster-scoped 资源也可能保留；请仅在可以整体销毁的一次性集群运行。

也可以在已有一次性集群的机器上一键运行完整 **6 个案例 × 4 种升级策略 = 24 次真实安装/升级**（依次执行，以免碰撞 cluster-wide 资源）：

    python3 phase2/run_cluster_matrix.py \
      --kubeconfig /absolute/path/to/disposable-cluster-kubeconfig \
      --confirm-disposable-cluster \
      --confirm-cleanup

此命令在当前工作环境**未运行**，不要将脚本存在误读为取得了 24 次结果。每次原生测试会保存旧版 Release、原生 diff、Pod readiness、API 数据和升级故障日志。程序卸载自己安装的 Helm Release，并删除自己创建的 namespace；测试结束后仍建议直接销毁整个一次性 Kubernetes 集群。

## 5. 人工成本：程序完成，实验未发生

human_review_study.py 为每个匿名参与者固定随机分配 10 个任务（4 正例、6 负控），一半对照 **真实 helm-diff 文本 + 官方文档**，一半在相同信息上额外显示 **CID 告警/风险细节**。从开始审阅到最终判断/迁移说明，用 monotonic clock 记真实秒数；用伪名 Hash 存档，不曝光 Oracle 标签。

人工程序已 dry-run，analyze_human_study.py 已检验；目前 human_review_summary.json **真实记录 0 人、0 次判读**，绝不虚构分钟/收益。

    python3 phase2/human_review_study.py --participant-id reviewer-001
    python3 phase2/analyze_human_study.py

完成这项要求需要独立工程师参与并按研究伦理知情同意。正式定论前还要固定招募人数、分配、统计和跨任务记忆效应控制。

## 6. FSE Industry 止损判定

- 原开发集：5 个家族、27 个构造配置状态（8 个 manifest-level failure、19 控制），CID 8/8、0/19；**不具有独立召回证据**。
- 新外部负控：6 个家族、72 状态，0 个失败、72 个稳定；CID 0/72 误报。合计 **11 家族、99 个配置状态**，但不同设计不能混为一个推广性准确率。
- 原提案≥2 家族的原生静默行为失败：**未检验**。
- 对完整 helm-diff+官方文档，在**相同真实人工分钟**下 ≥15pp 的优势：**未检验**。过去相对仅文档 K=4 的 +12.5pp 也未达原阈值。
- 不应撰写“所有实验完成、超过工业基线、满足投稿门槛”的结论。现阶段真实优势可能不存在，必须允许负结果。

## 7. 复现实验

离线验证（不需要网络、GPU、集群）：

    python3 scripts/verify_results.py
    python3 phase2/verify_phase2.py

重跑本轮实际完成的 CPU 实验（先下载 Helm v3.17，再在独立目录安装固定版本 diff 插件）：

    bash scripts/bootstrap_tools.sh --with-prometheus
    bash phase2/bootstrap_diff_plugin.sh

    python3 phase2/run_holdout.py
    python3 phase2/reuse_policy_controls.py
    python3 phase2/helm_diff_historical_replay.py
    python3 phase2/helm_diff_historical_replay.py --concise
    python3 phase2/analyze_human_study.py
    python3 phase2/analyze_phase2.py

归档：原 10 个官方 Chart + 新 14 个原始 Chart、54 份原生 diff 文本及 JSON、72 记录、选择排除台账、实际部署程序与人工计时程序、技术环境诊断、原始图表。下载大体积 Helm/Prometheus toolchain 的方法参见顶层 README。

权威技术说明：[Helm v3 upgrade](https://helm.sh/docs/v3/helm/helm_upgrade/)、[原生 helm-diff](https://github.com/databus23/helm-diff)、[kube-state-metrics](https://github.com/kubernetes/kube-state-metrics)。

