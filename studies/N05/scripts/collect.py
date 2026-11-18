#!/usr/bin/env python3
"""Download pinned crates.io release archives and index Rustdoc code fences.

Official published .crate tarballs are used as the research units. The source
archives are not executed here; only Cargo metadata and documentation are read.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tarfile
import time
import tomllib
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "crates"
PINNED = [
    ("tokio", "1.45.1"),
    ("sqlx", "0.8.6"),
    ("clap", "4.5.40"),
    ("serde", "1.0.219"),
    ("reqwest", "0.12.19"),
    ("tracing-subscriber", "0.3.19"),
    ("rand", "0.9.1"),
    ("chrono", "0.4.41"),
    ("uuid", "1.17.0"),
    ("rayon", "1.10.0"),
    ("bitflags", "2.9.1"),
    ("itertools", "0.14.0"),
    ("futures-util", "0.3.31"),
    ("tokio-util", "0.7.15"),
    ("hyper", "1.6.0"),
    ("axum", "0.8.4"),
    ("regex", "1.11.1"),
    ("petgraph", "0.8.1"),
    ("indexmap", "2.10.0"),
    ("strum", "0.27.1"),
    ("flate2", "1.1.2"),
    ("indicatif", "0.17.11"),
    ("prost", "0.13.5"),
    ("tinyvec", "1.9.0"),
]


def extract_rustdoc_blocks(src):
    """Identify consecutive /// and //! blocks without interpreting Rust.

    This deliberately excludes macro-generated `#[doc=...]` text; coverage is
    measured on the published, literal source, not on rustdoc expansion.
    """
    blocks, current, begin = [], [], 0
    for n, line in enumerate(src.splitlines(), 1):
        m = re.match(r"^\s*//[/!](?:\s?)(.*)$", line)
        if m:
            if not current:
                begin = n
            current.append(m.group(1))
        else:
            if current:
                blocks.append((begin, "\n".join(current)))
                current = []
    if current:
        blocks.append((begin, "\n".join(current)))
    return blocks


def parse_fences(doc, path, block_start, crate, version):
    rows = []
    lines = doc.splitlines()
    ix = 0
    while ix < len(lines):
        m = re.match(r"^\s*(`{3,}|~{3,})([^`]*)$", lines[ix])
        if not m:
            ix += 1
            continue
        delim, header = m.groups()
        end = ix + 1
        while end < len(lines) and not re.match(r"^\s*" + re.escape(delim[0]) + "{" + str(len(delim)) + r",}\s*$", lines[end]):
            end += 1
        if end >= len(lines):
            ix += 1
            continue
        tags = [t.strip() for t in header.strip().split(",") if t.strip()]
        known_lang = tags[0].split()[0] if tags else "rust"
        if known_lang not in ("rust", "rs", "") or any(
            t in ("ignore", "compile_fail", "text", "should_panic") or t.startswith("ignore-") for t in tags
        ):
            ix = end + 1
            continue
        orig = "\n".join(lines[ix + 1 : end]).strip("\n")
        if not (6 <= len(orig) <= 5500) or len(orig.splitlines()) > 130:
            ix = end + 1
            continue
        normalized_name = crate.replace("-", "_")
        if not re.search(r"\b" + re.escape(normalized_name) + r"\s*::", orig):
            ix = end + 1
            continue
        # Rustdoc convention: `# ...` is compiled, but omitted from page.
        # `##` displays a literal `#` in doctests.
        def rustdoc_hidden(s):
            # Rustdoc accepts whitespace before its hidden-line marker; a
            # bare '#' stands for a hidden blank. Real Rust attributes '#['
            # are NOT hidden. `##` escapes one literal '#'.
            m = re.match(r"^(\s*)#(?:\s(.*))?$", s)
            if m:
                return (True, m.group(1) + (m.group(2) or ""))
            m = re.match(r"^(\s*)##(.*)$", s)
            if m:
                return (False, m.group(1) + "#" + m.group(2))
            return (False, s)

        decoded = [rustdoc_hidden(s) for s in orig.splitlines()]
        compiled = "\n".join(s for _, s in decoded)
        visible = "\n".join(s for hidden, s in decoded if not hidden)
        surrounding = "\n".join(lines[max(0, ix - 14) : ix])
        explicit = bool(re.search(r"\b(features?|cfg|cargo\s+add)\b", surrounding, re.I))
        item = {
            "id": hashlib.sha256(f"{crate}@{version}:{path}:{block_start + ix}:{orig}".encode()).hexdigest()[:16],
            "crate": crate,
            "version": version,
            "source": path,
            "line": block_start + ix,
            "tags": tags,
            "explicit_context": explicit,
            "context_before": surrounding,
            "raw_code": orig,
            "compiled_code": compiled,
            "visible_code": visible,
            "code_sha256": hashlib.sha256(orig.encode()).hexdigest(),
        }
        rows.append(item)
        ix = end + 1
    return rows


def collect_one(crate, version):
    RAW.mkdir(parents=True, exist_ok=True)
    target = RAW / f"{crate}-{version}.crate"
    url = f"https://static.crates.io/crates/{crate}/{crate}-{version}.crate"
    if not target.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "n05-research/0.1"})
        with urllib.request.urlopen(req, timeout=90) as stream:
            content = stream.read()
        target.write_bytes(content)
    data = target.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    docs = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        members = {m.name.split("/", 1)[-1]: m for m in tf.getmembers() if m.isfile()}
        manifest_name = "Cargo.toml.orig" if "Cargo.toml.orig" in members else "Cargo.toml"
        manifest = tomllib.loads(tf.extractfile(members[manifest_name]).read().decode("utf-8-sig"))
        for path, member in members.items():
            if not (path.startswith("src/") and path.endswith(".rs") or path.lower() in ("readme.md", "readme.markdown", "lib.md")):
                continue
            if member.size > 500_000:
                continue
            try:
                source = tf.extractfile(member).read().decode("utf-8")
            except UnicodeError:
                continue
            if path.endswith(".rs"):
                blocks = extract_rustdoc_blocks(source)
            else:
                blocks = [(1, source)]
            for start, block in blocks:
                docs.extend(parse_fences(block, path, start, crate, version))
    pkg = manifest.get("package", {})
    metadata = pkg.get("metadata", {}).get("docs", {})
    # TOML `[package.metadata.docs.rs]` creates a key `docs` -> `rs`.
    if not metadata and "docs.rs" in pkg.get("metadata", {}):
        metadata = pkg["metadata"]["docs.rs"]
    if isinstance(metadata.get("rs"), dict):
        metadata = metadata["rs"]
    features = manifest.get("features", {})
    record = {
        "crate": crate,
        "version": version,
        "archive_url": url,
        "archive_sha256": sha,
        "size": len(data),
        "edition": pkg.get("edition"),
        "rust_version": pkg.get("rust-version"),
        "license": pkg.get("license"),
        "license_file": pkg.get("license-file"),
        "repository": pkg.get("repository"),
        "docs_metadata": metadata,
        "default_features": features.get("default", []),
        "feature_names": sorted(features.keys()),
        "feature_map": features,
        "n_snippets": len(docs),
        "n_explicit": sum(r["explicit_context"] for r in docs),
    }
    return record, docs


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    rows, all_docs, failures = [], [], []
    for i, (crate, version) in enumerate(PINNED, 1):
        try:
            record, docs = collect_one(crate, version)
            rows.append(record)
            all_docs.extend(docs)
            print(f"[{i:02}/{len(PINNED)}] {crate}@{version}: {len(docs)} candidate fences, metadata={record['docs_metadata']}", flush=True)
        except Exception as ex:
            failures.append({"crate": crate, "version": version, "error": str(ex)})
            print(f"[{i:02}/{len(PINNED)}] FAIL {crate}@{version}: {ex}", flush=True)
    (DATA / "crates_manifest.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    (DATA / "corpus.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in all_docs))
    (DATA / "collection_failures.json").write_text(json.dumps(failures, indent=2))
    print(f"Downloaded {len(rows)} projects; found {len(all_docs)} candidate snippets; failed {len(failures)}")


if __name__ == "__main__":
    main()
