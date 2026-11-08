"""GitHub REST API utilities for fetching release manifests."""
from __future__ import annotations
import json
import sys
import urllib.request
from urllib.parse import urlparse
from typing import Optional


from concurrent.futures import ThreadPoolExecutor, as_completed


def http_json(url: str, token: Optional[str] = None):
    """Fetches a JSON response from an HTTP URL, supporting optional Bearer auth token."""
    headers = {"User-Agent": "app-hub-builder"}
    if token:  # only for api.github.com, never for download redirects
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "api.github.com":
            raise ValueError(f"Security Policy Violation: Bearer token cannot be attached to {url}")
        headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        data = json.load(r)
    return data


def fetch_manifests(repo: str, token: Optional[str], max_workers: int = 8) -> list[dict]:
    """Fetches manifest.json assets from non-draft, non-prerelease releases in the GitHub repo concurrently."""
    out, page = [], 1
    while True:
        rels = http_json(f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}", token)
        if not rels:
            break
        asset_tasks: list[tuple[str, str]] = []
        for rel in rels:
            if rel.get("draft") or rel.get("prerelease"):  # skips rolling "-latest" releases
                continue
            asset = next((a for a in rel.get("assets", []) if a["name"] == "manifest.json"), None)
            if asset:
                asset_tasks.append((rel.get("tag_name", "unknown"), asset["browser_download_url"]))

        if asset_tasks:
            workers = min(max_workers, len(asset_tasks))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_tag = {executor.submit(http_json, url): tag for tag, url in asset_tasks}
                for future in as_completed(future_to_tag):
                    tag = future_to_tag[future]
                    try:
                        out.append(future.result())
                    except Exception as e:  # one bad release must not break the site build
                        print(f"warn: skipping {tag}: {e}", file=sys.stderr)
        page += 1
    return out

