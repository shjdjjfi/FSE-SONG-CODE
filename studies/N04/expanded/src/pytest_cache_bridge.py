"""Strict, opt-in pytest lastfailed identity-bridge prototype.

This small component only handles syntactically intact test bodies and safe
pytest parameter-ID relabeling. It rejects semantic changes, splits, ambiguous
duplicates and unsupported syntax. It is a research prototype, not a replacement
for CI quarantine systems or a validated Git-to-Git identity tracker.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path


def functions(source: str) -> dict[str, ast.FunctionDef]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    out = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            out[node.name] = node
        if isinstance(node, ast.ClassDef):
            for ch in node.body:
                if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)) and ch.name.startswith("test"):
                    out[node.name + "::" + ch.name] = ch
    return out


def normalized_body(node: ast.FunctionDef) -> str:
    return ast.dump(ast.Module(body=node.body, type_ignores=[]), include_attributes=False)


def param_ids(node: ast.FunctionDef) -> dict[str, str] | None:
    """Map parameter ID to repr(value), for simple statically declared lists.

    False mappings are less desirable than missed mappings, so unsupported
    parametrizations return None and cannot be bridged.
    """
    for dec in node.decorator_list:
        if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute) or dec.func.attr != "parametrize":
            continue
        if len(dec.args) < 2:
            return None
        try:
            arg_names = ast.literal_eval(dec.args[0])
            values = ast.literal_eval(dec.args[1])
            if isinstance(arg_names, str) and "," in arg_names:
                return None
            ids = None
            for kw in dec.keywords:
                if kw.arg == "ids":
                    ids = ast.literal_eval(kw.value)
            if ids is None or len(ids) != len(values):
                return None
            descs = [repr(v) for v in values]
            if len(set(descs)) != len(descs):
                return None
            return dict(zip(ids, descs))
        except (ValueError, TypeError, AttributeError):
            return None
    return {}


def build_mapping(old_source: str, new_source: str) -> tuple[dict[str, str], dict]:
    old = functions(old_source)
    new = functions(new_source)
    audit = {"examined":len(old), "new_tests":len(new), "safe_links":0,
             "changed_semantics":0, "split_ambiguous":0, "unmatched_or_ambiguous":0,
             "param_id_pairs":0}
    mapping = {}
    for name, src in old.items():
        matching_prefixes = [k for k in new if k.startswith(name + "_")]
        if len(matching_prefixes) > 1:
            audit["split_ambiguous"] += 1
            continue
        targets = [k for k, dest in new.items() if normalized_body(src) == normalized_body(dest)]
        if name in new and normalized_body(src) != normalized_body(new[name]):
            audit["changed_semantics"] += 1
            continue
        if len(targets) != 1:
            audit["unmatched_or_ambiguous"] += 1
            continue
        target = targets[0]
        old_ids, new_ids = param_ids(src), param_ids(new[target])
        if old_ids is None or new_ids is None:
            audit["unmatched_or_ambiguous"] += 1
            continue
        if old_ids and new_ids:
            inverted = {v:k for k,v in new_ids.items()}
            if set(old_ids.values()) != set(new_ids.values()):
                audit["unmatched_or_ambiguous"] += 1
                continue
            for old_id, identity in old_ids.items():
                mapping[name + "[" + old_id + "]"] = target + "[" + inverted[identity] + "]"
                audit["param_id_pairs"] += 1
        elif not old_ids and not new_ids:
            mapping[name] = target
        else:
            audit["unmatched_or_ambiguous"] += 1
            continue
        audit["safe_links"] += 1
    # If two distinct old tests would both carry their history into one new
    # identity, drop all mappings to that destination (non-injective merge).
    inverted = {}
    for a,b in mapping.items():
        inverted.setdefault(b, []).append(a)
    for target,sources in inverted.items():
        if len(sources) > 1:
            for src in sources:
                mapping.pop(src)
            audit["unmatched_or_ambiguous"] += len(sources)
            audit["safe_links"] -= len(sources)
    return mapping, audit


def rewrite_cache(root: Path, old_filename: str, new_filename: str,
                  old_source: str, new_source: str) -> dict:
    cache_file = root / ".pytest_cache" / "v" / "cache" / "lastfailed"
    if not cache_file.exists():
        return {"reason":"no_cache", "cache_entries":0, "transferred":0}
    cache = json.loads(cache_file.read_text(encoding="utf-8"))
    mapping,audit = build_mapping(old_source,new_source)
    rewritten = {}
    changed = []
    discarded = []
    for original, value in cache.items():
        if not original.startswith(old_filename + "::"):
            rewritten[original] = value
            continue
        old_test = original.split("::",1)[1]
        new_test = mapping.get(old_test)
        if new_test is not None:
            key = new_filename + "::" + new_test
            rewritten[key] = value
            changed.append({"from":original,"to":key})
        else:
            discarded.append(original)
    cache_file.write_text(json.dumps(rewritten,indent=2),encoding="utf-8")
    return {**audit,"reason":"completed", "cache_entries":len(cache),
            "transferred":len(changed),"discarded":len(discarded),
            "transfer_details":changed,"discarded_entries":discarded}
