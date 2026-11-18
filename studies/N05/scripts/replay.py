#!/usr/bin/env python3
"""Compile exact Rustdoc code snippets as external consumer crates.

Evidence: a snippet is an admissible feature-mismatch witness iff the docs.rs
feature profile compiles, default consumer profile fails, and the failure is
reproduced on the same source without external dependencies injected.

`--stage screen` does not tune any feature search parameters; its results are
only labels. `--stage search` uses fixed budgets and the frozen screen labels.
"""
import argparse
import gzip
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RESULTS = ROOT / "results"
WORK = ROOT / "work"
LOCAL_CARGO = ROOT.parent / "tools" / "cargo-home"
RUSTBIN = Path(os.environ.get("N05_RUST_BIN_DIR") or (
    str(LOCAL_CARGO / "bin") if (LOCAL_CARGO / "bin" / "cargo").exists()
    else str(Path(shutil.which("cargo") or str(Path.home() / ".cargo" / "bin" / "cargo")).parent)
))
CARGO_HOME = Path(os.environ.get("N05_CARGO_HOME") or os.environ.get("CARGO_HOME") or (
    str(LOCAL_CARGO) if LOCAL_CARGO.exists() else str(Path.home() / ".cargo")
))
RUSTUP_HOME = Path(os.environ.get("N05_RUSTUP_HOME") or os.environ.get("RUSTUP_HOME") or (
    str(ROOT.parent / "tools" / "rustup-home") if (ROOT.parent / "tools" / "rustup-home").exists()
    else str(Path.home() / ".rustup")
))
TIMEOUT = 180
MAX_FIX_ATTEMPTS = 8


def read_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def code_for_consumer(snippet, visible=False):
    code = snippet["visible_code"] if visible else snippet["compiled_code"]
    if re.search(r"\bfn\s+main\s*\(", code):
        return code + "\n"
    if code.lstrip().startswith("#!["):
        # Treat crate attributes as crate-level, as rustdoc does.
        return code + "\n\nfn main() {}\n"
    if "?" in code and not re.search(r"\bfn\s+main\s*\(", code):
        return "fn main() -> Result<(), Box<dyn std::error::Error>> {\n" + code + "\nOk(())\n}\n"
    return "fn main() {\n" + code + "\n}\n"


def cargo_manifest(meta, profile, features=()):
    crate = meta["crate"]
    edition = "2021"   # fixed consumer edition, independent from source crate edition
    if profile in ("docs", "docs_cfg"):
        docs = meta["docs_metadata"]
        extra = sorted(set(meta["feature_names"]) - {"default"}) if docs.get("all-features") else docs.get("features", [])
        default_enabled = not docs.get("no-default-features", False)
    else:
        extra = list(features)
        default_enabled = True
    q = ", ".join(json.dumps(f) for f in extra)
    return (f'[package]\nname = "n05_{crate.replace("-", "_")}_consumer"\nversion = "0.1.0"\n'
            f'edition = "{edition}"\n\n[dependencies]\n'
            f'{json.dumps(crate)} = {{ version = "={meta["version"]}", '
            f'default-features = {str(default_enabled).lower()}, features = [{q}] }}\n')


def error_stats(stdout, stderr):
    errs = []
    for l in stdout.splitlines():
        if not l.startswith("{"):
            continue
        try:
            d = json.loads(l)
        except json.JSONDecodeError:
            continue
        if d.get("reason") != "compiler-message":
            continue
        msg = d.get("message", {})
        if msg.get("level") == "error":
            spans = msg.get("spans", [])
            errs.append({"code": (msg.get("code") or {}).get("code"),
                         "message": msg.get("message"),
                         "rendered": (msg.get("rendered") or "")[:1200],
                         "line": spans[0].get("line_start") if spans else None})
    return errs[:50]


