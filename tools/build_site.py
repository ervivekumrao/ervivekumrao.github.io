#!/usr/bin/env python3
"""Zero-cost static site generator for the app hub.

Inputs : catalog/site.json, catalog/projects/<id>/{project.json,privacy.md,assets/*}, static/*
         + release manifests (manifest.json assets) from this repo's GitHub Releases.
Outputs: <out>/index.html, apps/<id>/, libs/<id>/, api/catalog.json, style.css

Usage  : python tools/build_site.py --out dist                 (CI: reads Releases via API)
         python tools/build_site.py --out dist --fixture tools/fixtures/manifests.sample.json   (offline)
"""
from __future__ import annotations
import argparse, base64, html, json, os, shutil, sys, urllib.request
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
            if rel.get("draft") or rel.get("prerelease"):  # skips rolling "-latest" releases
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
:root{--bg:#f8fafc;--fg:#0f172a;--mut:#64748b;--card:#ffffff;--card-border:#e2e8f0;--card-shadow:0 4px 14px -2px rgba(0,0,0,0.06);--line:#e2e8f0;--acc:#2563eb;--acc-hover:#1d4ed8;--acc-glow:rgba(37,99,235,0.12);--tag-bg:#f1f5f9;--tag-fg:#334155}
@media(prefers-color-scheme:dark){:root{--bg:#0b0f19;--fg:#f8fafc;--mut:#94a3b8;--card:#131b2e;--card-border:#1e293b;--card-shadow:0 4px 20px -2px rgba(0,0,0,0.35);--line:#1e293b;--acc:#38bdf8;--acc-hover:#0284c7;--acc-glow:rgba(56,189,248,0.2);--tag-bg:#1e293b;--tag-fg:#cbd5e1}}
html[data-theme="light"]{:root{--bg:#f8fafc;--fg:#0f172a;--mut:#64748b;--card:#ffffff;--card-border:#e2e8f0;--card-shadow:0 4px 14px -2px rgba(0,0,0,0.06);--line:#e2e8f0;--acc:#2563eb;--acc-hover:#1d4ed8;--acc-glow:rgba(37,99,235,0.12);--tag-bg:#f1f5f9;--tag-fg:#334155}}
html[data-theme="dark"]{:root{--bg:#0b0f19;--fg:#f8fafc;--mut:#94a3b8;--card:#131b2e;--card-border:#1e293b;--card-shadow:0 4px 20px -2px rgba(0,0,0,0.35);--line:#1e293b;--acc:#38bdf8;--acc-hover:#0284c7;--acc-glow:rgba(56,189,248,0.2);--tag-bg:#1e293b;--tag-fg:#cbd5e1}}
*{box-sizing:border-box}body{margin:0;font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg);-webkit-font-smoothing:antialiased}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
main,header>div,footer{max-width:1040px;margin:0 auto;padding:1.5rem 1rem}
header{border-bottom:1px solid var(--line);background:var(--card);backdrop-filter:blur(8px);position:sticky;top:0;z-index:100}
header>div{display:flex;align-items:center;justify-content:space-between;padding:.75rem 1rem}
header a.logo{text-decoration:none;font-weight:700;font-size:1.25rem;color:var(--fg);letter-spacing:-0.02em}
.theme-btn{background:transparent;border:1px solid var(--card-border);color:var(--fg);padding:.35rem .75rem;border-radius:8px;cursor:pointer;font-size:.85rem;font-weight:500;display:inline-flex;align-items:center;gap:.4rem;transition:background .15s ease,border-color .15s ease}
.theme-btn:hover{background:var(--tag-bg);border-color:var(--acc)}
.hero-box{background:var(--card);border:1px solid var(--card-border);border-radius:16px;padding:2.5rem 2rem;margin-bottom:2.5rem;box-shadow:var(--card-shadow)}
.hero-box h1{margin:0 0 .5rem 0;font-size:2.25rem;letter-spacing:-0.03em}.hero-box p.lead{font-size:1.15rem;color:var(--mut);margin:0 0 1.5rem 0;max-width:780px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1.25rem;margin-top:1rem}
.card{background:var(--card);border:1px solid var(--card-border);border-radius:14px;padding:1.25rem;transition:transform .2s ease,box-shadow .2s ease,border-color .2s ease;box-shadow:var(--card-shadow);display:flex;flex-direction:column}
.card:hover{transform:translateY(-2px);box-shadow:0 8px 24px -4px rgba(0,0,0,0.12);border-color:var(--acc)}
.card-title{display:flex;align-items:center;margin:0 0 .5rem 0;font-size:1.15rem;font-weight:600}
.card-title img{width:32px;height:32px;border-radius:8px;margin-right:.75rem;object-fit:contain;flex-shrink:0}
.card p{color:var(--mut);font-size:.925rem;margin:0 0 1rem 0;flex-grow:1;line-height:1.5}
.card-footer{display:flex;align-items:center;justify-content:space-between;margin-top:auto;padding-top:.75rem;border-top:1px dashed var(--line)}
.mut{color:var(--mut)}.tag{display:inline-block;font-size:.75rem;font-weight:500;background:var(--tag-bg);color:var(--tag-fg);border-radius:6px;padding:.2rem .6rem;margin:0 .3rem .3rem 0}
.btn{display:inline-flex;align-items:center;justify-content:center;background:var(--acc);color:#fff!important;font-weight:600;font-size:.9rem;padding:.6rem 1.25rem;border-radius:8px;text-decoration:none!important;margin:.25rem .5rem .25rem 0;transition:background .15s ease,transform .1s ease}
.btn:hover{background:var(--acc-hover);transform:translateY(-1px)}.btn.alt{background:transparent;color:var(--acc)!important;border:1px solid var(--acc)}
.btn.alt:hover{background:var(--acc-glow)}.shots{display:flex;gap:1rem;overflow-x:auto;padding:.5rem 0 1rem 0;scrollbar-width:thin}
.shots img{height:320px;border-radius:12px;border:1px solid var(--card-border);box-shadow:var(--card-shadow);flex-shrink:0}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;font-size:.875rem}
pre{background:var(--card);border:1px solid var(--card-border);border-radius:10px;padding:1rem;overflow-x:auto}
code{background:var(--tag-bg);padding:.15rem .4rem;border-radius:4px;color:var(--fg)}
table{border-collapse:collapse;width:100%;margin:1rem 0}td,th{border-bottom:1px solid var(--line);padding:.6rem .75rem;text-align:left}
th{font-weight:600;color:var(--mut);font-size:.85rem;text-transform:uppercase;letter-spacing:.5px}
.qr{background:#fff;padding:12px;border-radius:12px;display:inline-block;box-shadow:var(--card-shadow)}.qr svg{max-width:220px;height:auto;display:block}.wrap{overflow-x:auto}
.proj-header{display:flex;align-items:flex-start;gap:1.25rem;margin-bottom:1.5rem;flex-wrap:wrap}
.proj-icon{width:72px;height:72px;border-radius:16px;object-fit:contain;box-shadow:var(--card-shadow);flex-shrink:0}
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

    def page(self, title: str, body: str, desc: str = "", icon_url: str = "") -> str:
        s = self.cfg
        icon_href = icon_url if icon_url else self.url("favicon.svg")
        icon_type = "image/svg+xml" if icon_href.endswith(".svg") else "image/png"
        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<script>(function(){{var t=localStorage.getItem("theme");if(t){{document.documentElement.setAttribute("data-theme",t);}}}})();</script>
<title>{esc(title)} · {esc(s.get('name'))}</title><meta name="description" content="{esc(desc or s.get('tagline'))}">
<link rel="icon" type="{icon_type}" href="{icon_href}">
<link rel="apple-touch-icon" href="{icon_href}">
<link rel="stylesheet" href="{self.url('style.css')}"></head><body>
<header><div><a class="logo" href="{self.url('/')}">{esc(s.get('name'))}</a><button id="theme-toggle" class="theme-btn" aria-label="Toggle dark/light theme"><span id="theme-icon">☀️</span> <span id="theme-label" class="mut">Theme</span></button></div></header>
<main>{body}</main>
<footer class="mut" style="border-top:1px solid var(--line);margin-top:3rem;padding-top:1.5rem">{esc(s.get('footer', ''))}</footer>
<script>
(function(){{
  var btn = document.getElementById("theme-toggle");
  var icon = document.getElementById("theme-icon");
  var label = document.getElementById("theme-label");
  if(!btn) return;
  function getTheme(){{
    var d = document.documentElement.getAttribute("data-theme");
    if(d) return d;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }}
  function updateUI(t){{
    icon.textContent = t === "dark" ? "🌙" : "☀️";
    label.textContent = t === "dark" ? "Dark" : "Light";
  }}
  updateUI(getTheme());
  btn.addEventListener("click", function(){{
    var current = getTheme();
    var next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
    updateUI(next);
  }});
}})();
</script>
</body></html>"""


def enrollment_payload(p: dict, m: dict) -> dict:
    do = p.get("device_owner", {})
    return {
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME": do["admin_component"],
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_PACKAGE_DOWNLOAD_LOCATION": m["url_latest"],
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM": m["cert_sha256_b64url"],
    }


def render_download(site: Site, p: dict, versions: list[dict]) -> str:
    if not versions:
        return "<h2 style='margin-top:2rem'>Download</h2><p class='mut'>No release has been published yet.</p>"
    m = versions[0]
    h = [f"<h2 style='margin-top:2rem'>Download</h2><p>Latest: <strong>{esc(m['version_name'])}</strong> · "
         f"{human_size(m['size_bytes'])} · Android {esc(m['min_sdk'])}+</p>",
         f"<a class='btn' href='{esc(m['url_latest'])}'>Download APK (latest)</a>",
         f"<a class='btn alt' href='{esc(m['url_versioned'])}'>This exact version</a>",
         f"<p class='mut' style='margin-top:1rem'>SHA-256: <code>{esc(m['sha256'])}</code><br>"
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
        h.append(f"<details style='margin-top:.5rem'><summary>QR payload</summary><pre>{esc(payload)}</pre></details>")
    rows = "".join(f"<tr><td>{esc(v['version_name'])}</td><td>{esc(v['released_at'][:10])}</td>"
                   f"<td><a href='{esc(v['url_versioned'])}'>APK</a></td></tr>" for v in versions[:15])
    h.append(f"<h3>Versions</h3><div class='wrap'><table><tr><th>Version</th><th>Date</th><th>File</th></tr>{rows}</table></div>")
    return "".join(h)


def render_project(site: Site, p: dict, versions: list[dict], root: Path):
    kind = p.get("type", "app")
    pid = p["id"]
    links = []
    if p.get("play_store_url"):
        links.append(f"<a class='btn' href='{esc(p['play_store_url'])}'>Get it on Google Play</a>")
    if p.get("visibility") == "public" and p.get("repo"):
        links.append(f"<a class='btn alt' href='https://github.com/{esc(p['repo'])}'>Source code</a>")
    if (root / "privacy.md").exists():
        links.append(f"<a class='btn alt' href='{site.url(f'{pid}/privacy/')}'>Privacy policy</a>")

    assets_dir = root / "assets"
    out_assets_dir = site.out / pid / "assets"

    if assets_dir.is_dir():
        shutil.copytree(assets_dir, out_assets_dir, dirs_exist_ok=True)

    tab_icon_url = ""
    icon_hdr = ""

    if (assets_dir / "icon.svg").exists():
        tab_icon_url = site.url(f"{pid}/assets/icon.svg")
        icon_hdr = f"<img class='proj-icon' src='{tab_icon_url}' alt='{esc(p['name'])} icon'>"
    elif (assets_dir / "icon.png").exists():
        png_bytes = (assets_dir / "icon.png").read_bytes()
        b64_str = base64.b64encode(png_bytes).decode("ascii")
        data_uri = f"data:image/png;base64,{b64_str}"
        svg_tab_content = (
            '<svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">\n'
            '  <defs>\n'
            '    <clipPath id="tab-round-corner">\n'
            '      <rect width="120" height="120" rx="26"/>\n'
            '    </clipPath>\n'
            '  </defs>\n'
            f'  <image href="{data_uri}" width="120" height="120" clip-path="url(#tab-round-corner)"/>\n'
            '</svg>\n'
        )
        out_assets_dir.mkdir(parents=True, exist_ok=True)
        (out_assets_dir / "icon_tab.svg").write_text(svg_tab_content, encoding="utf-8")
        tab_icon_url = site.url(f"{pid}/assets/icon_tab.svg")
        icon_hdr = f"<img class='proj-icon' src='{tab_icon_url}' alt='{esc(p['name'])} icon'>"

    shots = "".join(f"<img loading='lazy' alt='' src='{site.url(f'{pid}/assets/{s}')}'>" for s in p.get("screenshots", []))
    desc = "".join(f"<p>{esc(x)}</p>" for x in p.get("description", "").split("\n\n") if x.strip())
    tags = "".join(f"<span class='tag'>{esc(t)}</span>" for t in p.get("tags", []))

    header_html = f"<div class='proj-header'>{icon_hdr}<div><h1 style='margin:0 0 .25rem 0'>{esc(p['name'])}</h1><p class='mut' style='font-size:1.1rem;margin:0 0 .75rem 0'>{esc(p.get('tagline'))}</p>{tags}</div></div>"
    body = f"{header_html}<div style='margin:1.5rem 0'>{desc}</div><div style='margin-bottom:2rem'>{''.join(links)}</div>"

    if shots:
        body += f"<h2 style='margin-top:2rem'>Showcase</h2><div class='shots'>{shots}</div>"

    if kind == "app":
        body += render_download(site, p, versions)
    else:
        lib = p.get("library", {})
        if lib.get("jitpack"):
            ver = lib.get("latest_version", "TAG")
            body += ("<h2 style='margin-top:2rem'>Install</h2><pre>repositories { maven { url = uri(\"https://jitpack.io\") } }\n"
                     f"dependencies {{ implementation(\"{esc(lib['jitpack'])}:{esc(ver)}\") }}</pre>")
        if lib.get("docs_url"):
            body += f"<p><a class='btn alt' href='{esc(lib['docs_url'])}'>API documentation</a></p>"

    site.write(f"{pid}/index.html", site.page(p["name"], body, p.get("tagline", ""), icon_url=tab_icon_url))
    if (root / "privacy.md").exists():
        site.write(f"{pid}/privacy/index.html", site.page(f"{p['name']} Privacy Policy",
                   md_to_html((root / "privacy.md").read_text(encoding="utf-8")), icon_url=tab_icon_url))


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
        pid = p["id"]
        badge = f"v{esc(versions[0]['version_name'])}" if versions else ""

        icon_card = ""
        if (root / "assets" / "icon.svg").exists():
            icon_url = site.url(f"{pid}/assets/icon.svg")
            icon_card = f"<img src='{icon_url}' alt=''>"
        elif (root / "assets" / "icon.png").exists():
            icon_url = site.url(f"{pid}/assets/icon_tab.svg")
            icon_card = f"<img src='{icon_url}' alt=''>"

        proj_url = site.url(f"{pid}/")
        tag_badge = badge or esc(p.get("type", "app"))
        sections.get(p.get("type", "app"), sections["other"]).append(
            f"<div class='card'>"
            f"<div class='card-title'>{icon_card}<a href='{proj_url}'>{esc(p['name'])}</a></div>"
            f"<p>{esc(p.get('tagline'))}</p>"
            f"<div class='card-footer'><span class='tag'>{tag_badge}</span><a href='{proj_url}' style='font-size:0.85rem;font-weight:600'>Details &rarr;</a></div>"
            f"</div>"
        )

    # Hero & Portfolio Sections
    profile_url = site.url("profile.jpg")
    hero_html = f"""<div class="hero-box">
<div style="display:flex;gap:2rem;align-items:center;flex-wrap:wrap">
  <div style="flex:1;min-width:280px">
    <div style="display:inline-flex;align-items:center;background:var(--tag-bg);color:var(--tag-fg);padding:0.3rem 0.8rem;border-radius:99px;font-size:0.85rem;font-weight:500;margin-bottom:1rem">
      <span style="width:8px;height:8px;background:#10b981;border-radius:50%;display:inline-block;margin-right:0.5rem"></span>
      Available for new opportunities
    </div>
    <h1 style="margin:0 0 0.75rem 0;font-size:2.5rem;letter-spacing:-0.03em">Hi, I'm Vivek Umrao.</h1>
    <p class="lead" style="font-size:1.1rem;line-height:1.65;color:var(--mut);margin-bottom:1.5rem">
      <em>"Most software engineers build on top of platforms. I build the platforms themselves."</em> As a Principal Software Engineer and Systems Architect with 15+ years of experience, I specialize in JVM internals, enterprise scale, and device-level security.
    </p>
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap">
      <a href="https://www.linkedin.com/in/ervivekumrao/" class="btn" target="_blank">Connect on LinkedIn</a>
      <a href="https://github.com/ervivekumrao" class="btn alt" target="_blank">View GitHub Profile</a>
      <a href="mailto:vivekumraomain@gmail.com" class="btn alt">Email Me</a>
    </div>
  </div>
  <div style="flex-shrink:0">
    <img src="{profile_url}" alt="Vivek Umrao" style="width:160px;height:160px;border-radius:50%;object-fit:cover;border:3px solid var(--card-border);box-shadow:var(--card-shadow)">
  </div>
</div>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-top:2rem;padding-top:1.5rem;border-top:1px solid var(--line)">
  <div>
    <div style="font-size:1.75rem;font-weight:700;color:var(--acc)">15+</div>
    <div style="font-size:0.85rem;color:var(--mut);font-weight:500">Years Experience</div>
  </div>
  <div>
    <div style="font-size:1.75rem;font-weight:700;color:var(--acc)">Millions</div>
    <div style="font-size:0.85rem;color:var(--mut);font-weight:500">Devices Secured (Knox)</div>
  </div>
  <div>
    <div style="font-size:1.75rem;font-weight:700;color:var(--acc)">JVM & Systems</div>
    <div style="font-size:0.85rem;color:var(--mut);font-weight:500">Core Engine Architecture</div>
  </div>
</div>
</div>"""

    exp_html = """<section style="margin-top:3rem">
<h2 style="font-size:1.75rem;margin-bottom:0.25rem">Professional Experience</h2>
<p class="mut" style="margin-top:0;margin-bottom:1.5rem">A track record of delivering impactful enterprise solutions at global scale.</p>

<div style="display:flex;flex-direction:column;gap:1.5rem">
  <div style="background:var(--card);border:1px solid var(--card-border);border-radius:14px;padding:1.5rem;box-shadow:var(--card-shadow)">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;margin-bottom:1rem">
      <div>
        <h3 style="margin:0;font-size:1.25rem">Principal Software Engineer</h3>
        <div style="color:var(--acc);font-weight:600">Pegasystems</div>
      </div>
      <div class="tag">Sep 2021 &mdash; Present</div>
    </div>
    <ul style="margin:0;padding-left:1.25rem;color:var(--fg);line-height:1.6">
      <li><b>Classload Priming & Engine Governance:</b> Architecting low-level PEGA Engine internals, introducing classload priming to ensure pods are traffic-ready at startup and eliminate cold starts. Optimized custom class loading, passivation strategies, and high-concurrency locking.</li>
      <li><b>Distributed ID Generation & Scalability:</b> Designed a distributed ID generation system that eliminates database bottlenecks across nodes, alongside hardened database connection pools for PEGA Infinity.</li>
      <li><b>Security & Hashing Architecture:</b> Drove PII security initiatives to safeguard sensitive customer data in logs/traces and led the migration to a unified hashing framework to future-proof enterprise security.</li>
      <li><b>APIs & Operational Excellence:</b> Orchestrated high-performance RESTful APIs and modernized testing with JUnit/Mockito, reducing regression overhead by 20% and improving system uptime.</li>
    </ul>
  </div>

  <div style="background:var(--card);border:1px solid var(--card-border);border-radius:14px;padding:1.5rem;box-shadow:var(--card-shadow)">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;margin-bottom:1rem">
      <div>
        <h3 style="margin:0;font-size:1.25rem">Staff Engineer</h3>
        <div style="color:var(--acc);font-weight:600">Samsung</div>
      </div>
      <div class="tag">Jul 2011 &mdash; Sep 2021</div>
    </div>
    <ul style="margin:0;padding-left:1.25rem;color:var(--fg);line-height:1.6">
      <li><b>Security at Scale (Knox Guard):</b> Played a fundamental role in architecting Knox Guard and Knox Configure, deploying system-level MDM security policies to millions of global devices.</li>
      <li><b>Patented Innovations & R&D:</b> Led proof-of-concept initiatives in mobile security and system optimization, translating R&D efforts into patented innovations for global Samsung variants.</li>
      <li><b>Technical Diplomacy:</b> Coordinated complex requirements between international R&D centers, ensuring feature parity across global markets while maintaining strict performance benchmarks.</li>
      <li><b>Agile Automation:</b> Built custom integration testing harnesses that accelerated the transition to Agile delivery within the Samsung mobile ecosystem.</li>
    </ul>
  </div>
</div>
</section>"""

    comp_html = """<section style="margin-top:3rem">
<h2 style="font-size:1.75rem;margin-bottom:0.25rem">Core Competencies</h2>
<p class="mut" style="margin-top:0;margin-bottom:1.5rem">Technical domain expertise extracted from professional engineering experience.</p>

<div class="grid">
  <div class="card">
    <div class="card-title">⚡ Core Systems & JVM</div>
    <p>Java (Expert), Kotlin, JVM Internals, Class Loading, High-Concurrency Locking, Passivation Strategy</p>
  </div>
  <div class="card">
    <div class="card-title">🔒 Mobile Security & MDM</div>
    <p>Android SDK, Samsung Knox, Device Policy Enforcement, Biometrics, Kiosk Architecture</p>
  </div>
  <div class="card">
    <div class="card-title">☁️ Backend & Infrastructure</div>
    <p>Spring Boot, PEGA Infinity, Apache Kafka, Docker & Kubernetes, RESTful APIs</p>
  </div>
  <div class="card">
    <div class="card-title">💾 Database & Storage</div>
    <p>PostgreSQL, Oracle, SQL Server, Connection Pooling, HikariCP, Resource Management</p>
  </div>
  <div class="card">
    <div class="card-title">🔬 Testing & CI/CD DevOps</div>
    <p>JUnit & Mockito, UI Automator, Git & Jenkins, Gradle & Maven, CI/CD Pipelines</p>
  </div>
</div>
</section>"""

    body = hero_html + exp_html + comp_html
    body += "<section style='margin-top:3rem'><h2 style='font-size:1.75rem;margin-bottom:0.25rem'>Featured Software & Open Source Projects</h2><p class='mut' style='margin-top:0;margin-bottom:1.5rem'>A portfolio of apps, open-source libraries, and tools built to solve specific platform engineering bottlenecks.</p>"
    for key, title in (("app", "Android Applications"), ("library", "Libraries & SDKs"), ("other", "Enterprise Systems & Tools")):
        if sections[key]:
            body += f"<h3 style='margin-top:2rem;font-size:1.35rem'>{title}</h3><div class='grid'>{''.join(sections[key])}</div>"
    body += "</section>"

    site.write("index.html", site.page(cfg.get("name", "Home"), body, cfg.get("tagline", "")))

    site.write("api/catalog.json", json.dumps({
        "projects": [p for p, _ in projects],
        "latest": {k: v[0] for k, v in by_app.items()}}, indent=2))
    print(f"built {len(projects)} projects, {len(manifests)} releases -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
