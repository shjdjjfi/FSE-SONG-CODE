#!/usr/bin/env python3
"""Mechanistic synthetic validation, NOT industrial expert-ground-truth data."""

import itertools
import json
import random
from pathlib import Path

from run_measurement import sharp_delta_bounds,sharp_coverage_bounds

OUT=Path(__file__).resolve().parent/'results'
SEEDS=(17,29,43)
N_PER_SEED=1500


def brute(U,A,B,m):
    obs=[sum(int(x in B)-int(x in A) for x in E)/m for E in itertools.combinations(U,m)]
    coverage=[sum(int(x in B) for x in E)/m for E in itertools.combinations(U,m)]
    return [min(obs),max(obs)],[min(coverage),max(coverage)]


def main():
    tested=0;witnesses=[]
    for seed in SEEDS:
        rng=random.Random(seed)
        for _ in range(N_PER_SEED):
            n=rng.randint(3,9)
            universe=[f'person{i}' for i in range(n)]
            A=set(rng.sample(universe,min(2,n)))
            B=set(rng.sample(universe,min(2,n)))
            m=rng.randint(1,min(4,n))
            expect,expected_cov=brute(universe,A,B,m)
            received=sharp_delta_bounds(universe,A,B,m)
            received_cov=sharp_coverage_bounds(universe,B,m)
            assert all(abs(x-y)<1e-12 for x,y in zip(expect,received)),(seed,expect,received)
            assert all(abs(x-y)<1e-12 for x,y in zip(expected_cov,received_cov))
            tested+=1
            if m==1 and expect==[-1.,1.] and len(witnesses)<12:
                left=next(u for u in universe if u in A-B)
                right=next(u for u in universe if u in B-A)
                witnesses.append({'public_recommendation_A':sorted(A),'public_recommendation_B':sorted(B),
                                  'public_candidate_universe':universe,
                                  'private_expertise_world_A':[left],
                                  'private_expertise_world_B':[right],
                                  'same_public_observations':True,
                                  'delta_A':-1.,'delta_B':1.})
    path=OUT/'synthetic_bounds_validation.json'
    path.write_text(json.dumps({'n_bruteforce_cases':tested,'seeds':list(SEEDS),
             'cases_per_seed':N_PER_SEED,'formula_vs_enumeration_disagreements':0,
             'world_witnesses_synthetic_only':witnesses,
             'claim_limit':'Synthetic tests validate closed-form sharp bounds, not actual company skills, membership or causal ROI'},
             indent=2)+'\n',encoding='utf-8')
    print('BRUTE_FORCE_BOUND_TESTS',tested,'FAILURES',0,'WITNESSES',len(witnesses))


if __name__=='__main__':main()
