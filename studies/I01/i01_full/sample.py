#!/usr/bin/env python3
"""Reproducible project-disjoint, advisory-year-balanced OSV sample."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import zipfile

from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'raw/osv-pypi-20261114.zip'
SEED = 'i01-20261114-project-'


def main():
    candidates = defaultdict(dict)
    corpus_count = 0
    withdrawn_count = 0
    with zipfile.ZipFile(SOURCE) as z:
        for filename in sorted(v for v in z.namelist() if v.endswith('.json')):
            corpus_count += 1
            doc = json.loads(z.read(filename))
            if doc.get('withdrawn'):
                withdrawn_count += 1
                continue
            published = doc.get('published') or ''
            if len(published) < 4 or not published[:4].isdigit():
                continue
            for item in doc.get('affected', []):
                package = item.get('package') or {}
                if package.get('ecosystem') != 'PyPI' or not package.get('name'):
                    continue
                name = canonicalize_name(package['name'])
                fixed = []
                for r in item.get('ranges', []):
                    if r.get('type') != 'ECOSYSTEM':
                        continue
                    for event in r.get('events', []):
                        if 'fixed' not in event:
                            continue
                        try:
                            v = Version(event['fixed'])
                        except (InvalidVersion, TypeError):
                            continue
                        if not (v.is_prerelease or v.is_devrelease):
                            fixed.append((v, event['fixed']))
                if not fixed:
                    continue
                osv_id = doc['id']
                prev = candidates[name].get(osv_id)
                curr = {
                    'project': name,
                    'osv_id': osv_id,
                    'published': published,
                    'modified': doc.get('modified'),
                    'summary': (doc.get('summary') or '')[:350],
                    'aliases': doc.get('aliases') or [],
                    'all_final_fixes': sorted(set([v for _, v in fixed]), key=Version),
                }
                if prev:
                    curr['all_final_fixes'] = sorted(set(prev['all_final_fixes'] + curr['all_final_fixes']), key=Version)
                candidates[name][osv_id] = curr

    frame = []
    for project, advisories in candidates.items():
        # Latest advisory first, ID ascending to break identical publication timestamps.
        latest = sorted(advisories.values(), key=lambda d: (d['published'], d['osv_id']))[-1]
        latest['fixed_version'] = latest['all_final_fixes'][0]
        year = int(latest['published'][:4])
        latest['stratum'] = 'early' if year <= 2023 else 'middle' if year <= 2025 else 'recent'
        latest['sampling_hash'] = hashlib.sha256((SEED + project).encode()).hexdigest()
        frame.append(latest)

    strata = defaultdict(list)
    for rec in frame:
        strata[rec['stratum']].append(rec)
    selected = []
    for key in ['early', 'middle', 'recent']:
        ordered = sorted(strata[key], key=lambda rec: rec['sampling_hash'])
        assert len(ordered) >= 40, (key, len(ordered))
        selected.extend(ordered[:40])
    selected.sort(key=lambda rec: ('early', 'middle', 'recent').index(rec['stratum']) * 1000 + int(rec['sampling_hash'][:6], 16) / 2**24)
    assert len({x['project'] for x in selected}) == 120
    summary = {
        'source_zip_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'corpus_json_entries': corpus_count,
        'withdrawn_entries': withdrawn_count,
        'eligible_unique_projects': len(frame),
        'eligible_project_strata': dict(Counter(rec['stratum'] for rec in frame)),
        'selected_unique_projects': len(selected),
        'selected_strata': dict(Counter(rec['stratum'] for rec in selected)),
        'selection_key': SEED,
        'selection_procedure': 'latest published OSV per project; first final fix; lowest SHA256(project+seed) per year stratum',
    }
    (ROOT/'sampling_summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    (ROOT/'osv_sample120.json').write_text(json.dumps(selected, indent=2, ensure_ascii=False))
    print(json.dumps(summary, indent=2))
    print('First 20 selected:', ', '.join(x['project'] for x in selected[:20]))


if __name__ == '__main__':
    main()
