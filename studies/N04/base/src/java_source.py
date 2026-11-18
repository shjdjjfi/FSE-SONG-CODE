"""Java test method snapshots from *pinned* Git revisions.

Uses Tree-sitter's syntax tree for methods. The body fingerprint retains
literal values and assertion calls: changing an expected value changes the
fingerprint. Method/test names are excluded from the body fingerprint.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
import hashlib
import re
import subprocess
from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_java


PARSER = Parser(Language(tree_sitter_java.language()))


def run_git(repo: str | Path, *args, check=True) -> str:
    p = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True)
    if p.returncode and check:
        raise RuntimeError(f"git {' '.join(args)}: {p.stderr[:350]}")
    return p.stdout if p.returncode == 0 else ""


@dataclass(frozen=True)
class Method:
    fqn: str
    classname: str
    package: str
    name: str
    path: str
    body: str
    body_hash: str
    calls: tuple[str, ...]
    parameterized: bool
    is_test: bool
    start_line: int

    def as_dict(self):
        return asdict(self)


def normalize(source: str) -> str:
    # A whitespace-normalization suitable for an *exact body* baseline;
    # no variable identifiers, constants, or assertion values are erased.
    source = re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.S)
    return re.sub(r"\s+", "", source)


def method_nodes(content: bytes, path: str) -> list[Method]:
    tree = PARSER.parse(content)
    source = content.decode("utf-8", errors="replace")
    package_match = re.search(r"(?m)^\s*package\s+([\w.]+)\s*;", source)
    package = package_match.group(1) if package_match else ""
    parameterized = "@RunWith(Parameterized.class)" in source or "@ParameterizedTest" in source
    result = []

    def walk(node, ancestors=()):
        if node.type in ("class_declaration", "interface_declaration", "record_declaration"):
            name = node.child_by_field_name("name")
            if name:
                ancestors += (content[name.start_byte:name.end_byte].decode("utf-8"),)
        if node.type == "method_declaration":
            name = node.child_by_field_name("name")
            body = node.child_by_field_name("body")
            if name is not None and body is not None and ancestors:
                name_string = content[name.start_byte:name.end_byte].decode("utf-8")
                body_text = content[body.start_byte:body.end_byte].decode("utf-8", errors="replace")
                signature = content[node.start_byte:body.start_byte].decode("utf-8", errors="replace")
                compact = normalize(body_text)
                calls = tuple(sorted(set(re.findall(
                    r"\b(?:assert\w+|expect\w*|verify|fail|run\w*|should\w*)\s*\(", body_text
                ))))
                classname = ".".join((*([package] if package else []), *ancestors))
                result.append(Method(
                    fqn=f"{classname}.{name_string}", classname=classname,
                    package=package, name=name_string, path=path,
                    body=compact, body_hash=hashlib.sha256(compact.encode()).hexdigest(),
                    calls=calls, parameterized=parameterized,
                    is_test="@Test" in signature or name_string.startswith("test"),
                    start_line=node.start_point.row + 1,
                ))
        for child in node.children:
            if child.is_named:
                walk(child, ancestors)

    walk(tree.root_node)
    return result


@lru_cache(maxsize=2000)
def methods_at(repo: str, sha: str, path: str) -> tuple[Method, ...]:
    p = subprocess.run(["git", "-C", repo, "show", f"{sha}:{path}"],
                       capture_output=True)
    if p.returncode:
        return ()
    return tuple(method_nodes(p.stdout, path))


@lru_cache(maxsize=250)
def java_test_diff(repo: str, before: str, after: str) -> tuple[list[dict], list[str], list[str]]:
    # --find-renames requires fetching every candidate blob. A repository-wide
    # packaging refactor can touch 8,000+ files; using it on partial clones
    # triggers gigabytes of downloads. Tree-only status is enough here.
    lines = run_git(repo, "diff", "--no-renames", "--name-status", before, after).splitlines()
    entries = []
    for line in lines:
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        if status.startswith("R") and len(parts) == 3:
            old, new = parts[1:]
        elif status.startswith("A"):
            old, new = None, parts[1]
        elif status.startswith("D"):
            old, new = parts[1], None
        else:
            old, new = parts[1], parts[1]
        def test_java(path):
            return bool(path and path.endswith(".java") and (
                "/test/" in path.lower() or path.lower().startswith("test/")
            ))
        if test_java(old) or test_java(new):
            entries.append({"status": status, "old": old, "new": new})
    before_paths = sorted({e["old"] for e in entries if e["old"]})
    after_paths = sorted({e["new"] for e in entries if e["new"]})
    return entries, before_paths, after_paths


def file_path_for_name(fqn: str, paths: list[str], module="") -> str | None:
    """Find a class in the *changed files*; reject ambiguous same-name classes."""
    outer = fqn.rsplit(".", 1)[0]
    klass = outer.split("$")[0].split(".")[-1]
    suffix = "/" + klass + ".java"
    valid = [x for x in paths if x.endswith(suffix)]
    if len(valid) == 1:
        return valid[0]
    if module and module != ".":
        chosen = [x for x in valid if x.startswith(module.strip("/") + "/")]
        if len(chosen) == 1:
            return chosen[0]
    return None

