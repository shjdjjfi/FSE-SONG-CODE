# Full I01 measured tables

## Strict pip wheel-only dry run: target × platform

|Platform|Python|Resolvable|Decisive|Rate|
|---|---|---:|---:|---:|
|linux_amd64|3.8|44|117|37.6%|
|linux_amd64|3.10|64|117|54.7%|
|linux_amd64|3.12|59|117|50.4%|
|linux_amd64|3.14|45|117|38.5%|
|windows_amd64|3.8|43|116|37.1%|
|windows_amd64|3.10|61|115|53.0%|
|windows_amd64|3.12|59|116|50.9%|
|windows_amd64|3.14|52|116|44.8%|
|macos_arm64|3.8|25|115|21.7%|
|macos_arm64|3.10|60|116|51.7%|
|macos_arm64|3.12|60|117|51.3%|
|macos_arm64|3.14|54|117|46.2%|

## `uv` (documented relaxed upper-bound) full resolver: target × platform

|Platform|Python|Resolvable|Decisive|Rate|
|---|---|---:|---:|---:|
|linux_amd64|3.8|44|117|37.6%|
|linux_amd64|3.10|64|117|54.7%|
|linux_amd64|3.12|60|117|51.3%|
|linux_amd64|3.14|46|117|39.3%|
|windows_amd64|3.8|43|117|36.8%|
|windows_amd64|3.10|64|117|54.7%|
|windows_amd64|3.12|63|117|53.8%|
|windows_amd64|3.14|58|117|49.6%|
|macos_arm64|3.8|25|117|21.4%|
|macos_arm64|3.10|62|117|53.0%|
|macos_arm64|3.12|62|117|53.0%|
|macos_arm64|3.14|57|117|48.7%|

## OSV advisory-year strata (`uv` policy)

|Stratum|Success|Decisive|Rate|
|---|---:|---:|---:|
|early|220|468|47.0%|
|middle|218|480|45.4%|
|recent|210|456|46.1%|

## OSV advisory-year strata (strict pip policy)

|Stratum|Success|Decisive|Rate|
|---|---:|---:|---:|
|early|220|467|47.1%|
|middle|208|476|43.7%|
|recent|198|453|43.7%|

## Baselines on independent `pip --no-deps`

|Model|Correct|Tested|Accuracy|False-safe|False-blocked|
|---|---:|---:|---:|---:|---:|
|b0_requires_python|209|282|74.1%|73|0|
|b1_tags|247|282|87.6%|35|0|
|b2_root_gate|282|282|100.0%|0|0|

## Exact paired McNemar tests against B2 (preregistered pip root holdout)

|Comparison|Pairs|B2-only correct|Baseline-only correct|Exact two-sided p|Holm-adjusted p|
|---|---:|---:|---:|---:|---:|
|b2_vs_b0_requires_python|282|73|0|2.1176e-22|4.2352e-22|
|b2_vs_b1_tags|282|35|0|5.8208e-11|5.8208e-11|
