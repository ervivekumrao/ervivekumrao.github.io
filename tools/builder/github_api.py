"""GitHub REST API utilities for fetching release manifests."""
from __future__ import annotations
import json
import sys
import urllib.request
from typing import Optional


def http_json(url: str, token: Optional[str] = None):
    """Fetches a JSON response from an HTTP URL, supporting optional Bearer auth token."""
    headers = {"User-Agent": "app-hub-builder"}
    if token:  # only for api.github.com, never for download redirects
        headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        data = json.load(r)
    return data


def fetch_manifests(repo: str, token: Optional[str]) -> list[dict]:
    """Fetches manifest.json assets from non-draft, non-prerelease releases in the GitHub repo."""
    out, page = [], 1
    while True:
        rels = http_json(f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}", token)
        if not rels:
            break
        for rel in rels:
            if rel.get("draft") or rel.get("prerelease"):  # skips rolling "-latest" releases
                continue
            asset = next((a for a in rel.get("assets", []) if a["name"] == "manifest.json"), None)
            if asset:
                try:
                    out.append(http_json(asset["browser_download_url"]))
                except Exception as e:  # one bad release must not break the site build
                    print(f"warn: skipping {rel.get('tag_name')}: {e}", file=sys.stderr)
        page += 1
    return out
