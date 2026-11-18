# N05：Rust 文档示例消费者配置回放——实验交付说明

> **更新：第二独立项目实验与公开 CI 实证审计。** 原文下方的 24+8 项目结果
> 保留为旧实验记录；新增 30 个软件包冻结样本、目录线索方法、GitHub Actions
> 真实成功运行的工作流证据、历史维护者修复的回溯覆盖率、准确版本的线上
> rustdoc feature 提示和 Cargo feature 闭包开销。最新科研结论以
> [`paper/INDUSTRIAL_VALIDATION.md`](paper/INDUSTRIAL_VALIDATION.md) 和
> [`prospective/results/independent_validation.json`](prospective/results/independent_validation.json)
> 为准。这些真实外部 CI 记录**不是**我们部署方法的 CI 效果。辅助 GitHub Actions
> 模板在 `industrial/`，属于尚未上游部署的可运行试点。

**请先读最新中文结案报告：[`paper/INDUSTRIAL_VALIDATION_CN.md`](paper/INDUSTRIAL_VALIDATION_CN.md)。**
旧表格仅用于记录初始的 24+8 个发布包。完整新结果包括第二组 30 个独立仓库、
24 个特性差异正例（v1 100% 对随机 75%，但精确仓库聚类 95% CI 包含零）、
排除 6 个内部测试夹具后的 18 个可疑消费示例（v1 与 rustc 强基线成功率均为 100%），
以及五组**观测性的**上游 CI 记录。真实工业 ROI 尚未被证实。

实验日期：2026 年 11 月 15 日（北京时间）。

本包对应附件中编号 **N05** 的第五个研究 Idea：
*Replaying Published Rust Examples Under Consumer Feature Profiles*。
没有使用 GPU、云模型 API 或私人数据，使用 crates.io 发布的原始版本软件包、Rust 1.91.0 和 CPU 编译。

## 一、完成的真实实验

| 指标 | 主实验（规则设计所用项目） | 外部项目验证集 |
|---|---:|---:|
| crate 发布版本 | 24 | 8 |
| 抽取的候选 Rustdoc 片段 | 2,212 | 909 |
| 冻结后实际编译的不同片段 | 141 | 60 |
| 默认配置失败 / docs feature 配置成功 | 25 | 7 |
| 同时通过两种配置的严格负控 | 61 | 25 |
| 无法独立重现的片段 | 30 | 20 |
| 依赖 docs 专用 cfg 开关 | 7 | 0 |
| 引导方法（≤8 次额外编译）成功率 | 100%（25/25） | 85.7%（6/7） |
| 三个随机顺序平均成功率 | 64.0% | 85.7% |
| 只读文本提示方法平均成功率 | 52.0% | 57.1% |
| 引导方法平均额外编译次数 | 1.68 | 2.29 |
| 随机顺序平均额外编译次数 | 5.27 | 3.90 |
| 已编译核验的子集最小补集 | 25/25 | 6/6 个已找到的补集 |
| 删除隐藏 Rustdoc 辅助行后失败 | 6/23 | 3/11 |

主实验引导方法的成功率较随机顺序高 36 个百分点，**以 crate 为独立聚类单位**的 10,000 次 bootstrap 差值 95% CI 为 +20.0 至 +50.7 个百分点。两者额外 Cargo 编译次数之差（随机减引导）的聚类区间为 +2.29 至 +4.67 次。

外部验证集上引导方法的成功率与随机顺序**相同**（均 85.7%），尽管观察到平均少使用约 1.62 次编译，但其聚类区间为 -0.67 至 +2.25 次，不能认定独立样本上提高有统计把握。

主实验另完成不使用任何 crate 特化规则的探索性消融：25 个样本中 23 个成功（92%），说明主实验的大部分表现并不依赖那些特化规则，也意味着仅凭这一结果不足以证明复杂新算法的必要性。

