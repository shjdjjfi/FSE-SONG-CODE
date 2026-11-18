# Table 1. Controlled simulations; NOT measured field performance

| Policy | Recall (positive) | False-page rate (negative) | False pages/100 simulated h | Delay among detected (min) |
|---|---:|---:|---:|---:|
| instance | 0.314 | 0.200 | 10.64 | 0.0 |
| service | 0.314 | 0.000 | 0.00 | 0.0 |
| targetdown10 | 0.314 | 0.200 | 10.64 | 0.0 |
| service_grace | 1.000 | 0.317 | 16.85 | 0.0 |
| targetdown10_grace | 1.000 | 0.318 | 16.91 | 0.0 |
| owner_no_gap | 0.314 | 0.000 | 0.00 | 0.0 |
| owner_lookback | 0.922 | 0.117 | 6.27 | 0.0 |
| owner_relink | 0.769 | 0.032 | 1.71 | 0.0 |
| owner_relink_v2 | 0.942 | 0.111 | 5.91 | 0.0 |
| owner_no_probe | 0.769 | 0.071 | 3.78 | 0.0 |
| probe_latch | 0.964 | 0.262 | 14.43 | 1.25 |