def run_check(meta, row, profile, features=(), force=False, visible=False):
    """Returns one persisted immutable-by-key check; no network calls in code."""
    key_data = {"crate": meta["crate"], "version": meta["version"], "id": row["id"],
                "profile": profile, "features": sorted(features), "toolchain": "1.91.0",
                "code_mode": "visible-only-v2" if visible else "hidden-included-v2"}
    key = hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()[:18]
    out_file = RESULTS / "checks" / f"{key}.json"
    if out_file.exists() and not force:
        return json.loads(out_file.read_text())
    proj = WORK / "consumers" / meta["crate"]
    (proj / "src").mkdir(parents=True, exist_ok=True)
    manifest = cargo_manifest(meta, profile, features)
    code = code_for_consumer(row, visible=visible)
    (proj / "Cargo.toml").write_text(manifest)
    (proj / "src" / "main.rs").write_text(code)
    # Resupply frozen transitive versions on clean artifact replays. Never
    # overwrite an existing experiment lockfile with another project's lock.
    saved_lock = DATA / "locks" / f'{meta["crate"]}.lock'
    if saved_lock.exists() and not (proj / "Cargo.lock").exists():
        shutil.copyfile(saved_lock, proj / "Cargo.lock")
    env = os.environ.copy()
    env["CARGO_HOME"] = str(CARGO_HOME)
    env["RUSTUP_HOME"] = str(RUSTUP_HOME)
    cmake_bin = Path(os.environ.get("N05_CMAKE_BIN_DIR") or
                     ROOT.parent / "tools" / "python-local" / "cmake" / "data" / "bin")
    env["PATH"] = str(RUSTBIN) + os.pathsep + str(cmake_bin) + os.pathsep + env.get("PATH", "")
    env["CARGO_TARGET_DIR"] = str(WORK / "target")
    env["CARGO_INCREMENTAL"] = "0"
    env["CARGO_BUILD_JOBS"] = "4"
    env["CARGO_TERM_COLOR"] = "never"
    env["RUST_BACKTRACE"] = "0"
    # libsqlite3-sys can invoke bindgen under SQLx's docs-only SQLite
    # features. Minimal containers may lack Clang's builtin stdarg.h search
    # path even while GCC ships it. Use the recorded host GCC include path.
    if meta["crate"] == "sqlx" and not env.get("BINDGEN_EXTRA_CLANG_ARGS"):
        try:
            inc = subprocess.check_output(["gcc", "-print-file-name=include"], text=True).strip()
            if (Path(inc) / "stdarg.h").is_file():
                env["BINDGEN_EXTRA_CLANG_ARGS"] = "-isystem " + inc
        except (OSError, subprocess.SubprocessError):
            pass
    if profile == "docs_cfg":
        # Only rescue documentation profiles that fail the feature-only build.
        # Applying docsrs itself requires nightly on some crates, so exclude it;
        # classify all such rescues separately from feature-only mismatch.
        d = meta["docs_metadata"]
        raw = d.get("rustc-args", []) + d.get("rustdoc-args", [])
        flags = []
        for j in range(len(raw) - 1):
            if raw[j] == "--cfg" and raw[j + 1] != "docsrs":
                flags.extend(("--cfg", raw[j + 1]))
        if flags:
            env["RUSTFLAGS"] = " ".join(flags)
    command = [str(RUSTBIN / "cargo"), "+1.91.0", "check", "--message-format=json", "--quiet"]
    if os.environ.get("N05_LOCKED") == "1":
        command.append("--locked")
    t0 = time.monotonic()
    try:
        call = subprocess.run(command, cwd=proj, env=env, capture_output=True, text=True,
                              timeout=TIMEOUT, errors="replace")
        stdout, stderr, rc, timed_out = call.stdout, call.stderr, call.returncode, False
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout or "", (exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr or ""
        rc, timed_out = 124, True
    elapsed = time.monotonic() - t0
    errors = error_stats(stdout, stderr)
    infrastructure = timed_out or bool(re.search(
        r"failed to download|failed to fetch|failed to select a version|could not resolve host|"
        r"failed to get|network failure|package .* requires rustc|failed to run custom build command|"
        r"No space left|linker .* failed|signal: 9|does not support rustc", stderr, re.I))
    status = "pass" if rc == 0 else ("infra" if infrastructure else "fail")
    rec = {"key": key, "args": key_data, "status": status, "returncode": rc,
           "seconds": round(elapsed, 4), "errors": errors,
           "error_count": len(errors), "stderr_excerpt": stderr[-2200:],
           "code_sha256": hashlib.sha256(code.encode()).hexdigest(),
           "manifest_sha256": hashlib.sha256(manifest.encode()).hexdigest(),
           "log_file": str((RESULTS / "check_logs" / f"{key}.txt.gz").relative_to(ROOT))}
    (RESULTS / "checks").mkdir(parents=True, exist_ok=True)
    (RESULTS / "check_logs").mkdir(parents=True, exist_ok=True)
    with gzip.open(ROOT / rec["log_file"], "wt", encoding="utf-8") as f:
        f.write("COMMAND " + " ".join(command) + "\n" + "\nSTDERR\n" + stderr +
                "\n\nJSON STDOUT\n" + stdout)
    out_file.write_text(json.dumps(rec, indent=2) + "\n")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["screen", "search"], default="screen")
    ap.add_argument("--limit", type=int, default=0, help="optional preflight, no claim of full execution")
    ap.add_argument("--crate", default="")
    args = ap.parse_args()
    metas = {m["crate"]: m for m in json.loads((DATA / "crates_manifest.json").read_text())}
    corpus = {r["id"]: r for r in read_jsonl(DATA / "corpus.jsonl")}
    sample = json.loads((DATA / "frozen_sample.json").read_text())
    assignments = sample["assignments"]
    # Repeated seed assignments must share labels and replays.
    ids = list(dict.fromkeys(r["id"] for r in assignments if not args.crate or r["crate"] == args.crate))
    if args.limit:
        ids = ids[:args.limit]
    (RESULTS / "checks").mkdir(parents=True, exist_ok=True)
    if args.stage == "screen":
        prev = {r["id"]: r for r in read_jsonl(RESULTS / "screen.jsonl")}
        for i, rid in enumerate(ids, 1):
            row = corpus[rid]
            meta = metas[row["crate"]]
            default = run_check(meta, row, "default")
            docs = run_check(meta, row, "docs")
            docs_cfg = None
            if docs["status"] == "fail" and (
                meta["docs_metadata"].get("rustc-args") or meta["docs_metadata"].get("rustdoc-args")
            ):
                docs_cfg = run_check(meta, row, "docs_cfg")
            label = "eligible_mismatch" if (default["status"] == "fail" and docs["status"] == "pass") else (
                "default_compiles" if default["status"] == "pass" else (
                "cfg_dependent" if (docs_cfg is not None and docs_cfg["status"] == "pass") else (
                "invalid_doc_sample" if docs["status"] == "fail" else "infrastructure")))
            prev[rid] = {"id": rid, "crate": row["crate"], "source": row["source"],
                         "line": row["line"], "risk": bool(any(x["id"] == rid and x["stratum"] == "risk" for x in assignments)),
                         "default": default["key"], "docs": docs["key"],
                         "docs_cfg": docs_cfg["key"] if docs_cfg else None,
                         "default_status": default["status"], "docs_status": docs["status"],
                         "label": label}
            (RESULTS / "screen.jsonl").write_text("".join(json.dumps(x) + "\n" for x in prev.values()))
            print(f"[{i:03}/{len(ids)}] {row['crate']} {rid} default={default['status']} docs={docs['status']} => {label}", flush=True)
    else:
        prev = {r["id"]: r for r in read_jsonl(RESULTS / "search.jsonl")}
        screened = {r["id"]: r for r in read_jsonl(RESULTS / "screen.jsonl")}
        for i, rid in enumerate(ids, 1):
            row = corpus[rid]
            if screened.get(rid, {}).get("label") != "eligible_mismatch":
                continue
            if rid in prev:
                continue
            prev[rid] = explore(meta=metas[row["crate"]], row=row)
            (RESULTS / "search.jsonl").write_text("".join(json.dumps(x) + "\n" for x in prev.values()))
            print(f"[{i:03}/{len(ids)}] {row['crate']} {rid} guided={prev[rid]['guided']['pass']} "
                  f"random={[v['pass'] for v in prev[rid]['random']]}", flush=True)


