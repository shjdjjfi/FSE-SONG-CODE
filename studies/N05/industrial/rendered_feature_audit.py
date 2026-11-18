#!/usr/bin/env python3
"""Verify feature disclosures on *version-specific* actual rendered docs pages."""
import datetime as dt
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PAGES = (
    ("tower-http", "0.6.6", "tower_http/cors/struct.CorsLayer.html", "feature `cors` only"),
    ("tower-http", "0.6.6", "tower_http/services/struct.ServeDir.html", "feature `fs` only"),
    ("tower", "0.5.2", "tower/trait.ServiceExt.html", "feature `util` only"),
    ("dashmap", "6.1.0", "dashmap/struct.DashSet.html", "Requires the `raw-api` feature"),
)


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocked = 0
        self.bits = []
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.blocked += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.blocked = max(self.blocked-1, 0)
    def handle_data(self, data):
        if self.blocked == 0:
            self.bits.append(data)


def main():
    path = ROOT / "industrial/rendered"
    path.mkdir(parents=True, exist_ok=True)
    report = []
    for crate, version, relative, expected in PAGES:
        url = f"https://docs.rs/{crate}/{version}/{relative}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (academic source audit)"})
        try:
            with urllib.request.urlopen(req, timeout=25) as f:
                payload = f.read()
                final_url = f.url
            html = payload.decode("utf-8", errors="replace")
            p = VisibleText()
            p.feed(html)
            visible = unescape(" ".join(p.bits))
            visible = re.sub(r"\s+", " ", visible)
            marker = expected.replace("`", "")
            ix = visible.lower().find(marker.lower())
            actual_match = ix >= 0
            rec = {"crate": crate, "version": version, "source_url": url,
                   "retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                   "effective_url": final_url, "html_sha256": hashlib.sha256(payload).hexdigest(),
                   "expected_explicit_feature_statement": marker,
                   "matched_in_version_specific_rendered_text": actual_match,
                   "context_excerpt": visible[max(0, ix - 140):ix+240] if actual_match else ""}
            filename = crate + "-" + version + "-" + relative.replace("/", "_")
            (path / (filename + ".html")).write_bytes(payload)
            report.append(rec)
            print(f"{crate}@{version} {relative}: disclosed={actual_match}", flush=True)
        except Exception as e:
            report.append({"source_url": url, "retrieval_error": str(e), "matched_in_version_specific_rendered_text": None})
            print(f"{url}: error {e}", flush=True)
    (ROOT / "industrial/rendered_feature_disclosure.json").write_text(json.dumps({
        "scope": "Four pre-selected already-known independent-holdout examples; descriptive verification, not an unbiased prevalence estimate.",
        "classification": "Feature requirement is disclosed on user-facing docs; consumer default-fail is not a demonstrated docs omission.",
        "cases": report}, indent=2) + "\n")


if __name__ == "__main__":
    main()
