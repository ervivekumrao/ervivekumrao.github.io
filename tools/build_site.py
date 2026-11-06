#!/usr/bin/env python3
"""Zero-cost static site generator for the app hub.

Inputs : catalog/site.json, catalog/projects/<id>/{project.json,privacy.md,assets/*}, static/*
         + release manifests (manifest.json assets) from this repo's GitHub Releases.
Outputs: <out>/index.html, apps/<id>/, libs/<id>/, api/catalog.json, style.css

Usage  : python tools/build_site.py --out dist                 (CI: reads Releases via API)
         python tools/build_site.py --out dist --fixture tools/fixtures/manifests.sample.json   (offline)
"""
from __future__ import annotations
import argparse, html, json, os, shutil, sys, urllib.request
from pathlib import Path

try:
    import markdown as _md
except ImportError:  # optional
    _md = None
try:
    import segno
except ImportError:  # optional: QR codes are skipped without it
    segno = None

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"


def esc(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def http_json(url: str, token: str | None = None):
    headers = {"User-Agent": "app-hub-builder"}
    if token:  # only for api.github.com, never for download redirects
        headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return json.load(r)


def fetch_manifests(repo: str, token: str | None) -> list[dict]:
    out, page = [], 1
    while True:
        rels = http_json(f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}", token)
        if not rels:
            break
        for rel in rels:
            if rel.get("draft") or rel.get("prerelease"):  # skips the rolling "-latest" releases
                continue
            asset = next((a for a in rel.get("assets", []) if a["name"] == "manifest.json"), None)
            if asset:
                try:
                    out.append(http_json(asset["browser_download_url"]))
                except Exception as e:  # one bad release must not break the site
                    print(f"warn: skipping {rel.get('tag_name')}: {e}", file=sys.stderr)
        page += 1
    return out


def human_size(n: int) -> str:
    return f"{n / 1_048_576:.1f} MB"


def md_to_html(text: str) -> str:
    return _md.markdown(text, extensions=["extra"]) if _md else f"<pre>{esc(text)}</pre>"


CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--mut:#5f6368;--card:#f6f8fa;--line:#d0d7de;--acc:#0b5fff}
@media(prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--mut:#9aa4af;--card:#161b22;--line:#30363d;--acc:#58a6ff}}
*{box-sizing:border-box}body{margin:0;font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg)}
a{color:var(--acc)}main,header>div,footer{max-width:960px;margin:0 auto;padding:1rem}
header{border-bottom:1px solid var(--line)}header a{text-decoration:none;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:1rem}
.card h3{margin:.2rem 0}.mut{color:var(--mut)}.tag{display:inline-block;font-size:.75rem;border:1px solid var(--line);border-radius:99px;padding:0 .5rem;margin:0 .25rem .25rem 0}
.btn{display:inline-block;background:var(--acc);color:#fff;padding:.5rem 1rem;border-radius:8px;text-decoration:none;margin:.25rem .5rem .25rem 0}
.btn.alt{background:transparent;color:var(--acc);border:1px solid var(--acc)}
.shots{display:flex;gap:.75rem;overflow-x:auto}.shots img{height:360px;border-radius:8px;border:1px solid var(--line)}
code,pre{background:var(--card);border-radius:6px}pre{padding:.75rem;overflow-x:auto}code{padding:.1rem .3rem}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid var(--line);padding:.4rem;text-align:left}
.qr svg{max-width:240px;height:auto;background:#fff;padding:8px;border-radius:8px}.wrap{overflow-x:auto}
"""


class Site:
    def __init__(self, out: Path, cfg: dict):
        self.out, self.cfg = out, cfg
        self.base = cfg.get("base_path", "").rstrip("/")

    def url(self, path: str) -> str:
        return f"{self.base}/{path.lstrip('/')}"

    def write(self, rel: str, content: str):
        p = self.out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def page(self, title: str, body: str, desc: str = "") -> str:
        s = self.cfg
        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · {esc(s.get('name'))}</title><meta name="description" content="{esc(desc or s.get('tagline'))}">
<link rel="stylesheet" href="{self.url('style.css')}"></head><body>
<header><div><a href="{self.url('/')}">{esc(s.get('name'))}</a></div></header>
<main>{body}</main>
<footer class="mut">{esc(s.get('footer', ''))}</footer></body></html>"""


def enrollment_payload(p: dict, m: dict) -> dict:
    do = p.get("device_owner", {})
    return {
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME": do["admin_component"],
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_PACKAGE_DOWNLOAD_LOCATION": m["url_latest"],
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM": m["cert_sha256_b64url"],
    }


def render_download(site: Site, p: dict, versions: list[dict]) -> str:
    if not versions:
        return "<h2>Download</h2><p class='mut'>No release has been published yet.</p>"
    m = versions[0]
    h = [f"<h2>Download</h2><p>Latest: <strong>{esc(m['version_name'])}</strong> · "
         f"{human_size(m['size_bytes'])} · Android {esc(m['min_sdk'])}+</p>",
         f"<a class='btn' href='{esc(m['url_latest'])}'>Download APK (latest)</a>",
         f"<a class='btn alt' href='{esc(m['url_versioned'])}'>This exact version</a>",
         f"<p class='mut'>SHA-256: <code>{esc(m['sha256'])}</code><br>"
         f"Signing certificate SHA-256: <code>{esc(m['cert_sha256_hex'])}</code></p>"]
    do = p.get("device_owner", {})
    if do.get("enabled") and do.get("admin_component"):
        payload = json.dumps(enrollment_payload(p, m), separators=(",", ":"))
        h.append("<h3>Device-owner enrollment (QR)</h3><p class='mut'>Factory-reset device: tap the welcome screen "
                 "6 times, then scan this code. Always points to the latest build.</p>")
        if segno:
            qr = segno.make(payload, error="l")
            svg = qr.svg_inline(scale=6, border=2)
            h.append(f"<div class='qr'>{svg}</div>")
        h.append(f"<details><summary>QR payload</summary><pre>{esc(payload)}</pre></details>")
    rows = "".join(f"<tr><td>{esc(v['version_name'])}</td><td>{esc(v['released_at'][:10])}</td>"
                   f"<td><a href='{esc(v['url_versioned'])}'>APK</a></td></tr>" for v in versions[:15])
    h.append(f"<h3>Versions</h3><div class='wrap'><table><tr><th>Version</th><th>Date</th><th>File</th></tr>{rows}</table></div>")
    return "".join(h)


def render_project(site: Site, p: dict, versions: list[dict], root: Path):
    kind = "libs" if p.get("type") == "library" else "apps"
    pid = p["id"]
    links = []
    if p.get("play_store_url"):
        links.append(f"<a class='btn' href='{esc(p['play_store_url'])}'>Get it on Google Play</a>")
    if p.get("visibility") == "public" and p.get("repo"):
        links.append(f"<a class='btn alt' href='https://github.com/{esc(p['repo'])}'>Source code</a>")
    if (root / "privacy.md").exists():
        links.append(f"<a class='btn alt' href='{site.url(f'{kind}/{pid}/privacy/')}'>Privacy policy</a>")
    shots = "".join(f"<img loading='lazy' alt='' src='{site.url(f'{kind}/{pid}/assets/{s}')}'>" for s in p.get("screenshots", []))
    desc = "".join(f"<p>{esc(x)}</p>" for x in p.get("description", "").split("\n\n") if x.strip())
    tags = "".join(f"<span class='tag'>{esc(t)}</span>" for t in p.get("tags", []))
    icon_hdr = ""
    for icon_name in ("icon.svg", "icon.png"):
        if (root / "assets" / icon_name).exists():
            icon_hdr = f"<img src='{site.url(f'{kind}/{pid}/assets/{icon_name}')}' alt='' style='width:64px;height:64px;border-radius:12px;margin-bottom:1rem;display:block'>"
            break
    body = f"{icon_hdr}<h1>{esc(p['name'])}</h1><p class='mut'>{esc(p.get('tagline'))}</p>{tags}{desc}{''.join(links)}"
    if shots:
        body += f"<div class='shots'>{shots}</div>"
    if kind == "apps":
        body += render_download(site, p, versions)
    else:
        lib = p.get("library", {})
        if lib.get("jitpack"):
            ver = lib.get("latest_version", "TAG")
            body += ("<h2>Install</h2><pre>repositories { maven { url = uri(\"https://jitpack.io\") } }\n"
                     f"dependencies {{ implementation(\"{esc(lib['jitpack'])}:{esc(ver)}\") }}</pre>")
        if lib.get("docs_url"):
            body += f"<p><a href='{esc(lib['docs_url'])}'>API documentation</a></p>"
    site.write(f"{kind}/{pid}/index.html", site.page(p["name"], body, p.get("tagline", "")))
    if (root / "privacy.md").exists():
        site.write(f"{kind}/{pid}/privacy/index.html", site.page(f"{p['name']} privacy policy",
                   md_to_html((root / "privacy.md").read_text(encoding="utf-8"))))
    if (root / "assets").is_dir():
        shutil.copytree(root / "assets", site.out / kind / pid / "assets", dirs_exist_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist")
    ap.add_argument("--fixture", help="JSON list of manifests (offline testing)")
    a = ap.parse_args()

    cfg = json.loads((CATALOG / "site.json").read_text(encoding="utf-8"))
    out = ROOT / a.out
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    site = Site(out, cfg)
    site.write("style.css", CSS)
    if (ROOT / "static").is_dir():
        shutil.copytree(ROOT / "static", out, dirs_exist_ok=True)

    if a.fixture:
        manifests = json.loads(Path(a.fixture).read_text(encoding="utf-8"))
    else:
        manifests = fetch_manifests(os.environ["HUB_REPO"], os.environ.get("GITHUB_TOKEN"))
    by_app: dict[str, list[dict]] = {}
    for m in manifests:
        by_app.setdefault(m["app_id"], []).append(m)
    for v in by_app.values():
        v.sort(key=lambda m: m["version_code"], reverse=True)

    projects = []
    for pj in sorted((CATALOG / "projects").glob("*/project.json")):
        p = json.loads(pj.read_text(encoding="utf-8"))
        if p.get("published", True):
            projects.append((p, pj.parent))
    projects.sort(key=lambda t: (t[0].get("order", 100), t[0]["name"].lower()))

    sections = {"app": [], "library": [], "other": []}
    for p, root in projects:
        versions = by_app.get(p["id"], [])
        render_project(site, p, versions, root)
        kind = "libs" if p.get("type") == "library" else "apps"
        badge = f"v{esc(versions[0]['version_name'])}" if versions else ""
        icon_card = ""
        for icon_name in ("icon.svg", "icon.png"):
            if (root / "assets" / icon_name).exists():
                icon_card = f"<img src='{site.url(f'{kind}/{p[\"id\"]}/assets/{icon_name}')}' alt='' style='width:28px;height:28px;border-radius:6px;vertical-align:middle;margin-right:.5rem'>"
                break
        sections.get(p.get("type", "app"), sections["other"]).append(
            f"<div class='card'><h3>{icon_card}<a href='{site.url(f'{kind}/{p[\"id\"]}/')}'>{esc(p['name'])}</a></h3>"
            f"<p class='mut'>{esc(p.get('tagline'))}</p><span class='tag'>{badge or esc(p.get('type', 'app'))}</span></div>")

    body = f"<h1>{esc(cfg.get('name'))}</h1><p>{esc(cfg.get('bio'))}</p>"
    for key, title in (("app", "Apps"), ("library", "Libraries"), ("other", "Other")):
        if sections[key]:
            body += f"<h2>{title}</h2><div class='grid'>{''.join(sections[key])}</div>"
    links = " · ".join(f"<a href='{esc(u)}'>{esc(n)}</a>" for n, u in cfg.get("links", {}).items())
    body += f"<p>{links}</p>"
    site.write("index.html", site.page(cfg.get("name", "Home"), body, cfg.get("tagline", "")))

    site.write("api/catalog.json", json.dumps({
        "projects": [p for p, _ in projects],
        "latest": {k: v[0] for k, v in by_app.items()}}, indent=2))
    print(f"built {len(projects)} projects, {len(manifests)} releases -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
