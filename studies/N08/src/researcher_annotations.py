#!/usr/bin/env python3
"""One non-blinded model-assisted researcher reading of available PR patches.

The user authorized the assistant to act as expert; do NOT pass this off as
independent human adjudication, two annotators, historic team membership, or
named-reviewer truth. Unknown remains unknown and is never imputed negative.
"""

import collections
import csv
import json
import statistics
from pathlib import Path

from analyze import DATA, RESULTS, read_json, save_json

# These entries were assessed after inspecting source-grounded patch excerpts
# and feature titles. The researcher also previously saw method results, so
# this is explicitly non-blind and exploratory, not confirmatory ground truth.
RESEARCHER_SUBSTANCE = {
    'BW10818': {
        12187:'yes',12907:'yes',13039:'yes',13287:'yes',13598:'yes',13609:'yes',
        14953:'yes',15070:'yes',15047:'yes',15140:'yes',15957:'yes'},
    'BW11709': {
        12646:'yes',12655:'yes',13576:'yes',14539:'yes',14942:'yes',14900:'yes',16820:'unknown'},
    'BW12407': {12853:'yes',12854:'yes',12875:'yes'},
    'BW13285': {
        14277:'yes',14388:'yes',14398:'yes',14538:'yes',15153:'yes',14432:'yes',
        15138:'unknown',16865:'unknown',17742:'unknown',17771:'unknown',18413:'unknown'},
    'BW14571': {14850:'unknown',16823:'unknown',16952:'unknown',16939:'unknown',16987:'yes',17434:'yes'},
    'BW15093': {
        15273:'yes',15362:'yes',15522:'no',15610:'yes',15620:'yes',
        15777:'yes',15827:'yes',16002:'no',16433:'yes',16748:'yes'},
    'GF104424': {
        105068:'yes',109309:'yes',110619:'yes',111338:'yes',112880:'yes',
        114196:'yes',115959:'yes',116308:'yes',116434:'yes',117061:'yes'},
}

EXPLANATIONS = {
    'BW10818':'Changed biometrics unlock, key-storage, OS prompt, IPC or cryptographic state inside the actual migrated component.',
    'BW11709':'Changed account-key encryption, rotation, trust or API logic inside the migrated key-rotation component.',
    'BW12407':'Changed biometric prompt decision or cached reload state inside the migrated lock component.',
    'BW13285':'Changed encryption behavior, type-0 rejection, SDK delegation or decryption contract in migrated cryptographic service.',
    'BW14571':'Changed report filtering or item inclusion behavior in migrated reports component.',
    'BW15093':'Changed conditional icon/layout configuration or runtime layout lifecycle in migrated anonymous layout.',
    'GF104424':'Changed alerting receiver/routing API behavior, integration conversion or storage semantics in the transferred subtree.',
}


