# N24 hosted evidence manifest

All eight ZIP files were downloaded from the completed GitHub Actions [run 44245392156](https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44245392156), commit `995fb33438e3f530f1b348b7bdc18f2673296561`, on 18 November 2026. The SHA-256 digests below were independently computed on the downloaded ZIP bytes and match the recorded GitHub artifact digests. These are unedited CI output artifacts, included verbatim in the companion experiment evidence archive.

| Evidence ZIP in archive | GitHub artifact ID | SHA-256 |
|---|---:|---|
| `runner_artifacts/host_linux.zip` | 14400614619 | `339f9a9be83d22e0d3544d8bb875359d0964e97d10337c08aabc8f836fd6c1cc` |
| `runner_artifacts/host_macos.zip` | 14401229415 | `d2f8b30c13fc073bcc4138cca07e5940c00c1e6ee5377de2934474cd19650fcc` |
| `runner_artifacts/host_windows.zip` | 14401703179 | `7cba8506529d72a7dbd0cf55f568b78c9f60582fcde72c0ce98fd320c15a731e` |
| `runner_artifacts/history_linux.zip` | 14402270185 | `ad64ae616b737cbea8d1e4714ef9a0d9581c7b899a6d90dc6e404e60c2ee4df8` |
| `runner_artifacts/history_macos.zip` | 14401743067 | `e95e3eb5bad79017d77ed488ab9c5506fd1753eefd220f2a85a16271306adbde` |
| `runner_artifacts/history_windows.zip` | 14402425580 | `6bb494e229a1d252acf0e17da72d54da1fad35493f6978f61e5c73702789e29a` |
| `runner_artifacts/aggregate.zip` | 14401114586 | `42db6907d2fc3fd485d49602e3ca02d35266b61cafec5bb9ec665a4ba51f5a13` |
| `runner_artifacts/aggregate_history.zip` | 14402430534 | `54b7fc3fe0c3257282d7103c92021a91f891f2146aaa53a1703119cd9cdfe9e9` |

The original `aggregate_history.zip` faithfully retains a **known analysis bug**: for a project with three native parent packages, it counted its lockfile version churn three times. The corrected repository-root `N24_CORRECTED_HISTORICAL_AGGREGATES.json` was recomputed from the original Linux/Windows/macOS `history_*.zip` contents using the corrected `analyze_history.py`. The original per-host experiment data, success/failure outcomes, and timestamps were **not changed**. In particular, the proper non-target version churn totals for the 9 unique project–host locks are 261 for npm11, 261 for npm12, and 1,113 for full regeneration. Treat these as aggregate version-change *counts*, not person-hours or monetary costs.

The controlled aggregated summary was likewise recomputed independently from three original `host_*.zip` contents; its 150 observations and 4/4 workflow-job success were verified. Raw output may contain machine-local temporary paths and npm diagnostics; no private access credentials or customer data were intentionally collected.