def candidate_features(meta, row):
    all_feats = [f for f in meta["feature_names"] if f != "default" and not f.startswith("_")]
    code = row["compiled_code"].lower()
    # Extract paths, features, known cfg context. Static, training-free ranking.
    path_parts = re.findall(r"(?:::|\b)\w+::(\w+)", code)
    tokens = set(re.findall(r"[a-z][a-z_\d]+", code)) | set(path_parts)
    hints = {f for f in all_feats if re.search(r"\b" + re.escape(f.replace("-", "_")) + r"\b", code)}
    boosts = collections_boosts(meta, row)
    scoring = []
    for f in all_feats:
        norm = f.replace("-", "_").lower()
        parts = [p for p in re.split("[_-]", norm) if len(p) >= 2]
        score = 15 * (norm in tokens) + 3 * sum(p in tokens for p in parts)
        if f in hints:
            score += 8
        score += boosts.get(f, 0)
        if re.search(r"\bnew_" + re.escape(norm) + r"\b", code):
            score += 8
        # Prefer explicit narrow features to whole-bundle aliases.
        if f in ("full", "all", "unstable", "_unstable-all-types"):
            score -= 6
        scoring.append((score, f))
    return [f for _, f in sorted(scoring, key=lambda t: (-t[0], t[1]))]


