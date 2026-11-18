# N21 增量构建明明成功，丢失的编译产物该怎么补？

只恢复编译状态或只恢复一部分输出时，增量构建可能判断为已完成。保存每项目的输出路径清单，可以在缓存恢复后定位缺失输出，只重编受影响的项目。成本与正确性可用真实编译和独立干净产物验证。

- Andrey Mokhov、Neil Mitchell、Simon Peyton Jones，Build Systems à la Carte，ICFP 2018。已给出构建追踪与验证阶段的理论。这里需用 TypeScript 真实缺失产物和修复成本量化部署选择。 https://simon.peytonjones.org/assets/pdfs/build-systems-original.pdf
- Kazi Amit Hasan 等，How Developers Adopt, Use, and Evolve CI/CD Caching，2026。已研究真实工作流的缓存实践；此题比较同一源码在缺失局部产物时的选择性恢复。 https://arxiv.org/abs/2604.13129
- Microsoft TypeScript #30602。已知 tsc 不一定重建手工删除的 JS；不能作为新发现。 https://github.com/microsoft/TypeScript/issues/30602
- Turborepo 配置。完整声明 outputs 并原子还原是重要生产基线。需要定位已经存在不完整缓存、无法直接完整取回的情况。 https://turborepo.dev/docs/reference/configuration

### 查询

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

