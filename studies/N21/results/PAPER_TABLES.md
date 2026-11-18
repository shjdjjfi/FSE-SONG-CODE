# Main N21 Paper Tables

Seed 17; 77 distinct fault/project settings and 13 project units in four workspaces. Each strategy sees the **same 77 injected settings**; input changes are evaluated separately.

| Strategy | Exact clean-oracle agreement | Median rebuilt source units (proxy) | Median measured seconds |
|---|---:|---:|---:|
| Unforced tsc -b | 0/77 | 0.0 | 0.18 |
| Path manifest | 55/77 | 2.0 | 1.11 |
| Output SHA manifest | 77/77 | 3.0 | 1.48 |
| Input-guarded SHA (ours) | 77/77 | 3.0 | 1.74 |
| Invalidate all buildinfo | 64/77 | 4.0 | 3.00 |
| Clean build | 77/77 | 4.0 | 2.98 |
| Force full solution | 64/77 | 4.0 | 3.05 |
| Complete local cache hit | 77/77 | 0.0 | 0.01 |

**Interpretation.** A complete cache hit is an *available-cache* ideal comparator. The same 77 cases include deletion, content corruption, and extra-output faults, so even `--force` does not make every case correct. Source-file units are project-level proxies; times are local, shared-machine timings, not industrial CI performance.

## Per-project repair cost (input-guarded hash vs clean)

| Workspace / project | Source files | Emitted files | Median rebuilt units (guarded / clean) | Median saved units | Median time saved (s) |
|---|---:|---:|---:|---:|---:|
| typescript/compiler | 78 | 156 | 252 / 252 | 0 | -0.47 |
| typescript/jsTyping | 6 | 12 | 174 / 252 | 78 | +10.73 |
| typescript/services | 168 | 336 | 168 / 252 | 84 | +13.64 |
| libraries/ts-pattern | 18 | 36 | 18 / 37 | 19 | +0.49 |
| libraries/zod | 13 | 26 | 13 / 37 | 24 | +0.89 |
| libraries/neverthrow | 5 | 10 | 5 / 37 | 32 | +1.99 |
| libraries/mitt | 1 | 2 | 1 / 37 | 36 | +2.26 |
| andrewthauer/core | 1 | 4 | 2 / 4 | 2 | +0.71 |
| andrewthauer/api | 1 | 4 | 3 / 4 | 1 | -0.07 |
| andrewthauer/cli | 1 | 4 | 1 / 4 | 3 | +1.37 |
| andrewthauer/web | 1 | 2 | 1 / 4 | 3 | +1.34 |
| quramy/x-core | 1 | 3 | 4 / 4 | 0 | -0.60 |
| quramy/x-cli | 3 | 9 | 3 / 4 | 1 | -0.19 |