def collections_boosts(meta, row):
    """Rule-based Rust feature contracts; no examples/outcomes are learned."""
    code = row["compiled_code"].lower()
    crate = meta["crate"]
    boost = {}

    def put(feature, n):
        boost[feature] = boost.get(feature, 0) + n

    if crate == "tokio":
        if re.search(r"#\s*\[tokio::(?:main|test)", code):
            put("macros", 24)
            put("rt-multi-thread", 16 if "current_thread" not in code else 0)
            put("rt", 12 if "current_thread" in code else 0)
        if "tokio::spawn" in code or "tokio::task" in code:
            put("rt", 13)
        if "asyncreadext" in code or "asyncwriteext" in code:
            put("io-util", 18)
    if crate == "clap" and re.search(r"#\s*\[derive\([^)]*(?:parser|subcommand|args|valueenum)", code):
        put("derive", 22)
    if crate == "strum" and re.search(r"#\s*\[derive\(", code):
        put("derive", 22)
    if crate == "uuid":
        for v in ("v1", "v3", "v4", "v5", "v6", "v7", "v8"):
            if "new_" + v in code or "::" + v in code:
                put(v, 20)
    if crate == "reqwest" and "reqwest::blocking" in code:
        put("blocking", 25)
    if crate == "sqlx":
        for database in ("postgres", "mysql", "sqlite"):
            if "sqlx::" + database in code:
                put(database, 25)
    if crate == "tracing-subscriber":
        if "tracing_subscriber::fmt" in code:
            put("fmt", 24)
        if "registry" in code:
            put("registry", 14)
    if crate == "tokio-util" and "tokio_util::codec" in code:
        put("codec", 24)
    # Rank the feature mentioned in the immediate prose/documentation above
    # the code, but do not use future compiler outcomes to build its ranking.
    context = row.get("context_before", "").lower()
    for f in meta["feature_names"]:
        if re.search(r"(?:feature[s]?|enable[d]?|cargo add).{0,35}\b" + re.escape(f.lower()) + r"\b", context):
            put(f, 8)
    return boost


def evaluate_sequence(meta, row, sequence, budget=MAX_FIX_ATTEMPTS):
    """Budget=8 *additional* Cargo checks, shared with all baselines."""
    used, additions, history = 0, [], []
    for f in sequence:
        if used >= budget:
            break
        if f in additions:
            continue
        additions.append(f)
        c = run_check(meta, row, "candidate", additions)
        used += 1
        history.append({"features": additions[:], "status": c["status"], "check": c["key"]})
        if c["status"] == "pass":
            return {"pass": True, "features": additions, "attempts": used, "history": history}
        if c["status"] == "infra":
            break
    return {"pass": False, "features": additions, "attempts": used, "history": history}


def explore(meta, row):
    features = candidate_features(meta, row)
    guided = evaluate_sequence(meta, row, features)
    explicit = [f for f in features if re.search(r"\b" + re.escape(f) + r"\b", row["raw_code"])]
    # A documented-text static baseline (same check ceiling, no diagnostic feedback).
    hint = evaluate_sequence(meta, row, explicit)
    randoms = []
    for seed in (17, 29, 43):
        rng = random.Random(f"random:{seed}:{row['id']}")
        seq = features[:]
        rng.shuffle(seq)
        randoms.append({"seed": seed, **evaluate_sequence(meta, row, seq)})
    return {"id": row["id"], "crate": meta["crate"], "rank": features,
            "budget": MAX_FIX_ATTEMPTS, "guided": guided, "explicit": hint, "random": randoms}


if __name__ == "__main__":
    main()
