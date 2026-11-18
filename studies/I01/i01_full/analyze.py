#!/usr/bin/env python3
"""Recompute all study metrics from frozen sample, gate, uv and pip raw logs."""
from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import random
import re
from statistics import median

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np
from scipy.stats import binomtest

ROOT=Path(__file__).resolve().parent
FIG=ROOT/'figures'
FIG.mkdir(exist_ok=True)


def read_jsonl(path):
    if not path.exists():return {}
    out={}
    for line in path.read_text().splitlines():
        try:
            d=json.loads(line)
            out[d['case_id']]=d
        except json.JSONDecodeError:
            continue
    return out


def ratio(num,den):
    return num/den if den else None


def python_version_key(record):
    """Order dotted versions numerically (3.8 < 3.10 < 3.12 < 3.14)."""
    return tuple(int(component) for component in record['python'].split('.'))


def metric_ci(rows, metric, seed=20261114, reps=2000):
    """Stratified **project-level** bootstrap; sample 40 projects/stratum."""
    byproject=defaultdict(list)
    for x in rows:byproject[x['project']].append(x)
    groups=defaultdict(list)
    for p,records in byproject.items():groups[records[0]['stratum']].append(p)
    assert sorted(groups)==['early','middle','recent']
    rng=random.Random(seed)
    vals=[]
    for _ in range(reps):
        collected=[]
        for k in ['early','middle','recent']:
            for _ in range(40):
                p=rng.choice(groups[k]);collected.extend(byproject[p])
        value=metric(collected)
        if value is not None:vals.append(value)
    vals.sort()
    return {'point':metric(rows),'lower_95':vals[int(.025*len(vals))] if vals else None,
            'upper_95':vals[min(len(vals)-1,int(.975*len(vals)))] if vals else None,
            'bootstrap_samples':len(vals)}