def main():
    rows = read_json(RESULTS / 'predictions.json')
    focused = {(r['event'],r['pr']) for r in read_json(RESULTS / 'focused_predictions.json')}
    events = {p.stem:read_json(p) for p in (DATA/'events').glob('*.json')}
    judgments=[]
    for row in rows:
        event,n = row['event'],row['pr']
        evidence_file = DATA/'semantic_evidence'/f'{event}__{n}.json'
        audit_file = DATA/'diff_audit'/f'{event}__{n}.json'
        evidence = read_json(evidence_file) if evidence_file.exists() else None
        diff = read_json(audit_file)
        judgment = RESEARCHER_SUBSTANCE.get(event,{}).get(n,'unknown')
        # Fail closed if a researcher marked yes/no but the independently
        # fetched patch evidence is unavailable or disagrees with prior hash.
        if evidence is None:
            judgment='unknown'
        elif evidence['sha256'] != diff['sha256']:
            raise AssertionError(f'Patch mismatch: {event} {n}')
        title = next((x['title'] for x in events[event]['histories']['after']['records'] if x['pr']==n),'')
        if judgment == 'yes':
            summary = EXPLANATIONS[event]
        elif judgment == 'no':
            summary = ('Changed illustration/icon presentation without directly changing the inherited review-domain '
                       'business invariant in the sampled migrated code files.')
        else:
            summary = ('Insufficient reviewed patch context to decide semantic continuity confidently.'
                       if not evidence else 'The source excerpt and title alone do not prove relevant semantic continuity.')
        clues = [item for item in (evidence or {}).get('examples',[]) if item.get('code')][:3]
        src = row['url']+'/files'
        judgments.append({
            'annotation_id':f'{event}__{n}', 'repository':row['repo'],'event':event,'pr':n,
            'pr_title':title,'pr_diff':src,
            'migration_pr':f"https://github.com/{row['repo']}/pull/{events[event]['migration_pr']}",
            'patch_sha256':evidence['sha256'] if evidence else None,
            'has_patch_excerpts':evidence is not None,'part_of_posthoc_focused_subset':(event,n) in focused,
            'annotator':'single model-assisted researcher, previously exposed to predictions',
            'semantic_continuity_researcher_yes_no_unknown':judgment,
            # Merely seeing a code diff cannot prove a particular old employee
            # was available or needed. Do not silently turn this into yes.
            'old_team_member_required_strict_independent_yes_no_unknown':'unknown',
            'new_team_member_required_strict_independent_yes_no_unknown':'unknown',
            'independent_named_expert_handle':None,
            'legacy_code_context_might_matter':'yes' if judgment=='yes' else 'unknown' if judgment=='unknown' else 'no',
            'confidence':3 if judgment=='yes' else 2 if judgment=='no' else 1,
            'rationale':summary,
            'source_code_line_examples':clues,
            'strict_oracle_usable':False,
            'limitations':'One non-blind AI researcher; no verified historical human-team mapping or independently adjudicated named experts'})
    counts=collections.Counter(r['semantic_continuity_researcher_yes_no_unknown'] for r in judgments)
    focus_counts=collections.Counter(r['semantic_continuity_researcher_yes_no_unknown'] for r in judgments
                                     if r['part_of_posthoc_focused_subset'])
    subset_yes={(r['event'],r['pr']) for r in judgments if r['semantic_continuity_researcher_yes_no_unknown']=='yes'}
    by_event=collections.defaultdict(list)
    for r in rows:
        if (r['event'],r['pr']) in subset_yes:
            by_event[r['event']].append(r)
    estimates={}
    for method in ('current_path','git_follow','recency_follow','windowed_handoff'):
        estimates[method]=statistics.mean(statistics.mean(r['method_outcomes'][method]['recall'] for r in group)
                                            for group in by_event.values()) if by_event else None
    result={'n_pr_event_pairs':len(rows),'has_patch_evidence':sum(r['has_patch_excerpts'] for r in judgments),
            'independent_expert_oracle_usable_prs':0,
            'semantic_counts_single_researcher_not_blinded':dict(counts),
            'focused_semantic_counts_posthoc':dict(focus_counts),
            'posthoc_semantic_yes_subset_observed_reviewer_recall':estimates,
            'warning':'Do not treat the labels here as two independent experts, as a named expertise oracle, or as a confirmed positive performance result.',
            'annotations':judgments}
    save_json('single_researcher_patch_annotation.json',result)
    path=RESULTS/'SINGLE_RESEARCHER_ANNOTATIONS.csv'
    with path.open('w',newline='',encoding='utf-8') as outf:
        writer=csv.DictWriter(outf,fieldnames=['annotation_id','repository','pr_diff','pr_title',
              'has_patch_excerpts','semantic_continuity_researcher_yes_no_unknown',
              'old_team_member_required_strict_independent_yes_no_unknown',
              'new_team_member_required_strict_independent_yes_no_unknown',
              'independent_named_expert_handle','legacy_code_context_might_matter',
              'confidence','rationale','patch_sha256','annotator'])
        writer.writeheader()
        for a in judgments: writer.writerow({k:a[k] for k in writer.fieldnames})
    print('ANNOTATED',len(judgments),'PATCH_AVAILABLE',result['has_patch_evidence'],
          'YES_NO_UNKNOWN',dict(counts),'FOCUSED',dict(focus_counts),
          'STRICT_ORACLE',result['independent_expert_oracle_usable_prs'])
    print('EXPLORATORY_RECALL_ON_YES_SUBSET',json.dumps(estimates))


if __name__=='__main__':
    main()
