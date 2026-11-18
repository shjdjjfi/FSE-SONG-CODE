#!/usr/bin/env python3
"""Download and hash historical fixed-release PyPI metadata for 120 sampled projects."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parent
RESP=ROOT/'raw/pypi_responses'
RESP.mkdir(parents=True,exist_ok=True)
SAMPLES=json.loads((ROOT/'osv_sample120.json').read_text())
UA='FSE-I01-public-compatibility-research/2026.11 (public PyPI metadata only)'


def fetch(item):
    name=item['project']
    vers=item['fixed_version']
    key=f'{name}=={vers}'
    destination=RESP/f'{name}.json'
    url=f'https://pypi.org/pypi/{urllib.parse.quote(name,safe="")}/{urllib.parse.quote(vers,safe="")}/json'
    code=None
    error=None
    raw=None
    if destination.exists():
        raw=destination.read_bytes()
        code=200
    else:
        for attempt in range(3):
            try:
                request=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json'})
                with urllib.request.urlopen(request,timeout=20) as answer:
                    raw=answer.read()
                    code=answer.status
                destination.write_bytes(raw)
                error=None
                break
            except urllib.error.HTTPError as exc:
                code=exc.code
                error=f'http_{code}'
                if 400<=exc.code<500:
                    break
            except Exception as exc:
                error=f'{type(exc).__name__}: {str(exc)[:120]}'
            time.sleep(0.25 * (attempt+1))
    obj=None
    try:
        obj=json.loads(raw) if raw else None
    except Exception as exc:
        error=f'json_error: {str(exc)[:100]}'
    urls=(obj or {}).get('urls',[])
    files=[]
    for f in urls:
        files.append({
            'filename':f.get('filename'),
            'packagetype':f.get('packagetype'),
            'requires_python':f.get('requires_python'),
            'yanked':bool(f.get('yanked',False)),
            'upload_time_iso_8601':f.get('upload_time_iso_8601'),
            'sha256':(f.get('digests') or {}).get('sha256'),
        })
    return {
        'key':key,'project':name,'version':vers,'source_url':url,
        'status':'ok' if obj else (error or f'http_{code}'),
        'http_status':code,'retrieved_utc':datetime.now(timezone.utc).isoformat(),
        'response_sha256':hashlib.sha256(raw).hexdigest() if raw else None,
        'requires_python':((obj or {}).get('info') or {}).get('requires_python'),
        'files':files,'release_file_count':len(files),
        'raw_response_path':str(destination.relative_to(ROOT)) if raw else None,
    }


def main():
    answers=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(fetch,item):item for item in SAMPLES}
        for n,future in enumerate(as_completed(futures),1):
            try:r=future.result()
            except Exception as exc:
                item=futures[future]
                r={'key':f"{item['project']}=={item['fixed_version']}",'project':item['project'],
                   'version':item['fixed_version'],'status':f'unexpected_{type(exc).__name__}',
                   'error':str(exc)[:150], 'files':[]}
            answers.append(r)
            if n%15==0:
                print(f'Fetched {n:3d}/{len(SAMPLES)}, success {sum(x["status"]=="ok" for x in answers)}',flush=True)
    answers.sort(key=lambda x:x['project'])
    (ROOT/'metadata_index.json').write_text(json.dumps(answers,indent=2,ensure_ascii=False))
    from collections import Counter
    print('STATUS',dict(Counter(r['status'] for r in answers)),flush=True)
    print('WHEELS',sum(sum(f['packagetype']=='bdist_wheel' for f in x['files']) for x in answers),flush=True)


if __name__=='__main__':main()
