# N21: verified GitHub-hosted Attest/typescript-cache-action results

Corrected runs: 3; actual Ubuntu-22.04 hosted jobs: 45; individual measurements: 42.
**All faults deliberately injected; none is a natural production CI incident. No valid incidence denominator or industrial ROI.**

## Direct raw-run links

- [Run 44237916114](https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44237916114) — commit a1d6723c1851006cd69de8db0d98861b666b782b; 15/15 jobs; 14/14 case artifacts; sum of job elapsed times 276 s (coarse).
- [Run 44238758566](https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44238758566) — commit 403d5fd951750ce45714372ca69f0134d34305e3; 15/15 jobs; 14/14 case artifacts; sum of job elapsed times 306 s (coarse).
- [Run 44238773494](https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44238773494) — commit 876c3f33de01690a5fc6165059b18a6b75110ca8; 15/15 jobs; 14/14 case artifacts; sum of job elapsed times 207 s (coarse).

Pilot [run 44237397496](https://github.com/shjdjjfi/FSE-EXP-1/actions/runs/44237397496) excluded from timing: generated declarations erroneously entered the input fingerprint.

## Runner observations (median and range, not statistically generalizable)

| Cache | Fault | Strategy | SHA correct | Strategy wall s median [min,max] | Internal cache restore s | Compressed cache B | SHA scan B |
|---|---|---|---:|---:|---:|---:|---:|
| complete | corrupt_dts | attest_only | 0/3 | 0.145 [0.117,0.145] | 0.583 | 3879 | 0 |
| complete | corrupt_dts | clean_all | 3/3 | 1.594 [1.300,3.327] | 0.470 | 3879 | 0 |
| complete | corrupt_dts | guarded_sha | 3/3 | 0.901 [0.809,0.950] | 0.385 | 3879 | 369 |
| complete | extra_stale | attest_only | 0/3 | 0.608 [0.201,0.871] | 0.606 | 3879 | 0 |
| complete | extra_stale | force_all | 0/3 | 1.833 [1.287,1.922] | 0.464 | 3879 | 0 |
| complete | extra_stale | guarded_sha | 3/3 | 0.972 [0.729,1.788] | 0.412 | 3879 | 369 |
| complete | none | attest_only | 3/3 | 0.143 [0.142,1.752] | 0.721 | 3879 | 0 |
| complete | none | guarded_sha | 3/3 | 0.222 [0.214,0.725] | 0.398 | 3879 | 339 |
| miss | none | attest_only | 3/3 | 1.928 [1.568,2.067] | 0.304 | 0 | 0 |
| miss | none | guarded_sha | 3/3 | 1.607 [1.425,1.794] | 0.252 | 0 | 0 |
| partial | none | attest_only | 0/3 | 0.204 [0.144,1.611] | 0.789 | 3863 | 0 |
| partial | none | clean_all | 3/3 | 1.702 [1.058,1.745] | 0.485 | 3863 | 0 |
| partial | none | force_all | 3/3 | 1.355 [0.910,1.370] | 0.705 | 3863 | 0 |
| partial | none | guarded_sha | 3/3 | 1.254 [0.964,1.939] | 0.714 | 3863 | 209 |

Strategy wall time includes detection/hash/repair; excludes checkout, npm install and Attest restoration. Internal cache restore timer comes from raw job logs (millisecond precision). GitHub REST composite duration is seconds precision. Separate strategies run on different ephemeral runners, not the same machine.

## Bounded engineering-economics calculation (not production ROI)

Intact-hit guard extra work median: +0.080 seconds. Against clean_all, guard saves +0.448 seconds for artificial partial and +0.692 seconds for artificial corrupted declaration.
Toy two-state break-even input fault proportions (assuming stable costs, only one damaged state and an idealized baseline that somehow knows which runs need clean_all at zero detection cost): partial=0.15111, corrupt=0.10326. These are modeled thresholds, NOT measured event rates, deployment financial ROI or engineering effort.

## Reproducibility

Each included results/github_actions_run_<id> folder contains REST run/jobs/artifact metadata, all 15 original ZIPs, all 15 complete logs and 15 JSON payloads. Per-job evidence hashes, actual transfer bytes, cache action timer, CPU and strategy timing are included in github_actions_aggregate.json and CSV. Total runner-job elapsed seconds summed across parallel jobs: 789 s, a usage proxy NOT GitHub billed time or a dollar charge. Release ZIP contains SHA-256 manifest.