注意：79 个默认配置可以编译的主实验示例中，只有 61 个同样通过了文档 feature 配置。前者不能全部计入严格的“正/负”比较分母；外部验证集同理，33 个默认成功中有 25 个是严格负控。

## 二、研究结论的边界

**25+7 个是 feature 配置差异，不等于 32 个文档缺陷。**

例如官方发布页面 [uuid 1.17.0 Uuid](https://docs.rs/uuid/1.17.0/uuid/struct.Uuid.html) 在 `new_v1`、`new_v5` 等方法旁已明确写明需要相应 feature。即使默认消费者确实编译失败，也不能据此说维护者漏写说明。

当前的数据支撑：

1. 固定发布包确实存在消费者默认 feature 与 docs.rs feature 配置之间的编译不一致。
2. 在本次选中的相应正例上，通过不超过 8 次实际编译可以找出很多较小的补集。
3. 每个主实验成功补集都经过独立逐项删除检查，满足子集最小性；18 个只需一个新 feature 的情况，在“新增 flag 数量”意义下显然达到全局最少。但含多个 feature 的补集不具有已证明的全局最优性。

尚不支撑：

- 这些页面没有标注 feature 的准确率、误报率≤5% 等结论（缺少对最终渲染页面的逐例独立判读）。
- 在未见过的项目上，成功率稳定优于现有方法≥15 个百分点（外部验证集没有出现该优势）。
- 实际企业 CI、生产部署、维护者修复或开发者工时节省等效果（实验是独立消费者编译回放）。

**结论：可复现的实验研究包已完成，但如果把“达到 FSE 2027 Industry 论文可投稿证据门槛”理解为完整且有说服力的工业收益和新颖性证明，目前仍不能诚实认定全部达标。**

投稿前应至少补齐：逐页 feature 披露人工复核、在未调参的更多独立项目上检验优势、与现有 Rustdoc/现成 feature 检测工具的严格对照，并尽可能加入真实仓库 release CI 的实用性试点。若这些结果否定方法收益，应按原选题的止损条件放弃或缩小论文主张。

## 三、成果目录

- `data/crates/*.crate`、`holdout/data/crates/*.crate`：官方源码原始发布包；完整 SHA-256 在各自的 `crates_manifest.json`。
- `data/corpus.jsonl`、`holdout/data/corpus.jsonl`：原始代码片段、位置和源上下文。
- `data/frozen_sample.json`、`holdout/data/frozen_sample.json`：三随机种子的抽样清单。
- `results/screen.jsonl`、`holdout/results/screen.jsonl`：全部编译标签。
- `results/search.jsonl`、`holdout/results/search.jsonl`：等额预算方法和基线的逐步查找过程。
- `results/minimized.jsonl`、`holdout/results/minimized.jsonl`：最小化实际试编结果和补集。
- `results/checks/`、`results/check_logs/`：JSON 运行摘要、错误、哈希、实际 Cargo 日志；外部验证集的结果置于 `holdout/results/`。
- `results/witness_audit.json`、`holdout/results/witness_audit.json`：逐例可跳转的源码审计卡。页面缺陷的人工标签保持 `NOT_REVIEWED`，没有伪造人工标注。
- `results/summary.json`、`holdout/results/summary.json`、`results/per_project.csv`：自动汇总和各项目统计。
- `figures/`：论文用 PNG 图。
- `paper/EXPERIMENTAL_DESIGN.md`：实验假设、对照、判定标准、统计计划与威胁。
- `paper/RESULTS.md`、`holdout/paper/RESULTS.md`：从实际结果自动生成的英文结果章节草案。
- `scripts/` 与 `tests/`：复现、审计与自动测试。安装工具与运行顺序见 [README.md](README.md)。

实验代码、样本选择和原始 Cargo 编译输出均保留，所有正例都能追溯到官方版本、具体代码片段和实际编译记录。未把未执行、超时或因外部依赖不完整导致的失败填成“成功”。
