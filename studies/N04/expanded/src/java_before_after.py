"""Join 30 genuinely executed before/after JUnit runs by source-derived identity.

Both checkouts are genuine Git revisions; the same Java 21 / Maven / host is
used for Surefire, after Java 8 recompilation of old Java-6-era sources.
Failures are observed, not synthesized. This is a ONE-COMMIT case study;
it does not prove a general industrial deployment gain or causal repair.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import random
from pathlib import Path

from java_param_lineage import infer


def load(path:Path):
    out=collections.defaultdict(list)
    with path.open(newline="",encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[(row["class"],row["test"])].append((int(row["iteration"]),row["status"]))
    return {k:[v for _,v in sorted(values)] for k,values in out.items()}


def tally(states:list[str])->dict:
    c=collections.Counter(states)
    failures=len(states)-c["passed"]-c["skipped"]
    return {"runs":len(states),"passed":c["passed"],"failed":c["failed"],
            "errors":c["error"],"skipped":c["skipped"],
            "nonpass":failures,"flaky":0<failures<len(states)}


def main(pre:Path,post:Path,before:Path,after:Path,out:Path):
    pre_runs=load(pre)
    post_runs=load(post)
    report=[]
    for klass in ("Issue256Test","Issue580Test"):
        rel=Path("src/test/java/org/java_websocket/issues")/(klass+".java")
        mapping,_=infer(before/rel,after/rel)
        for old,new in sorted(mapping.items()):
            a=pre_runs.get((klass,old),[])
            b=post_runs.get((klass,new),[])
            ta,tb=tally(a),tally(b)
            report.append({"class":klass,"old_test":old,"new_test":new,
                           **{"pre_"+k:v for k,v in ta.items()},
                           **{"post_"+k:v for k,v in tb.items()}})
    out.mkdir(parents=True,exist_ok=True)
    with (out/"before_after_40_cases.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(report[0]))
        w.writeheader();w.writerows(report)

    all_complete=all(x["pre_runs"]==30 and x["post_runs"]==30 for x in report)
    replay=[]
    for seed in (17,29,43):
        for r in report:
            klass=r["class"]
            old=pre_runs[(klass,r["old_test"])]
            new=post_runs[(klass,r["new_test"])]
            pr=list(old);po=list(new)
            random.Random(seed*7919+sum(ord(c) for c in r["old_test"])).shuffle(pr)
            random.Random(seed*107+sum(ord(c) for c in r["new_test"])).shuffle(po)
            pre20=pr[:20]
            future10=po[20:]
            past_flaky="passed" in pre20 and any(x in ("failed","error") for x in pre20)
            future_flaky="passed" in future10 and any(x in ("failed","error") for x in future10)
            replay.append({"seed":seed,"class":klass,"old_test":r["old_test"],
                           "new_test":r["new_test"],"pre20_quarantine":past_flaky,
                           "future10_observed_flaky":future_flaky,
                           "missed_flaky_preserved":future_flaky and not past_flaky,
                           "missed_flaky_reset":future_flaky,
                           "possibly_stale_quarantine":past_flaky and not r["post_flaky"]})
    with (out/"case_replay.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(replay[0]))
        w.writeheader();w.writerows(replay)

    summaries={}
    for klass in ("Issue256Test","Issue580Test","ALL"):
        cases=[r for r in report if klass=="ALL" or r["class"]==klass]
        summaries[klass]={"mapped_cases":len(cases),
                         "all_30_repetitions_complete":all(x["pre_runs"]==30 and x["post_runs"]==30 for x in cases),
                         "pre_total_executions":sum(x["pre_runs"] for x in cases),
                         "post_total_executions":sum(x["post_runs"] for x in cases),
                         "pre_nonpass":sum(x["pre_nonpass"] for x in cases),
                         "post_nonpass":sum(x["post_nonpass"] for x in cases),
                         "pre_flaky_cases":sum(x["pre_flaky"] for x in cases),
                         "post_flaky_cases":sum(x["post_flaky"] for x in cases)}
    replay_summary=[]
    for seed in (17,29,43):
        r=[x for x in replay if x["seed"]==seed]
        replay_summary.append({"seed":seed,
                               "future_flaky_cases":sum(x["future10_observed_flaky"] for x in r),
                               "missed_preserved":sum(x["missed_flaky_preserved"] for x in r),
                               "missed_reset":sum(x["missed_flaky_reset"] for x in r),
                               "stale_quarantine_proxy":sum(x["possibly_stale_quarantine"] for x in r)})
    summary={"old_sha":"27e26758d6604f5d078709233028bb87b4a39e16",
             "new_sha":"2ce6e6149d0ef44f4919e75326265c64c144a00f",
             "runtime":"Java 21 Surefire on same host, old project compiled with JDK8 for Java 6 compatibility",
             "complete_40_case_mapping":all_complete,"summaries":summaries,
             "counterfactual_identity_decisions":replay_summary,
             "limitation":"One commit, shared services/socket scheduling, non-randomized run order, CI quarantine actions were not actually performed."}
    (out/"before_after_results.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--pre",type=Path,default=Path("results/java_pre_30_complete/junit_cases.csv"))
    p.add_argument("--post",type=Path,default=Path("results/java_post_30_complete/junit_cases.csv"))
    p.add_argument("--before",type=Path,default=Path("data/javawebsocket_pre"))
    p.add_argument("--after",type=Path,default=Path("data/javawebsocket_post"))
    p.add_argument("--out",type=Path,default=Path("results/java_before_after"))
    a=p.parse_args()
    main(a.pre,a.post,a.before,a.after,a.out)
