import hashlib, json, os, random, subprocess, sys, time
from pathlib import Path, PurePosixPath
import tarfile, zipfile, tempfile

root=Path(sys.argv[1]).resolve()
out=Path(os.environ["IFG_OUTPUT_DIR"]).resolve()
arm=os.environ["IFG_ARM"]
seed=int(os.environ["IFG_SEED"])
tsc=root/"ts-5.9.3/package/bin/tsc"
projects=("ts-pattern","zod")
rng=random.Random(seed)

def add(project,relative,data):
    p=project/"src"/relative
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(data)

def tree(project):
    directory=project/"dist"
    return {x.relative_to(directory).as_posix():hashlib.sha256(x.read_bytes()).hexdigest()
            for x in sorted(directory.rglob("*")) if x.is_file()}

def run(project_paths, force=False):
    argv=["node",str(tsc),"-b","--verbose",*[str(p/"tsconfig.json") for p in project_paths]]
    if force: argv.append("--force")
    start=time.perf_counter()
    cp=subprocess.run(argv,capture_output=True, encoding="utf-8",timeout=90,cwd=out)
    log={"argv":argv,"exit":cp.returncode,"stdout":cp.stdout,"stderr":cp.stderr,
         "seconds":time.perf_counter()-start}
    if cp.returncode: raise RuntimeError(log)
    return log

def prepare(parent):
    a,b=(parent/name for name in projects)
    with zipfile.ZipFile(root/"ts-pattern-source.zip") as z:
        for member in z.namelist():
            p=PurePosixPath(member)
            if len(p.parts)>2 and p.parts[1]=="src" and p.suffix==".ts":
                add(a,Path(*p.parts[2:]),z.read(member))
    with tarfile.open(root/"zod-3.25.76.tgz") as z:
        for member in z:
            p=PurePosixPath(member.name)
            if (member.isfile() and p.parts[:3]==("package","src","v3") and p.suffix==".ts"
                    and not {"tests","benchmarks"}&set(p.parts)):
                add(b,Path(*p.parts[3:]),z.extractfile(member).read())
    for project in (a,b):
        config={"compilerOptions":{"target":"ES2022","module":"CommonJS","strict":True,"skipLibCheck":True,
                 "composite":True,"rootDir":"src","outDir":"dist","tsBuildInfoFile":"cache.tsbuildinfo",
                 "types":[]},"include":["src/**/*.ts"],"exclude":["**/*.test.ts","**/tests/**"]}
        (project/"tsconfig.json").write_text(json.dumps(config),encoding="utf-8")
    return {p.name:p for p in (a,b)}

records=[]
work=out/"work"
independent=out/"reference"
production=prepare(work)
reference=prepare(independent)
reference_log=run(list(reference.values()),force=True)
initial_log=run(list(production.values()))
truth={name:tree(path) for name,path in reference.items()}
valid={name:tree(path) for name,path in production.items()}
assert truth==valid and all(truth.values())
initial={name:sorted(files) for name,files in valid.items()}

# Each seed changes artifact locations. Each library is the target once.
for damaged in projects:
    p=production[damaged]
    # Omit primary entrypoints to test whether entrypoint-only checks are sufficient.
    eligible=[f for f in initial[damaged] if "/" in f]
    choices=rng.sample(eligible, 1+(seed%3))
    for relative in choices: (p/"dist"/relative).unlink()
    if arm=="baseline":
        targets=list(projects)
    elif arm=="method":
        targets=[n for n in projects if set(initial[n])-set(tree(production[n]))]
    else:
        targets=[n for n in projects if not (production[n]/"dist/index.js").is_file()]
    logs=[run([production[n] for n in targets],force=True)] if targets else []
    pre={name:tree(path) for name,path in production.items()}
    matched=pre==truth
    fallback=[]
    if not matched:
        fallback=list(projects)
        logs.append(run(list(production.values()),force=True))
    final={name:tree(path) for name,path in production.items()}
    assert final==truth
    records.append({"damaged":damaged,"removed":choices,"repair_targets":targets,
        "matched_before_independent_oracle":matched,"fallback_rebuilt":fallback,"matched_after":True,
        "expected_digests":truth,"pre_recovery_digests":pre,"after_recovery_digests":final,
        "recovery_source_units":sum(len(list((production[n]/"src").rglob("*.ts"))) for n in targets+fallback),
        "compile_seconds":sum(log["seconds"] for log in logs),"logs":logs})

# Unchanged control: any audit reporting missing output on this tree is invalid.
negative=all(sorted(tree(p))==initial[n] for n,p in production.items())
raw=out/"events.json"
raw.write_text(json.dumps({"reference":reference_log,"initial":initial_log,"negative_control":negative,
                           "records":records},indent=2),encoding="utf-8")
total=sum(r["recovery_source_units"] for r in records)
metrics={"kind":"real","arm":arm,"seed":seed,"dataset":sys.argv[2],"split":sys.argv[3],
          "recovery_source_units":total,"artifacts":["events.json"]}
(out/"metrics.json").write_text(json.dumps(metrics),encoding="utf-8")
print(total,[(r["damaged"],r["matched_before_independent_oracle"]) for r in records])