def make_figures(rows):
    pylist=['3.8','3.10','3.12','3.14']
    platlist=['linux_amd64','windows_amd64','macos_arm64']
    labels=['Linux x86-64','Windows AMD64','macOS arm64']
    for field,label,path in [
        ('pip_strict_status','Strict pip dry-run','full_resolution_heatmap.png'),
        ('uv_status','uv resolution (ignores Python upper bounds)','uv_relaxed_resolution_heatmap.png')]:
        matrix=np.full((3,4),np.nan)
        count=np.zeros((3,4),dtype=int)
        for i,plat in enumerate(platlist):
            for j,py in enumerate(pylist):
                subset=[x for x in rows if x['platform']==plat and x['python']==py
                        and x['metadata_status']=='ok' and x[field] in ('success','unsat')]
                count[i,j]=len(subset)
                if subset:matrix[i,j]=sum(x[field]=='success' for x in subset)/len(subset)
        fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
        im=ax.imshow(matrix,cmap='viridis',vmin=0,vmax=1)
        ax.set_xticks(range(4),[f'Python {v}' for v in pylist])
        ax.set_yticks(range(3),labels)
        ax.set_title(f'{label}: pinned security-fix wheel and full dependency closure\n120 projects, 3 advisory-year strata',fontsize=11)
        for i in range(3):
            for j in range(4):
                if not math.isnan(matrix[i,j]):
                    ax.text(j,i,f'{100*matrix[i,j]:.1f}%\n(n={count[i,j]})',
                            ha='center',va='center',fontsize=10,
                            color='white' if matrix[i,j]<.65 else 'black')
        fig.colorbar(im,ax=ax,label='Resolvable share')
        fig.savefig(FIG/path,dpi=170)
        plt.close(fig)

    discord=np.full((3,4),np.nan)
    for i,plat in enumerate(platlist):
        for j,py in enumerate(pylist):
            subset=[x for x in rows if x['platform']==plat and x['python']==py
                    and x['metadata_status']=='ok'
                    and x['uv_status'] in ('success','unsat')
                    and x['pip_strict_status'] in ('success','unsat')]
            if subset:
                discord[i,j]=sum(x['uv_status']!=x['pip_strict_status'] for x in subset)/len(subset)
    fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
    discord_max=max(.05,float(np.nanmax(discord)))
    im=ax.imshow(discord,cmap='magma_r',vmin=0,vmax=discord_max)
    ax.set_xticks(range(4),[f'Python {v}' for v in pylist])
    ax.set_yticks(range(3),labels)
    ax.set_title('Cross-target resolver disagreement: uv versus strict pip\nBoth runs are metadata/solver checks, not application CI',fontsize=11)
    for i in range(3):
        for j in range(4):
            if not math.isnan(discord[i,j]):
                ax.text(j,i,f'{100*discord[i,j]:.1f}%',ha='center',va='center',fontsize=11,
                        color='white' if discord[i,j]>discord_max*.62 else 'black')
    fig.colorbar(im,ax=ax,label='Disagreement share')
    fig.savefig(FIG/'resolver_disagreement_heatmap.png',dpi=170)
    plt.close(fig)

    problems=Counter(x['root_reason'] for x in rows)
    cats=['ok','no_wheel_for_release','no_matching_platform_abi_wheel',
          'requires_python_or_yanked','metadata_http_404']
    counts=[problems.get(c,0) for c in cats]
    fig,ax=plt.subplots(figsize=(10,4),layout='constrained')
    b=ax.barh(range(5),counts,color=['#238b45','#e0a13f','#be5549','#d18058','#727e90'])
    ax.set_yticks(range(5),['Compatible root wheel','Fixed release has no wheel',
                           'No target-compatible wheel','Python range / yanked','Metadata HTTP 404'])
    ax.invert_yaxis();ax.set_xlabel('Target scenarios (n=1,440)')
    ax.set_title('Root-level necessary-condition preflight')
    ax.bar_label(b,padding=4);ax.set_xlim(0,max(counts)*1.16)
    fig.savefig(FIG/'preflight_diagnostics.png',dpi=170)
    plt.close(fig)

    # Study flow: explicitly show every unknown and distinguish the two
    # different full-resolution tools, rather than dropping missing cases.
    sampling=json.loads((ROOT/'sampling_summary.json').read_text())
    rootcounts=Counter(str(x['b2_root_gate']) for x in rows)
    uvc=Counter(x['uv_status'] for x in rows)
    pipc=Counter(x['pip_strict_status'] for x in rows)
    fig,ax=plt.subplots(figsize=(12.5,7.2),layout='constrained')
    ax.set_xlim(0,1);ax.set_ylim(0,1);ax.axis('off')
    def node(cx,cy,w,h,label,color):
        ax.add_patch(FancyBboxPatch((cx-w/2,cy-h/2),w,h,
                     boxstyle='round,pad=0.015,rounding_size=0.018',
                     linewidth=1.1,edgecolor='#43505a',facecolor=color))
        ax.text(cx,cy,label,fontsize=10,ha='center',va='center',linespacing=1.35)
    def arrow(x1,y1,x2,y2):
        ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',
                                    mutation_scale=15,linewidth=1.25,color='#536675'))
    node(.5,.90,.54,.085,f"OSV official PyPI archive: {sampling['corpus_json_entries']:,} JSON advisories",'#e7f0f8')
    node(.5,.75,.54,.085,f"Eligible projects with explicit ecosystem fixed version: {sampling['eligible_unique_projects']:,}",'#e7f0f8')
    node(.5,.60,.54,.085,'SHA-selected: 120 distinct projects\n40 per advisory-year stratum','#dbeedc')
    node(.5,.45,.54,.085,'1,440 pinned fixed-release targets\n4 Python versions × 3 OS platforms','#e7f0f8')
    for a,b in [(0.85,0.805),(0.705,0.655),(0.555,0.505)]:arrow(.5,a,.5,b)
    node(.17,.20,.28,.22,f"Independent root preflight (B2)\npass: {rootcounts['True']}\nfail: {rootcounts['False']}\nmetadata unknown: {rootcounts['None']}",'#fff0d7')
    node(.50,.20,.28,.22,f"uv full resolution\nsuccess: {uvc['success']}\nunsat: {uvc['unsat']}\nunknown: {sum(v for k,v in uvc.items() if k not in ('success','unsat'))}\n480 macOS 11 reruns",'#e3ebff')
    node(.83,.20,.28,.22,f"pip independent audit\nsuccess: {pipc['success']}\nunsat: {pipc['unsat']}\nunknown: {sum(v for k,v in pipc.items() if k not in ('success','unsat'))}\n288 preregistered dual checks",'#e2f2e6')
    for x in (.17,.50,.83):arrow(.5,.395,x,.325)
    ax.set_title('Public advisory sampling and complete experimental flow\nUnknown results retained in all 1,440 target IDs',fontsize=13,pad=16)
    fig.savefig(FIG/'study_flow.png',dpi=170)
    plt.close(fig)


