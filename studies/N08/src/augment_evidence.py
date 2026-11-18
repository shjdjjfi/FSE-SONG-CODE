#!/usr/bin/env python3
"""Collect source-grounded code-change cues for researcher judgment.

No output of this script is an independently adjudicated expertise label.
Only short changed-line samples are stored; complete patches remain at GitHub.
"""

import concurrent.futures
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

from harvest import fetch, write_json
from analyze import DATA, RESULTS, read_json

CODE_ENDINGS = ('.ts', '.tsx', '.js', '.jsx', '.go', '.py', '.rs', '.java', '.cs', '.c', '.cpp', '.h')
HUNK_RE = re.compile(r'^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@')


def summarize_patch(raw, prefix):
    files, path, code_changed, all_changes, examples = [], '', False, 0, []
    changed = []
    for line in raw.decode('utf-8', 'replace').splitlines():
        if line.startswith('diff --git a/'):
            parts = line.split(' ', 3)
            path = parts[3][2:] if len(parts) == 4 and parts[3].startswith('b/') else ''
            code_changed = path.startswith(prefix) and path.endswith(CODE_ENDINGS) and not any(
                z in path.lower() for z in ('.test.', '.spec.', '/test/', '/tests/'))
            if path.startswith(prefix):
                files.append(path)
            continue
        if code_changed and line[:1] in ('+', '-') and not line.startswith(('+++', '---')):
            all_changes += 1
            # Preserve code signals for visual inspection; truncate and cap globally.
            if len(examples) < 32:
                examples.append({'file': path, 'change': line[:1], 'code': line[1:].strip()[:180]})
            changed.append(line[1:].strip())
    substantive_tokens = [s for s in changed if s and not s.startswith(('//', '/*', '*', 'import ', 'export {'))]
    guard = sum(bool(re.search(r'\b(if|else|return|throw|await|try|catch|switch|case|for|while|filter|map|find|some|every)\b|=>', s)) for s in substantive_tokens)
    logic = sum(bool(re.search(r'[=!<>]=|\?\.|\&\&|\|\||\b(true|false|null|undefined)\b', s)) for s in substantive_tokens)
    return {'target_files': sorted(set(files)), 'target_code_changed_lines': all_changes,
            'noncomment_nonimport_changed_lines': len(substantive_tokens),
            'control_flow_or_callback_lines': guard, 'branch_or_comparison_lines': logic,
            'examples': examples, 'automated_code_semantic_signal_only': 'present' if guard or logic else 'undetermined'}


def main():
    rows = read_json(RESULTS / 'predictions.json')
    events = {p.stem: read_json(p) for p in (DATA / 'events').glob('*.json')}
    outdir = DATA / 'semantic_evidence'
    outdir.mkdir(exist_ok=True)
    errors = {}
    def one(row):
        event, repo, pr = row['event'], row['repo'], row['pr']
        path = outdir / f'{event}__{pr}.json'
        if path.exists():
            return read_json(path)
        url = f'https://github.com/{repo}/pull/{pr}.patch'
        buf, _ = fetch(url, timeout=25, attempts=2)
        audit = DATA / 'diff_audit' / f'{event}__{pr}.json'
        prior = read_json(audit) if audit.exists() else {}
        digest = hashlib.sha256(buf).hexdigest()
        if prior and prior['sha256'] != digest:
            raise ValueError(f'Patch content SHA mismatch for {event} #{pr}: source changed or different response')
        summary = {'event': event, 'repository': repo, 'pr': pr, 'url': url,
                   'sha256': digest, 'bytes': len(buf), 'fetched_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                   'migration_url': f"https://github.com/{repo}/pull/{events[event]['migration_pr']}",
                   **summarize_patch(buf, events[event]['new_prefix'])}
        write_json(path, summary)
        return summary
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(one, row): row for row in rows}
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                row = futures[future]
                errors[f"{row['event']}__{row['pr']}"] = str(exc)
    summaries = [read_json(x) for x in sorted(outdir.glob('*.json'))]
    write_json(RESULTS / 'researcher_evidence_index.json', {
        'total': len(rows), 'collected': len(summaries), 'errors': errors,
        'interpretation': 'Source-grounded code snippets for one researcher; never independent human expert truth',
        'entries': [{k: v for k, v in row.items() if k not in ('examples',)} for row in summaries]})
    md = ['# PR code evidence available to a researcher', '',
          'Source-grounded patch excerpts; **not independently blinded, not expertise ground truth**.', '']
    for s in summaries:
        md.extend([f"## {s['event']} — [PR #{s['pr']}]({s['url']})", '',
                   f"Files: {len(s['target_files'])}; target code diff lines: {s['target_code_changed_lines']}; logic cues: {s['control_flow_or_callback_lines']}.", ''])
        for x in s['examples'][:10]:
            md.append(f"- `{x['file']}` `{x['change']}` `{x['code'].replace('`', '')}`")
        md.append('')
    (RESULTS / 'RESEARCHER_PR_EVIDENCE.md').write_text('\n'.join(md), encoding='utf-8')
    print('PATCH_SUMMARIES', len(summaries), 'ROWS', len(rows), 'FAILED', len(errors))
    if errors:
        print('ERRORS', json.dumps(errors, ensure_ascii=False)[:1200])


if __name__ == '__main__':
    main()
