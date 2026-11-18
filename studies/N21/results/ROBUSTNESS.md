# Paired robustness and sensitivity

Same 77 seed-17 settings, input-guarded SHA against clean build; all 77 paired outputs exact.
This is descriptive research-fixture data, **not an inferential independent sample**.

| Subset | Paired settings | Median fewer source units | Median fraction fewer | Median local seconds saved | Settings faster |
|---|---:|---:|---:|---:|---:|
| Overall | 77 | 3.0 | 51.3% | +1.23 | 57/77 |
| andrewthauer | 26 | 2.0 | 50.0% | +1.13 | 22/26 |
| libraries | 28 | 28.0 | 75.7% | +1.86 | 27/28 |
| quramy | 14 | 0.5 | 12.5% | -0.37 | 1/14 |
| typescript | 9 | 78.0 | 30.9% | +10.73 | 7/9 |

## Leave one workspace out (sensitivity, not confidence intervals)

| Workspace omitted | Settings retained | Median fraction fewer source units | Median local seconds saved |
|---|---:|---:|---:|
| andrewthauer | 51 | 51.3% | +1.44 |
| libraries | 49 | 30.9% | +0.50 |
| quramy | 63 | 64.9% | +1.45 |
| typescript | 68 | 51.3% | +0.97 |

## Per-project descriptive medians

| Project | Settings | Median fewer units | Median seconds saved | Settings faster |
|---|---:|---:|---:|---:|
| andrewthauer/api | 7 | 1.0 | -0.07 | 3/7 |
| andrewthauer/cli | 7 | 3.0 | +1.37 | 7/7 |
| andrewthauer/core | 7 | 2.0 | +0.71 | 7/7 |
| andrewthauer/web | 5 | 3.0 | +1.34 | 5/5 |
| libraries/mitt | 7 | 36.0 | +2.26 | 7/7 |
| libraries/neverthrow | 7 | 32.0 | +1.99 | 7/7 |
| libraries/ts-pattern | 7 | 19.0 | +0.49 | 6/7 |
| libraries/zod | 7 | 24.0 | +0.89 | 7/7 |
| quramy/x-cli | 7 | 1.0 | -0.19 | 1/7 |
| quramy/x-core | 7 | 0.0 | -0.60 | 0/7 |
| typescript/compiler | 3 | 0.0 | -0.47 | 1/3 |
| typescript/jsTyping | 3 | 78.0 | +10.73 | 3/3 |
| typescript/services | 3 | 84.0 | +13.64 | 3/3 |

The unit metric is compiler-logged rebuilt-project source-file counts, not CPU instructions.
Do not treat faults, seeds, or project units from the same repository as independent industrial incidents.
