#!/usr/bin/env python3
"""Reproducible follow-up scientific figures; strictly label proxy and scenarios."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results'/'figures'
OUT.mkdir(parents=True,exist_ok=True)

def read(name):return json.loads((ROOT/'results'/name).read_text())

def main():
    base=read('metrics.json')
    cv=read('hybrid_strong_baselines_cv.json')
    gate=read('FINAL_SUBMISSION_GATE_AUDIT.json')
    roi=read('shadow_replay_and_roi_bounds.json')
    values=[base['metrics']['recall']['current_path']['event_macro_mean'],
            base['metrics']['recall']['windowed_handoff']['event_macro_mean'],
            cv['prequential_strict_time_replay']['event_macro_recall'],
            cv['leave_one_event_out_retrospective']['event_macro_recall']]
    labs=['Current path','180-day handoff','Time-forward hybrid','Leave-event-out hybrid']
    fig, ax=plt.subplots(figsize=(8.5,4.5))
    colors=['#6b7280','#157f9e','#107c59','#b2683c']
    bars=ax.bar(labs,[100*v for v in values],color=colors,width=.65)
    for b,v in zip(bars,values):
        ax.text(b.get_x()+b.get_width()/2,100*v+1.0,f'{100*v:.1f}%',ha='center',fontsize=11)
    ax.axhline(100*values[0]+10,color='firebrick',linestyle='--',lw=1.5,
               label='Exploratory +10pp numeric threshold (not expert truth)')
    ax.set_ylim(0,50);ax.set_ylabel('Observed reviewer Recall@2 (%)')
    ax.set_title('Post-transfer reviewer retrieval — observational proxy only')
    ax.legend(loc='upper left',fontsize=8)
    ax.tick_params(axis='x',labelrotation=14)
    ax.grid(axis='y',alpha=.18)
    fig.text(.5,.005,'No independent expert ground truth, no roster or causal review-time measurements.',ha='center',fontsize=8,color='#7b3d3d')
    fig.tight_layout(rect=[0,.045,1,1])
    for suffix in ('png','svg'):
        fig.savefig(OUT/f'fig4_followup_observed_reviewer_recall.{suffix}',dpi=190)
    plt.close(fig)

    table=roi['hypothetical_cost_break_even_sensitivity_NOT_MEASURED_ROI']
    minutes=[5,15,30];incidents=[2,8,24]
    data=[[next(x['minimum_avoided_incidents_per_100_prs'] for x in table if x['reviewer_minutes_per_contact']==m and x['avoided_incident_hours']==h)
           for h in incidents] for m in minutes]
    fig,ax=plt.subplots(figsize=(7.0,4.5))
    heat=ax.imshow(data,cmap='Blues',aspect='auto')
    ax.set_xticks(range(3),[f'{x} h' for x in incidents]);ax.set_yticks(range(3),[f'{x} min' for x in minutes])
    ax.set_xlabel('Hypothetical labor avoided per prevented incident')
    ax.set_ylabel('Assumed cost per supplemental invitation')
    for i in range(3):
        for j in range(3):
            ax.text(j,i,f'{data[i][j]:.2f}',ha='center',va='center',color='white' if data[i][j]>7 else 'black',fontsize=12)
    ax.set_title('Break-even incidents required per 100 PRs — SCENARIO ONLY')
    fig.colorbar(heat,ax=ax,label='Minimum avoided incidents per 100 PRs')
    fig.text(.5,.005,'No avoided incident, reviewer cost, or company savings has been measured.',ha='center',fontsize=8,color='#7b3d3d')
    fig.tight_layout(rect=[0,.05,1,1])
    for suffix in ('png','svg'):
        fig.savefig(OUT/f'fig5_hypothetical_roi_breakeven.{suffix}',dpi=190)
    plt.close(fig)
    print('PLOTS 2 figures, 4 files')


if __name__=='__main__':main()
