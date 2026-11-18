# N05 docs.rs 能编译的示例，默认依赖用户能直接运行吗？

*Replaying Published Rust Examples Under Consumer Feature Profiles*

## 工业场景

crate 维护者决定发布前给哪些示例加 feature 说明或 CI 矩阵。已核对 docs.rs 的 metadata、Tokio 的本地文档构建 issue、SQLx 0.8.6 公开文档；从固定版本的页面抽取真实未标 ignore 的完整片段。

## 可证伪假设

Rust crate 文档构建的 feature set 可能大于真实消费者所启用的 set。研究缺口是自动选出偏差见证和最小可编译 feature 补集，检验消费者不读额外迁移说明时，页面上的最小依赖声明能否支持同一段示例。

## 最近先例

- **’R: Towards Detecting and Understanding Code-Document Violations in Rust**，Wanrong Ouyang、Baojian Hua，ISSRE Workshops, 2021。已有 Rust 源码与 doctest 的程序分析。不确定消费者 feature 最小补集是否曾被直接评估，需全文再核对。 [原始来源](https://csslab-ustc.github.io/publications/2021/rdoc.pdf)
- **RFC 3485: Feature Documentation**，Rust 项目，RFC。feature 文档标注已有明确提案，不能以发现缺标注作为论文创新。 [原始来源](https://rust-lang.github.io/rfcs/3485-feature-documentation.html)
- **docs.rs Metadata**，docs.rs 项目，官方文档。支持公开配置 all-features、features 和 no-default-features。相关性可直接用实际编译而非推断检验。 [原始来源](https://docs.rs/about/metadata)

## 正式实验设计草案

对照为从文档声明运行 cargo doctest 并采用 feature 标注；方法按 published manifest 建消费者 crate，在候选 feature 图里优先运行最小见证；消融去掉消费者配置差异、保留等额编译预算。oracle 由独立 cargo check/test 和源码可运行合同给出，留出 crate、保留已经明确标注的负控。

对照、方法、消融共享冻结输入和等预算。种子 17、29、43 按项目或时间分层形成不同配对样本，按项目或独立事件聚类估计 95% 区间。独立项目过少时报告逐项目效应和范围。获得独立标签后再冻结样本及指标。

**工程效果及止损条件。** 以同额编译预算多检出 ≥15 个百分点的可操作示例失败，误报 ≤5%；若全部由现有 doc(cfg) 或普通默认 doctest 解释，停止。

## 已完成的核验

**SCREENED。** 解析了 Tokio 1.45.1 和 SQLx 0.8.6 的固定 Cargo.toml。Tokio 无默认 feature 且 docs.rs 配置 all-features；SQLx 默认四项为 any/macros/migrate/json，docs.rs 另请求 all-databases、_unstable-all-types、sqlite-preupdate-hook。

**待补证据。** 这是构建配置差异。需要安装工作区内可用的固定 Rust 工具链，抽取明确版本的真实文档示例，并在消费者 crate 编译。先关照页面已有 feature 说明和 Tokio 的 cfg 项。

**投稿定位和主要威胁。** Short；须控制平台 target、依赖锁和网络下载。当前环境未发现 Cargo。与 I08 生成 SDK 未知枚举失效独立。

[数据清单](data_manifest.json)

## 定向查新记录

2026-11-14 UTC，Codex 通用网页搜索及学术发现。相关结果窗口见 [检索台账](../../novelty_search.json)。

- site:github.com doc "examples" "default" "rustdoc" "target" feature flags doctest feature combinations issue
- "documentation tests" "feature" "doctest" empirical study documentation examples configuration rust doctest cargo
- "doctest" "feature flags" cargo rustdocs target docs.rs hidden examples compile feature issue
- "documentation examples" executed empirical study project documentation test code snippets software engineering
- docs.rs feature flags "doctest" issue docs.rs rust docs all features tests crate
- site:github.com/rust-lang/docs.rs feature flags "default" docs examples cargo test documented
- "documentation" "code examples" Rust libraries empirical "rustdoc" rdoc data tool authors
- rust doctest docs.rs all-features "doctest" "default" feature crate issue
- site:github.com tokio serde clap "docs.rs" "all-features" docs.rs features configuration Cargo.toml
- rust docs.rs compare documented default features flag doc cfg Cargo serde tokio sqlx user missing feature
- crates.io feature usage "empirical" Cargo optional features dependency ecosystem feature unification Rust study
- "Leveraging" Rust code-document violations rustdoc 2021 rdoc authors DOI
- docs.rs "all-features" "default" "doc examples" feature rust cargo check rustdoc published feature metadata
- site:github.com tokio feature "enable the" "docs.rs" "sync" unresolved import tokio issue
- site:github.com "docs.rs" "example" "runtime-tokio" sqlx feature missing example cargo
- site:github.com tokio docs "feature flag" "example" "unresolved" tokio default issue docs
- Rust documentation test feature configurations docs.rs documentation code examples test validation feature flags