def main():
    rows=json.loads((ROOT/'all_1440_cases.json').read_text())
    metadata=json.loads((ROOT/'metadata_index.json').read_text())
    release_dates=Counter()
    for item in metadata:
        timestamps=sorted(f['upload_time_iso_8601'] for f in item.get('files',[])
                          if f.get('upload_time_iso_8601'))
        release_dates[timestamps[0][:4] if timestamps else 'missing']+=1
    uv_original=read_jsonl(ROOT/'uv_full.jsonl')
    uv_macfix=read_jsonl(ROOT/'uv_macos11.jsonl')
    uv=dict(uv_original)
    uv.update(uv_macfix)
    uv_corrections=[k for k,rec in uv_macfix.items()
                    if k in uv_original and rec['status']!=uv_original[k]['status']]
    pip=read_jsonl(ROOT/'pip_validation.jsonl')
    allpip=read_jsonl(ROOT/'pip_all.jsonl')
    for r in rows:
        r['uv_status']=uv.get(r['case_id'],{}).get('status','not_run')
        r['uv_seconds']=uv.get(r['case_id'],{}).get('seconds')
        allpip_result=allpip.get(r['case_id'],{})
        r['pip_strict_status']=allpip_result.get('full',{}).get('status','not_run')
        r['pip_strict_inferred']=bool(allpip_result.get('full_inferred_from_no_deps',False))
    assert len(rows)==1440
    outcome=Counter(x['uv_status'] for x in rows)
    strict_outcome=Counter(x['pip_strict_status'] for x in rows)
    known=[x for x in rows if x['uv_status'] in ('success','unsat')]
    eligible=[x for x in known if x['metadata_status']=='ok']
    failing_gate=[x for x in known if x['b2_root_gate'] is False]
    false_block=[x['case_id'] for x in failing_gate if x['uv_status']=='success']
    rootpass=[x for x in eligible if x['b2_root_gate'] is True]
    root_fail_full=[x for x in rootpass if x['uv_status']=='unsat']
    root_fail_full_strict=[x for x in rows if x['b2_root_gate'] is True
                           and x['pip_strict_status']=='unsat']
    transitive_culprits=Counter()
    for x in root_fail_full:
        s=uv[x['case_id']].get('stderr_excerpt','')
        for name in set(re.findall(r'Wheels are required for [`\']([^`\']+)[`\']',s)):
            transitive_culprits[name]+=1
    percell=[]
    strict_percell=[]
    for plat in ['linux_amd64','windows_amd64','macos_arm64']:
        for py in ['3.8','3.10','3.12','3.14']:
            subset=[x for x in eligible if x['python']==py and x['platform']==plat]
            successes=sum(x['uv_status']=='success' for x in subset)
            percell.append({'python':py,'platform':plat,'success':successes,
                            'decisive':len(subset),'rate':ratio(successes,len(subset))})
            strict_subset=[x for x in rows if x['python']==py and x['platform']==plat
                           and x['metadata_status']=='ok'
                           and x['pip_strict_status'] in ('success','unsat')]
            strict_success=sum(x['pip_strict_status']=='success' for x in strict_subset)
            strict_percell.append({'python':py,'platform':plat,'success':strict_success,
                                   'decisive':len(strict_subset),
                                   'rate':ratio(strict_success,len(strict_subset))})
    perstratum=[]
    strict_perstratum=[]
    for stratum in ['early','middle','recent']:
        subset=[x for x in eligible if x['stratum']==stratum]
        perstratum.append({'stratum':stratum,'success':sum(x['uv_status']=='success' for x in subset),
                           'decisive':len(subset),'rate':ratio(sum(x['uv_status']=='success' for x in subset),len(subset))})
        strictsubset=[x for x in rows if x['stratum']==stratum and x['metadata_status']=='ok'
                      and x['pip_strict_status'] in ('success','unsat')]
        strict_perstratum.append({'stratum':stratum,
                                  'success':sum(x['pip_strict_status']=='success' for x in strictsubset),
                                  'decisive':len(strictsubset),
                                  'rate':ratio(sum(x['pip_strict_status']=='success' for x in strictsubset),len(strictsubset))})
    perpattern=Counter();recover=0;recover_den=0;reverse=0;recover_byplat=Counter()
    earliest_working_python=Counter()
    first_migration_from_py38=Counter()
    for project in sorted(set(x['project'] for x in rows)):
        for plat in ['linux_amd64','windows_amd64','macos_arm64']:
            # Do not cast dotted Python versions to floats: 3.10 is newer
            # than 3.8 even though float('3.10') < float('3.8').
            four=sorted([x for x in rows if x['project']==project and x['platform']==plat],
                        key=python_version_key)
            chars={"success":'1',"unsat":'0',"unknown_error":'?',"timeout":'?',"not_run":'?'}
            pattern=''.join(chars.get(x['uv_status'],'?') for x in four)
            if 'metadata_http' in four[0]['root_reason']:pattern='????'
            perpattern[pattern]+=1
            if '?' not in pattern:
                first_success=next((['3.8','3.10','3.12','3.14'][i]
                                    for i,ch in enumerate(pattern) if ch=='1'),'never')
                earliest_working_python[first_success]+=1
                if pattern[0]=='0':
                    next_fix=next((['3.8','3.10','3.12','3.14'][i]
                                   for i,ch in enumerate(pattern[1:],start=1) if ch=='1'),'none')
                    first_migration_from_py38[next_fix]+=1
            if pattern[0]=='0':
                recover_den+=1
                if pattern[-1]=='1':
                    recover+=1;recover_byplat[plat]+=1
            if pattern[0]=='1' and pattern[-1]=='0':reverse+=1
    disagree=0;cross_decisive=0
    for project in sorted(set(x['project'] for x in rows)):
        for py in ['3.8','3.10','3.12','3.14']:
            triple=[x for x in eligible if x['project']==project and x['python']==py]
            if len(triple)==3:
                cross_decisive+=1
                disagree+=len(set(x['uv_status'] for x in triple))>1
    strict_patterns=Counter()
    strict_recover=0;strict_recover_den=0;strict_reverse=0
    strict_first_upgrade=Counter()
    for project in sorted(set(x['project'] for x in rows)):
        for plat in ['linux_amd64','windows_amd64','macos_arm64']:
            four=sorted([x for x in rows if x['project']==project and x['platform']==plat],
                        key=python_version_key)
            if four[0]['metadata_status']!='ok':
                strict_patterns['????']+=1
                continue
            p=''.join({'success':'1','unsat':'0'}.get(x['pip_strict_status'],'?') for x in four)
            strict_patterns[p]+=1
            if p[0]=='0':
                strict_recover_den+=1
                if p[-1]=='1':strict_recover+=1
                if '?' not in p:
                    next_py=next((['3.8','3.10','3.12','3.14'][i] for i,c in enumerate(p)
                                    if i and c=='1'),'none')
                    strict_first_upgrade[next_py]+=1
            if p[0]=='1' and p[-1]=='0':strict_reverse+=1
    full_time=sum(x['uv_seconds'] or 0 for x in rows)
    success_closure_sizes=[uv[x['case_id']].get('resolved_packages',0) for x in rows
                           if x['uv_status']=='success']
    avoided_time=sum(x['uv_seconds'] or 0 for x in rows if x['b2_root_gate'] is False)
    complete_preflight=sum(x['b2_root_gate'] is False for x in rows)
    reltime=ratio(avoided_time,full_time)

    # Exact per-scenario independent pip checks (not inferred from the uv output).
    gold=[]
    uv_pip_conflicts=[]
    for r in rows:
        ev=pip.get(r['case_id'])
        r['pip_root_status']=(ev or {}).get('no_deps',{}).get('status')
        if ev is None:continue
        item={**r,'pip_full_status':ev.get('full',{}).get('status'),
              'pip_root_status':ev.get('no_deps',{}).get('status')}
        gold.append(item)
        if (item['pip_full_status'] in ('success','unsat') and
            r['uv_status'] in ('success','unsat') and
            item['pip_full_status']!=r['uv_status']):
            uv_pip_conflicts.append(r['case_id'])
    base_comp={}
    for b in ['b0_requires_python','b1_tags','b2_root_gate']:
        subset=[x for x in gold if x['metadata_status']=='ok' and
                x[b] is not None and x['pip_root_status'] in ('success','unsat')]
        errors=[x for x in subset if x[b]!=(x['pip_root_status']=='success')]
        false_safe=[x for x in subset if x[b] and x['pip_root_status']=='unsat']
        false_blocked=[x for x in subset if x[b] is False and x['pip_root_status']=='success']
        base_comp[b]={'tested':len(subset),'correct':len(subset)-len(errors),
                      'accuracy':ratio(len(subset)-len(errors),len(subset)),
                      'false_safe':len(false_safe),'false_blocked':len(false_blocked),
                      'false_blocked_cases':[x['case_id'] for x in false_blocked]}
    mcnemar={}
    for name in ('b0_requires_python','b1_tags'):
        paired=[x for x in gold if x['metadata_status']=='ok'
                and x['pip_root_status'] in ('success','unsat')
                and x['b2_root_gate'] is not None and x[name] is not None]
        b2_only=0
        comparator_only=0
        for x in paired:
            truth=x['pip_root_status']=='success'
            correct_b2=x['b2_root_gate']==truth
            correct_base=x[name]==truth
            b2_only+=bool(correct_b2 and not correct_base)
            comparator_only+=bool(correct_base and not correct_b2)
        discord=b2_only+comparator_only
        mcnemar[f'b2_vs_{name}']={
            'paired_cases':len(paired),'b2_correct_only':b2_only,
            'comparator_correct_only':comparator_only,
            'discordant_pairs':discord,
            'two_sided_exact_p':(binomtest(b2_only,discord,0.5).pvalue if discord else 1.0),
        }
    prior=0.0
    for i,(key,value) in enumerate(sorted(mcnemar.items(),key=lambda x:x[1]['two_sided_exact_p'])):
        prior=max(prior,min(1.0,(len(mcnemar)-i)*value['two_sided_exact_p']))
        mcnemar[key]['holm_adjusted_p']=prior
    pip_full=Counter(x['pip_full_status'] for x in gold)
    pip_root=Counter(x['pip_root_status'] for x in gold)
    allpip_cross=Counter((x['uv_status'],x['pip_strict_status']) for x in rows)
    allpip_conflict_ids=[x['case_id'] for x in rows
                         if x['uv_status'] in ('success','unsat')
                         and x['pip_strict_status'] in ('success','unsat')
                         and x['uv_status']!=x['pip_strict_status']]
    two_solver_consensus={
        'both_success':sum(x['uv_status']=='success' and x['pip_strict_status']=='success' for x in rows),
        'both_unsat':sum(x['uv_status']=='unsat' and x['pip_strict_status']=='unsat' for x in rows),
        'uv_success_pip_unsat':sum(x['uv_status']=='success' and x['pip_strict_status']=='unsat' for x in rows),
        'uv_unsat_pip_success':sum(x['uv_status']=='unsat' and x['pip_strict_status']=='success' for x in rows),
        'either_unknown':sum(x['uv_status'] not in ('success','unsat') or
                             x['pip_strict_status'] not in ('success','unsat') for x in rows),
    }
    native_anchor=[x for x in rows if x['python']=='3.12' and x['platform']=='linux_amd64']
    native_anchor_summary={
        'cases':len(native_anchor),
        'uv_success':sum(x['uv_status']=='success' for x in native_anchor),
        'strict_pip_success':sum(x['pip_strict_status']=='success' for x in native_anchor),
        'both_success':sum(x['uv_status']=='success' and x['pip_strict_status']=='success' for x in native_anchor),
        'both_unsat':sum(x['uv_status']=='unsat' and x['pip_strict_status']=='unsat' for x in native_anchor),
        'disagreement':sum(x['uv_status'] in ('success','unsat') and x['pip_strict_status'] in ('success','unsat')
                            and x['uv_status']!=x['pip_strict_status'] for x in native_anchor),
    }
    strict_actual_full_calls=sum(not x.get('full_inferred_from_no_deps',False) for x in allpip.values())
    strict_direct_calls=sum(x.get('no_deps') is not None for x in allpip.values())
    strict_total_seconds=sum((x.get('full') or {}).get('seconds',0) or 0 for x in allpip.values())
    strict_total_seconds+=sum((x.get('no_deps') or {}).get('seconds',0) or 0 for x in allpip.values())
    allpip_b2_false_success=[x['case_id'] for x in rows
                             if x['b2_root_gate'] is False and x['pip_strict_status']=='success']
    allpip_direct_false_positive=[x['case_id'] for x in rows
                                  if x['b2_root_gate'] is False
                                  and (allpip.get(x['case_id'],{}).get('no_deps') or {}).get('status')=='success']
    def baseline_accuracy(group,field):
        val=[r for r in group if r.get('pip_root_status') in ('success','unsat')
             and r[field] is not None]
        return ratio(sum(r[field]==(r['pip_root_status']=='success') for r in val),len(val))
    def paired_difference(group,model):
        val=[r for r in group if r.get('pip_root_status') in ('success','unsat')
             and r['b2_root_gate'] is not None and r[model] is not None]
        if not val:return None
        return sum((r['b2_root_gate']==(r['pip_root_status']=='success'))-
                   (r[model]==(r['pip_root_status']=='success')) for r in val)/len(val)
    baseline_ci={
        f'{name}_accuracy':metric_ci(rows,lambda g,k=name:baseline_accuracy(g,k))
        for name in ['b0_requires_python','b1_tags','b2_root_gate']
    }
    baseline_ci['b2_minus_b0_accuracy']=metric_ci(rows,lambda g:paired_difference(g,'b0_requires_python'))
    baseline_ci['b2_minus_b1_accuracy']=metric_ci(rows,lambda g:paired_difference(g,'b1_tags'))
    pipeline_ci={
        'closure_success':metric_ci(rows,lambda grp:ratio(sum(x['uv_status']=='success' for x in grp if x['metadata_status']=='ok' and x['uv_status'] in ('success','unsat')),
                                                   sum(x['metadata_status']=='ok' and x['uv_status'] in ('success','unsat') for x in grp))),
        'prune_fraction':metric_ci(rows,lambda grp:ratio(sum(x['b2_root_gate'] is False for x in grp),len(grp))),
        'root_to_full_failure':metric_ci(rows,lambda grp:ratio(sum(x['b2_root_gate'] is True and x['uv_status']=='unsat' for x in grp),
                                                           sum(x['b2_root_gate'] is True and x['uv_status'] in ('success','unsat') for x in grp))),
        'python314_minus_python38_success_rate':metric_ci(rows,lambda grp:
            (ratio(sum(x['uv_status']=='success' for x in grp if x['python']=='3.14' and x['metadata_status']=='ok' and x['uv_status'] in ('success','unsat')),
                   sum(x['python']=='3.14' and x['metadata_status']=='ok' and x['uv_status'] in ('success','unsat') for x in grp)) or 0)-
            (ratio(sum(x['uv_status']=='success' for x in grp if x['python']=='3.8' and x['metadata_status']=='ok' and x['uv_status'] in ('success','unsat')),
                   sum(x['python']=='3.8' and x['metadata_status']=='ok' and x['uv_status'] in ('success','unsat') for x in grp)) or 0)),
        'strict_pip_success_rate':metric_ci(rows,lambda grp:ratio(
            sum(x['pip_strict_status']=='success' for x in grp if x['metadata_status']=='ok'
                and x['pip_strict_status'] in ('success','unsat')),
            sum(x['metadata_status']=='ok' and x['pip_strict_status'] in ('success','unsat') for x in grp))),
        'uv_vs_strict_pip_disagreement_rate':metric_ci(rows,lambda grp:ratio(
            sum(x['uv_status']!=x['pip_strict_status'] for x in grp
                if x['uv_status'] in ('success','unsat') and x['pip_strict_status'] in ('success','unsat')),
            sum(x['uv_status'] in ('success','unsat') and
                x['pip_strict_status'] in ('success','unsat') for x in grp))),
    }
    analysis={
        'source_date':'2026-11-14','planned_scenarios':1440,'performed_uv':len(uv),
        'uncorrected_uv_first_pass_scenarios':len(uv_original),
        'macos11_corrective_rerun_scenarios':len(uv_macfix),
        'macos13_default_to_macos11_changed_outcomes':len(uv_corrections),
        'macos_version_correction_changed_ids':uv_corrections,
        'performed_pip':len(pip),'performed_pip_all':len(allpip),
        'uv_status_counts':dict(outcome),'strict_pip_status_counts':dict(strict_outcome),
        'uv_vs_strict_pip_all_contingency':{f'{a}|{b}':n for (a,b),n in allpip_cross.items()},
        'uv_vs_strict_pip_all_disagreement_ids':allpip_conflict_ids,
        'two_solver_consensus':two_solver_consensus,
        'linux_python312_nearest_host_anchor':native_anchor_summary,
        'strict_pip_full_inferred_from_independent_root_rejection':sum(x['pip_strict_inferred'] for x in rows),
        'strict_pip_actual_full_solver_calls':strict_actual_full_calls,
        'strict_pip_actual_no_deps_calls':strict_direct_calls,
        'strict_pip_total_observed_subprocess_seconds':round(strict_total_seconds,2),
        'strict_pip_false_blocks_by_root_gate':len(allpip_b2_false_success),
        'strict_pip_false_blocks_cases':allpip_b2_false_success,
        'strict_pip_root_gate_false_rejects_pip_nodeps':len(allpip_direct_false_positive),
        'strict_pip_root_gate_false_rejects_cases':allpip_direct_false_positive,
        'primary_eligible_decisive':len(eligible),'primary_eligible_success':sum(x['uv_status']=='success' for x in eligible),
        'preflight_pass':sum(x['b2_root_gate'] is True for x in rows),
        'preflight_impossible':complete_preflight,
        'preflight_unknown':sum(x['b2_root_gate'] is None for x in rows),
        'false_blocked_vs_uv':len(false_block),'false_blocked_cases':false_block,
        'full_resolution_fail_given_root_pass':len(root_fail_full),
        'full_resolution_fail_given_root_pass_cases':[x['case_id'] for x in root_fail_full][:20],
        'strict_pip_resolution_fail_given_root_pass':len(root_fail_full_strict),
        'strict_pip_resolution_fail_given_root_pass_cases':[x['case_id'] for x in root_fail_full_strict][:20],
        'top_transitive_no_wheel_dependencies':dict(transitive_culprits.most_common(20)),
        'per_cell':percell,'per_cell_strict_pip':strict_percell,
        'per_stratum':perstratum,'per_stratum_strict_pip':strict_perstratum,
        'outcome_patterns':dict(perpattern.most_common()),
        'strict_pip_outcome_patterns':dict(strict_patterns.most_common()),
        'strict_pip_python38_fail_to_python314_success':strict_recover,
        'strict_pip_python38_fail_count':strict_recover_den,
        'strict_pip_reverse_python38_success_to_python314_fail':strict_reverse,
        'strict_pip_first_successful_migration':dict(strict_first_upgrade),
        'fixed_release_first_upload_year':dict(sorted(release_dates.items())),
        'earliest_working_python_by_project_platform':dict(earliest_working_python),
        'first_successful_migration_from_python38':dict(first_migration_from_py38),
        'old_python_fail_new_python_success_project_platforms':recover,
        'old_python_fail_count_project_platforms':recover_den,
        'reverse_cliff_old_success_new_fail':reverse,
        'old_to_new_recovery_by_platform':dict(recover_byplat),
        'cross_platform_disagreements':disagree,'cross_platform_decisive_project_python':cross_decisive,
        'solver_calls_saved_by_preflight':complete_preflight,
        'solver_calls_reduction_fraction':ratio(complete_preflight,1440),
        'solver_total_subprocess_seconds':round(full_time,2),
        'uv_success_resolved_package_count_median':median(success_closure_sizes) if success_closure_sizes else None,
        'uv_success_resolved_package_count_max':max(success_closure_sizes) if success_closure_sizes else None,
        'estimated_avoided_subprocess_seconds':round(avoided_time,2),
        'estimated_subprocess_time_reduction_fraction':reltime,
        'pip_full':dict(pip_full),'pip_root':dict(pip_root),
        'pip_full_vs_uv_disagreement':len(uv_pip_conflicts),
        'pip_full_vs_uv_disagreement_ids':uv_pip_conflicts,
        'pip_root_baseline_comparison':base_comp,
        'pip_root_exact_paired_mcnemar':mcnemar,
        'pip_root_baseline_project_bootstrap':baseline_ci,
        'project_cluster_bootstrap':pipeline_ci,
        'preregistered_thresholds':{
            'uv_decisive_at_least_90pct':ratio(len(known),1440)>=.90,
            'pip_full_decisive_at_least_95pct':len(gold)==288 and ratio(pip_full['success']+pip_full['unsat'],len(gold))>=.95,
            'root_gate_false_blocks_zero':not false_block,
            'at_least_10pct_solver_call_reduction':ratio(complete_preflight,1440)>=.10,
        },
        'warnings':['Wheel-only; cannot imply security-safe alternate/backport is absent.',
                    'pip cross-target environment markers may use host interpreter/platform; uv pip compile is primary full resolver.',
                    'Result is distribution-only, NOT deployment/build/tests/functional compatibility.',
                    'Stratified by advisory year; not a prevalence-weighted PyPI random sample.']
    }
    (ROOT/'analysis_results.json').write_text(json.dumps(analysis,indent=2,ensure_ascii=False))
    make_figures(rows)
    table=['# Full I01 measured tables\n', '## Strict pip wheel-only dry run: target × platform\n',
           '|Platform|Python|Resolvable|Decisive|Rate|','|---|---|---:|---:|---:|']
    for x in strict_percell:table.append(f"|{x['platform']}|{x['python']}|{x['success']}|{x['decisive']}|{x['rate']:.1%}|")
    table+=['\n## `uv` (documented relaxed upper-bound) full resolver: target × platform\n',
           '|Platform|Python|Resolvable|Decisive|Rate|','|---|---|---:|---:|---:|']
    for x in percell:table.append(f"|{x['platform']}|{x['python']}|{x['success']}|{x['decisive']}|{x['rate']:.1%}|")
    table+=['\n## OSV advisory-year strata (`uv` policy)\n','|Stratum|Success|Decisive|Rate|','|---|---:|---:|---:|']
    for x in perstratum:table.append(f"|{x['stratum']}|{x['success']}|{x['decisive']}|{x['rate']:.1%}|")
    table+=['\n## OSV advisory-year strata (strict pip policy)\n','|Stratum|Success|Decisive|Rate|','|---|---:|---:|---:|']
    for x in strict_perstratum:table.append(f"|{x['stratum']}|{x['success']}|{x['decisive']}|{x['rate']:.1%}|")
    table+=['\n## Baselines on independent `pip --no-deps`\n',
             '|Model|Correct|Tested|Accuracy|False-safe|False-blocked|',
             '|---|---:|---:|---:|---:|---:|']
    for b,x in base_comp.items():
        acc='N/A' if x['accuracy'] is None else f"{x['accuracy']:.1%}"
        table.append(f"|{b}|{x['correct']}|{x['tested']}|{acc}|{x['false_safe']}|{x['false_blocked']}|")
    table+=['\n## Exact paired McNemar tests against B2 (preregistered pip root holdout)\n',
            '|Comparison|Pairs|B2-only correct|Baseline-only correct|Exact two-sided p|Holm-adjusted p|',
            '|---|---:|---:|---:|---:|---:|']
    for k,x in mcnemar.items():
        table.append(f"|{k}|{x['paired_cases']}|{x['b2_correct_only']}|{x['comparator_correct_only']}|{x['two_sided_exact_p']:.5g}|{x['holm_adjusted_p']:.5g}|")
    (ROOT/'TABLES.md').write_text('\n'.join(table)+'\n')
    print(json.dumps({k:analysis[k] for k in ['performed_uv','performed_pip','uv_status_counts','primary_eligible_success',
          'false_blocked_vs_uv','full_resolution_fail_given_root_pass','solver_calls_reduction_fraction','estimated_subprocess_time_reduction_fraction',
          'pip_full_vs_uv_disagreement','preregistered_thresholds']},indent=2))


if __name__=='__main__':main()
