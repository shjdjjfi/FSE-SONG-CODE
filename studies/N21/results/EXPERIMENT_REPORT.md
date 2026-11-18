# N21: Measured Experiment Summary

_Recomputed solely from archived trial records._

Analyzed 920 trials in 4 workspaces and 13 distinct projects; seeds [17, 29, 43].

| Strategy | Correct / injected cases | Median source units rebuilt | Median wall time |
|---|---:|---:|---:|
| `standard` | 0/101 | 0 | 0.184 s |
| `selective_path` | 71/101 | 3 | 1.15 s |
| `selective_hash` | 77/77 | 3 | 1.484 s |
| `guarded_hash` | 101/101 | 3 | 1.981 s |
| `invalidate_all` | 64/77 | 4 | 3.0 s |
| `clean_all` | 101/101 | 4 | 2.948 s |
| `force_all` | 64/77 | 4 | 3.051 s |
| `full_cache` | 101/101 | 0 | 0.011 s |

A full cache hit restores complete outputs without compilation and is therefore not the same operating condition as an unavailable/incomplete cache.
The comparisons are conditional on preexisting input/output identity. Exact manifests are generated from a trusted prior build.

## Separate workspaces

| Workspace | Arm | Correct / cases | Median units | Median time |
|---|---|---:|---:|---:|
| andrewthauer | standard | 0/32 | 0.0 | 0.179 s |
| andrewthauer | selective_path | 23/32 | 1.0 | 1.316 s |
| andrewthauer | selective_hash | 26/26 | 2.0 | 1.821 s |
| andrewthauer | guarded_hash | 32/32 | 2.0 | 2.085 s |
| andrewthauer | invalidate_all | 22/26 | 4.0 | 2.69 s |
| andrewthauer | clean_all | 32/32 | 4.0 | 2.736 s |
| andrewthauer | force_all | 22/26 | 4.0 | 2.697 s |
| andrewthauer | full_cache | 32/32 | 0.0 | 0.006 s |
| libraries | standard | 0/40 | 0.0 | 0.195 s |
| libraries | selective_path | 28/40 | 5.0 | 1.078 s |
| libraries | selective_hash | 28/28 | 9.0 | 1.419 s |
| libraries | guarded_hash | 40/40 | 13.0 | 2.152 s |
| libraries | invalidate_all | 24/28 | 37.0 | 3.223 s |
| libraries | clean_all | 40/40 | 37.0 | 3.273 s |
| libraries | force_all | 24/28 | 37.0 | 3.297 s |
| libraries | full_cache | 40/40 | 0.0 | 0.022 s |
| quramy | standard | 0/20 | 0.0 | 0.183 s |
| quramy | selective_path | 14/20 | 3.0 | 1.134 s |
| quramy | selective_hash | 14/14 | 3.5 | 1.166 s |
| quramy | guarded_hash | 20/20 | 3.0 | 1.418 s |
| quramy | invalidate_all | 12/14 | 4.0 | 1.08 s |
| quramy | clean_all | 20/20 | 4.0 | 1.071 s |
| quramy | force_all | 12/14 | 4.0 | 1.043 s |
| quramy | full_cache | 20/20 | 0.0 | 0.003 s |
| typescript | standard | 0/9 | 0 | 0.161 s |
| typescript | selective_path | 6/9 | 168 | 5.874 s |
| typescript | selective_hash | 9/9 | 174 | 6.192 s |
| typescript | guarded_hash | 9/9 | 174 | 5.859 s |
| typescript | invalidate_all | 6/9 | 252 | 15.959 s |
| typescript | clean_all | 9/9 | 252 | 16.251 s |
| typescript | force_all | 6/9 | 252 | 15.692 s |
| typescript | full_cache | 9/9 | 0 | 0.095 s |

## Main paired comparison (hash-manifest vs alternatives)

- `selective_hash_vs_force_all`: 64 pairs where **both** methods were correct; median saved source-file proxy 3.0, median reduction 51.4%, median wall-time difference 1.296 seconds. These repeated faults are correlated within projects.
- `selective_hash_vs_invalidate_all`: 64 pairs where **both** methods were correct; median saved source-file proxy 3.0, median reduction 51.4%, median wall-time difference 1.327 seconds. These repeated faults are correlated within projects.
- `selective_hash_vs_clean_all`: 77 pairs where **both** methods were correct; median saved source-file proxy 3, median reduction 51.4%, median wall-time difference 1.331 seconds. These repeated faults are correlated within projects.
- `selective_hash_vs_full_cache`: 77 pairs where **both** methods were correct; median saved source-file proxy -3, median reduction n/a, median wall-time difference -1.476 seconds. These repeated faults are correlated within projects.
- `guarded_hash_vs_force_all`: 64 pairs where **both** methods were correct; median saved source-file proxy 3.0, median reduction 51.4%, median wall-time difference 1.076 seconds. These repeated faults are correlated within projects.
- `guarded_hash_vs_invalidate_all`: 64 pairs where **both** methods were correct; median saved source-file proxy 3.0, median reduction 51.4%, median wall-time difference 1.345 seconds. These repeated faults are correlated within projects.
- `guarded_hash_vs_clean_all`: 101 pairs where **both** methods were correct; median saved source-file proxy 3, median reduction 51.4%, median wall-time difference 0.776 seconds. These repeated faults are correlated within projects.
- `guarded_hash_vs_full_cache`: 101 pairs where **both** methods were correct; median saved source-file proxy -3, median reduction n/a, median wall-time difference -1.974 seconds. These repeated faults are correlated within projects.

## Scientific cautions

- All observed faults were deliberately injected, not sampled from real CI failure logs.
- Repository-level dependence precludes treating every trial or random seed as an independent sample.
- full_cache is an idealized *available complete cache hit*; this baseline must be conditioned on availability.
- Units count project source files for projects reported as rebuilt; not instructions or CPU work.
