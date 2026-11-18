"""Flag public label/source contradictions without silently rewriting labels."""

import argparse
from collections import Counter
import json
from pathlib import Path


def audit(data: dict) -> dict:
    conflicts=[]
    for case in data["cases"]:
        if case["idoft_status"] != "Deleted":
            continue
        same=[x for x in case["candidates"] if
              x["body_equal"] and x["target"].split(".")[-1] == case["old_id"].split(".")[-1]
              and x["file_rename"]]
        if same:
            conflicts.append({"event":case["event_id"],
                              "detected_sha":case["idoft_detected_sha"],
                              "old_id":case["old_id"],
                              "target_identical_method":same[0]["target"],
                              "original_status":case["idoft_status"],
                              "conflict_type":"IDoFT Deleted vs same-name equal-body moved Java test"})
    return {"source":"https://github.com/TestingResearchIllinois/idoft",
            "policy":"IDoFT FAQ says unchanged test-method bodies with moved IDs should be marked MovedOrRenamed; these cases warrant manual source/fixture review",
            "not_an_automatic_correction":True,
            "n_cases":len(data["cases"]),
            "n_deleted":sum(x["idoft_status"]=="Deleted" for x in data["cases"]),
            "conflict_count":len(conflicts), "conflicts":conflicts}


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--input",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    args=a.parse_args()
    output=audit(json.loads(args.input.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,indent=2),encoding="utf-8")
    print("Deleted",output["n_deleted"],"conflicts",output["conflict_count"])


if __name__=="__main__":
    main()
