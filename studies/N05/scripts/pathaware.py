#!/usr/bin/env python3
"""Generic source-path feature hints, frozen before third-cohort search."""
import re

import replay

PATH_BONUS = 30


def candidate_features_v2(meta, row):
    original = replay.candidate_features(meta, row)
    path = row.get("source", "")
    components = {segment.lower().replace("-", "_") for segment in
                  re.split(r"[/\\]", path) if segment and segment.lower() not in
                  ("src", "lib.rs", "mod.rs", "main.rs", "readme.md")}
    parts = {p for segment in components for p in re.findall(r"[a-z0-9_]+", segment)}
    # Full-feature labels in a feature-gated source directory are strong
    # hypotheses; otherwise maintain the untouched original ranking.
    scored = []
    for idx, feature in enumerate(original):
        spelling = feature.lower().replace("-", "_")
        bonus = PATH_BONUS if spelling in parts else 0
        scored.append((-bonus, idx, feature))
    return [f for _, _, f in sorted(scored)]
