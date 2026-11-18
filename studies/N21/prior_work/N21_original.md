# N21 增量构建明明成功，丢失的编译产物该怎么补？

*Recovering Incomplete TypeScript Build Outputs Without Rebuilding Intact Projects*

## 工业决策与可证伪假设

只恢复编译状态或只恢复一部分输出时，增量构建可能判断为已完成。保存每项目的输出路径清单，可以在缓存恢复后定位缺失输出，只重编受影响的项目。成本与正确性可用真实编译和独立干净产物验证。

工程对象与样本。ts-pattern 5.8.0 与 Zod 3.25.76 v3 源码，TypeScript 5.9.3。受控删除产物，固定编译选项，范围为同一工作区的独立构建单元。项目引用闭包、编译期路径可迁移性和真实 CI 部分恢复率是下一步。

## 和图中论文的区别

图中 #14 的 oracle 是消费者 feature 配置下的示例编译；这里输入源、feature 和编译器均固定，决策是恢复哪个项目的增量输出。与 #12 无版本/安全更新；与另外四题无公共对象或 oracle。

## 已知先例与研究差别

- 已给出构建追踪与验证阶段的理论。这里需用 TypeScript 真实缺失产物和修复成本量化部署选择。 [Andrey Mokhov、Neil Mitchell、Simon Peyton Jones，Build Systems à la Carte，ICFP 2018](https://simon.peytonjones.org/assets/pdfs/build-systems-original.pdf)
- 已研究真实工作流的缓存实践；此题比较同一源码在缺失局部产物时的选择性恢复。 [Kazi Amit Hasan 等，How Developers Adopt, Use, and Evolve CI/CD Caching，2026](https://arxiv.org/abs/2604.13129)
- 已知 tsc 不一定重建手工删除的 JS；不能作为新发现。 [Microsoft TypeScript #30602](https://github.com/microsoft/TypeScript/issues/30602)
- 完整声明 outputs 并原子还原是重要生产基线。需要定位已经存在不完整缓存、无法直接完整取回的情况。 [Turborepo 配置](https://turborepo.dev/docs/reference/configuration)
- 直接面向 tsc --build 缓存恢复。应按该 action 的输出策略做强基线，控制其工作流、命中状态和局部失败。 [Attest/typescript-cache-action](https://github.com/Attest/typescript-cache-action)
- 同时声明输出文件和 tsbuildinfo 的配置已有实现。必须比较应用该基线之后出现的真实局部丢失。 [Google Wireit TypeScript recipe](https://github.com/google/wireit/pull/905)
- 缓存恢复后 TypeScript 因旧 tsbuildinfo 误跳过构建已知，issue 已建议对项目 force。差异只可能来自跨项目的实证影响和独立恢复验证。 [Nx #35079](https://github.com/nrwl/nx/issues/35079)

## 实验设计

- **基线。** 已知缺失时整组 tsc -b --force。另需评估整组缓存原子还原与标准正确配置的 Turborepo。
- **方法。** 使用上一次构建的产物路径清单挑有缺失的项目，仅对这些项目执行 tsc -b --force。
- **关键消融。** 仅检查入口 index.js，独立产物校验失败后再执行整组重建。
- **独立真值。** 干净目录重新编译，逐文件核对路径与 SHA-256；显式计入未恢复时实际触发的回退。
- **停止规则。** 最小受控实验中每个种子恢复后的产物都应精确一致，平均减少至少 10 个被重编译的源码单元。若真实 CI 能使用完整产物恢复且无此局部场景、或项目引用闭包抵消收益，则停止。
- **下一项证据。** 取公开 CI 的真实 cache path/outputs 与恢复日志，增加至少两个工作区及项目引用级别的 holdout，比较原子恢复。

## 定向查新

2026-11-18 UTC，Codex Web 对论文、官方工具及 issue 的发现与核对。检索结果为相关性排序的有限窗口。

- site:github.com microsoft TypeScript tsbuildinfo missing output incrementality "rebuild" incremental build success no output
- "incremental build" "cache" "missing outputs" Maven Gradle TypeScript empirical study incremental correctness build systems
- site:github.com "tsbuildinfo" "does not" "output files" TypeScript incremental GitHub Actions cache
- site:github.com "tsbuildinfo" "cache" missing declaration output Next.js Vite pnpm TypeScript
- "typescript" "cache" outputs tsbuildinfo package incremental build missing JS turbor ep Nx paired artifacts issue
- site:github.com .tsbuildinfo "dist" "missing" "cache" monorepo turborepo nx tsc
- Turborepo caching outputs tsbuildinfo dist incremental TypeScript official docs cache outputs nx
- site:github.com/microsoft/TypeScript "noEmit" incremental tsc `.tsbuildinfo` compile emit check build cache issue TS
- "selective" "repair" "missing output" TypeScript project references tsbuildinfo restore build docs tool force
- "missing" "declared outputs" "selective" "incremental" build cache many Bazel Gradle artifact repair software engineering
- "Build Systems à la Carte" Mokhov Mitchell Peyton Jones constructive verifying traces early cutoff
- "dependency caching" "outputs" "restore-keys" rebuild outputs Azure pipelines GitHub Actions caching artifact consistency
- typescript open source "composite": true "outDir" "tsBuildInfoFile" site:github.com tsconfig.json zod ts-pattern
- site:github.com "composite" "tsBuildInfoFile" "outDir" typescript small library runtime source github tsconfig open source
- "Reproducible Builds" "Build Systems" incremental builds cache incorrect software engineering empirical hermetic
- site:github.com "tsbuildinfo" "output" "recover" incremental only missing rebuild selected project reference TypeScript
- "artifacts" "build cache" "partially" "restored" Turborepo Nx CI issues corrupted missing outputs
- "incremental" "cache" "missing outputs" rebuild affected projects manifest tsc TypeScript Turborepo research
- "restore" "artifact" "missing" "manifest" "incremental" build system detect absence project output study
- site:github.com "cache" "tsbuildinfo" ".github/workflows" tsc --build cache artifacts
- site:github.com "tsbuildinfo" ".github/workflows" "restore-keys" TypeScript cache
- site:github.com "tsbuildinfo" "actions/cache@v4" TypeScript "dist"
- site:github.com "tsbuildinfo" "output files" "cache" "tsc --build" original open source CI

[回到总报告](../FINAL_4_IDEAS.md)

## 本轮实测

TypeScript 5.9.3 在 ts-pattern 与 Zod 的受控探查中都返回 0，却保留了缺失的 JS。两份源码干净产物为 36 和 26 个文件。冻结实验用独立干净编译逐文件核对 SHA-256。尚未评估缓存原子还原、真实项目引用闭包和内容过时的工件。

每个种子对两个项目各做一次缺失注入。指标为总重编译源码单元数。

| Seed | 基线 | 方法 | 消融 |
|---|---:|---:|---:|
| 17 | 62 | 31 | 62 |
| 29 | 62 | 31 | 62 |
| 43 | 62 | 31 | 62 |

成功执行 9/9。

## 现有工具补测

后续强基线探查使用 Wireit 0.14.12 的实机配置。两个真实源码输入分别触发一次同类缺失。本地缓存可用时，2/2 恢复与干净输出相同，均未执行构建；禁用缓存且 clean=if-file-deleted 时，2/2 返回 0 但仍缺产物；禁用缓存改用 clean=true 时，2/2 恢复完整。这组结果把后续研究范围收窄到缓存无法完整恢复、主编译器仍依赖增量状态的情形。受控探查在冻结批次之外，未估计真实工作流中的发生率。 [Wireit TypeScript 配置](https://github.com/google/wireit#typescript)
