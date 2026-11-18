# Source archives

Each SHA-256 identifies the supplied ZIP before import. The table maps it to
the study directory in this repository. See [publication notes](PUBLICATION_NOTES.md)
for the publication scope and [external inputs](EXTERNAL_INPUTS.tsv) for exact
checksums of files retained outside Git.

| Supplied ZIP | Study directory | SHA-256 |
| --- | --- | --- |
| `I01_FSE2027_Industry_Extended_CPU_20261114.zip` | [I01](../studies/I01) | `b023a4c6a56f5e9f9e84c0090465bbb6ee6fad6b496e4df3b01983fe7c0378d2` |
| `N02_Helm_Config_Intent_Experiments.zip` | [N02](../studies/N02) | `3fa467fa8d503a422e05738c65af66b977aa0b4acaffffdb5fac1d8015f530af` |
| `N02_Helm_Intent_Phase3_External_Challenge.zip` | [N02](../studies/N02) | `88403602fd9c18d6d53a228df85d9c87a44d262e339b9e662ed56ac489842f3f` |
| `N04_FSE2027_Experiments_20261115.zip` | [N04/base](../studies/N04/base) | `c8f5f366fc6266dd60f80493b6bb7493efb81016e94e6f7035b336edbe29ae01` |
| `N04_FSE2027_Expanded_Experiments_20261115.zip` | [N04/expanded](../studies/N04/expanded) | `34d2c5f6d8fcaf557f112c4b2eba07b92610f28c286dd0a3e278f173b2a1eebf` |
| `N05_FSE2027_Experiments_And_Evidence.zip` | [N05](../studies/N05) | `8f4074c94764299eb963ba10e41aefddcfeafea808fe1de1210a3cf9a5791caf` |
| `N06_FSE2027_Experiments.zip` | [N06](../studies/N06) | `bfa67cd7a714d7a35796dc458d0bc392eb33ef51e67f5af1f67e618fb841e98e` |
| `FSE2027_N08_Experimental_Evidence.zip` | [N08](../studies/N08) | `a5a98f4bcd736ee4f25899c942fd33bcaeccc7185b2559e69747d7c56cf44ea3` |
| `N21_FSE2027_Industry_Experiments.zip` | [N21](../studies/N21) | `43734e948a037fed19a0e2aff979320832a65662bd9d94bc8812ca0cafe2748f` |
| `N22_FSE2027_Industry_Experiments.zip` | [N22/base](../studies/N22/base) | `4e3de7a93e1520f7d6a6c25084bd529e7bb19bd7beb4765aa730ff5f0083a010` |
| `N22_FSE_Industry_full_artifact_20261118.zip` | [N22/addendum-20261118](../studies/N22/addendum-20261118) | `c44bd83e26494991857d61fef4994651290562258389d022970a8422dddc7146` |
| `N24_FSE2027_Complete_Experiments.zip` | [N24](../studies/N24) | `95c1206c3ee3d9154e1f9f97860dcc9913243c4b48e5f861ca44cb31e19d6731` |

The standalone N02 baseline and the cumulative bundle contain byte-identical
phase-1 files apart from their readmes. The standalone readme is available as
[README_PHASE1.md](../studies/N02/README_PHASE1.md). N04 and N22 each have two
distinct study directories. The nested I01 baseline was unpacked at
[`studies/I01/i01_full`](../studies/I01/i01_full).
