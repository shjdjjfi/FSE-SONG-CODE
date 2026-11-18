"""Source-derived numbered-method-to-JUnit-parameter mapping for a real change.

This narrow, inspectable matcher never reads the IDoFT labels to construct its
mapping. It requires one identical helper invocation in old and new test
methods plus an explicit finite JUnit parameter range. Unsupported code
abstains. Validated only on a single Java-WebSocket commit, not general Java.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import re
from pathlib import Path


TEST_RE = re.compile(
    r"@Test(?:\([^\n]*\))?\s*public\s+void\s+(\w+)\s*\(\s*\)\s*"
    r"(?:throws\s+[^\{\n]+)?\{\s*([^\{\}]*?)\s*\}",re.DOTALL)
INVOCATION_RE = re.compile(r"^([A-Za-z_]\w*)\s*\(\s*([^;]*?)\s*\)\s*;$")


def extract(source: str) -> tuple[dict[str, str], int | None]:
    methods={}
    for m in TEST_RE.finditer(source):
        call=re.sub(r"\s+","",m.group(2))
        if INVOCATION_RE.fullmatch(call):
            methods[m.group(1)]=call
    is_parameterized="@RunWith(Parameterized.class)" in source
    number=re.search(r"NUMBER_OF_TESTS\s*=\s*(\d+)\s*;",source)
    count=int(number.group(1)) if number and is_parameterized and "@Parameterized.Parameters" in source else None
    return methods,count


def infer(old_file:Path,new_file:Path) -> tuple[dict[str,str],dict]:
    old,n_old=extract(old_file.read_text(encoding="utf-8"))
    new,n_new=extract(new_file.read_text(encoding="utf-8"))
    assert n_old is None and n_new is not None
    lookup=collections.defaultdict(list)
    for name,body in new.items():
        lookup[body].append(name)
    mapping={}
    rejections=[]
    for name,body in old.items():
        m=re.fullmatch(r"(.+?)(\d+)",name)
        if m is None:
            rejections.append({"old_name":name,"reason":"not_numbered"})
            continue
        index=int(m.group(2))
        candidates=lookup.get(body,[])
        if index>=n_new or len(candidates)!=1:
            rejections.append({"old_name":name,"reason":"out_of_range_or_ambiguous_new_method"})
            continue
        mapping[name]=f"{candidates[0]}[{index}]"
    return mapping,{"old_runnable_methods":len(old),"new_runnable_methods":len(new),
                    "generated_junit_parameter_values":n_new,
                    "mapped":len(mapping),"rejections":rejections}


def run(before:Path, after:Path, idoft:Path, out:Path):
    out.mkdir(parents=True,exist_ok=True)
    mappings={}
    audit={}
    for klass in ("Issue256Test","Issue580Test"):
        rel=Path("src/test/java/org/java_websocket/issues")/(klass+".java")
        mappings[klass],audit[klass]=infer(before/rel,after/rel)
    with idoft.open(newline="",encoding="utf-8") as f:
        records=list(csv.DictReader(f))
    selected=[r for r in records if r.get("Status")=="MovedOrRenamed" and "TooTallNate/Java-WebSocket" in r.get("Project URL","")]
    table=[]
    for row in selected:
        fq=row["Fully-Qualified Test Name (packageName.ClassName.methodName)"]
        old_class,old_method=fq.rsplit(".",1)
        klass=old_class.split(".")[-1]
        inferred=mappings[klass].get(old_method)
        table.append({"old_fq_test":fq,
                      "new_fq_test":old_class+"."+inferred if inferred is not None else "",
                      "matched_from_source_without_labels":bool(inferred),
                      "idoft_status":row["Status"],"source_commit":row["SHA Detected"]})
    with (out/"java_source_derived_lineage.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]))
        w.writeheader();w.writerows(table)
    output={"source_parent":"27e26758d6604f5d078709233028bb87b4a39e16",
            "source_after":"2ce6e6149d0ef44f4919e75326265c64c144a00f",
            "source_rule":"identical helper call with args + unique parameterized method + bounded numerical suffix",
            "audits":audit,"independent_idoft_moved_records":len(selected),
            "matching_independent_idoft_records":sum(x["matched_from_source_without_labels"] for x in table),
            "limitation":"Only one repository/one refactoring commit; not independently tested on other Java parameterizations."}
    (out/"java_param_lineage_results.json").write_text(json.dumps(output,indent=2),encoding="utf-8")
    print(json.dumps(output,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--before",type=Path,default=Path("data/javawebsocket_pre"))
    p.add_argument("--after",type=Path,default=Path("data/javawebsocket_post"))
    p.add_argument("--idoft",type=Path,default=Path("data/raw/idoft_maven.csv"))
    p.add_argument("--out",type=Path,default=Path("results/java_lineage"))
    a=p.parse_args();run(a.before,a.after,a.idoft,a.out)
