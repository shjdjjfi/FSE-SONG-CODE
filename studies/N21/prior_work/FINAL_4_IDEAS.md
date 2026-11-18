# FSE 2027 Industry 四个新增研究候选

**工业验证通过 0/4。** 四个研究问题已与图中 #12–#17 去重。在本轮核对的公开先例中，尚未确认已有研究完整回答下列收窄后的问题。绝对未发表状态仍未确认，已公开的机制与工具列在各题中。

| 候选 | 独立研究问题 | 当前阶段 |
|---|---|---|
| [N21 增量构建局部恢复](ideas/N21.md) | 工件恢复不全时，只重编受影响项目能否取得与干净构建一致的产物？ | 冻结对照与 Wireit 三配置探查 |
| [N23 Java 注解默认值](ideas/N23.md) | 依赖升级后，哪些旧二进制消费点会读取新默认值？ | 冻结 JVM 反射对照，需下游框架行为 |
| [N24 npm lockfile 修复代价](ideas/N24.md) | 几种修复策略覆盖哪些平台包，会改动多少无关版本？ | 冻结安装对照，逐项补全已有实现 |
| [N22 同 schema 的数据库迁移](ideas/N22.md) | 哪些迁移路径会保留相同 schema 和账本，却遗漏应用需要的数据？ | 实测负控，尚缺真实故障 |

## 实测摘要

B0001 对 N21、N23、N24 按基线、方法、消融和种子 17/29/43 做冻结对照。真实成功执行 **27/27**，按原始记录重算。N22 单独做局部试验。

- **N21。** 三臂分别为 **62 / 31 / 62** 个重编译源码单元。方法恢复后与独立干净输出的逐文件哈希一致。两次故障修复编译用时中位数为 **11.49 / 7.99 / 10.56 秒**，仅反映本机和当前样本。另测 Wireit 0.14.12：有本地缓存或 clean=true 时分别 2/2 恢复完整。禁用缓存且 clean=if-file-deleted 时 2/2 仍缺产物，命令均返回 0。[TypeScript #30602](https://github.com/microsoft/TypeScript/issues/30602) · [Wireit #905](https://github.com/google/wireit/pull/905) · [Nx #35079](https://github.com/nrwl/nx/issues/35079)
- **N23。** 三臂误分类为 **4 / 0 / 2**，每种子 12 个受控 JVM 探针。三个种子复用消费者探针。框架行为和工业发生率还没有验证。[JLS §9.6.2](https://docs.oracle.com/javase/specs/jls/se17/html/jls-9.html#jls-9.6.2) · [Maven API 演进研究](https://arxiv.org/abs/2110.07889)
- **N24。** 三臂的缺失目标包或非目标版本改动代价为 **2 / 0 / 2**。Next.js 已实现逐项修补。研究的剩余价值是量化实际依赖图上不同修复策略的等价条件、版本代价和失败边界。[npm #4828](https://github.com/npm/cli/issues/4828) · [StrykerJS #5478](https://github.com/stryker-mutator/stryker-js/issues/5478) · [Next.js 修补逻辑](https://github.com/vercel/next.js/blob/canary/packages/next/src/lib/patch-incorrect-lockfile.ts)
- **N22。** 全新与分步迁移得到相同 SQLite schema、迁移账本和默认数据。主动改写的站点保留用户值，作为应容许的差异。仍需真实业务查询失败证据。[django-test-migrations](https://github.com/wemake-services/django-test-migrations) · [Flyway 数据管理](https://documentation.red-gate.com/fd/data-138347109.html)

**优先推进 N21、N23。** N21 先找公开工作流中的实际缓存未恢复证据，给三种已有恢复配置量化适用边界，N23 先确认实际下游注解使用点及框架输出。N24 需要重冻题目，N22 先取真实案例。

[去重与失败记录](DECISIONS_AND_FAILURES.md) · [复算数据](EXPERIMENT_RESULTS.json) · [门槛核查](verification.json) · [查新和复现入口](README.md)
