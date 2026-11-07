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
    if _md:
        return _md.markdown(text, extensions=["extra"])
    if text.strip().startswith("<"):
        return text
    return f"<pre>{esc(text)}</pre>"


CSS = """
:root{--bg:#f8fafc;--fg:#0f172a;--mut:#64748b;--card:#ffffff;--card-border:#e2e8f0;--card-shadow:0 4px 14px -2px rgba(0,0,0,0.06);--line:#e2e8f0;--acc:#2563eb;--acc-hover:#1d4ed8;--acc-glow:rgba(37,99,235,0.12);--tag-bg:#f1f5f9;--tag-fg:#334155}
@media(prefers-color-scheme:dark){:root{--bg:#0b0f19;--fg:#f8fafc;--mut:#94a3b8;--card:#131b2e;--card-border:#1e293b;--card-shadow:0 4px 20px -2px rgba(0,0,0,0.35);--line:#1e293b;--acc:#38bdf8;--acc-hover:#0284c7;--acc-glow:rgba(56,189,248,0.2);--tag-bg:#1e293b;--tag-fg:#cbd5e1}}
[data-theme="light"]{--bg:#f8fafc!important;--fg:#0f172a!important;--mut:#64748b!important;--card:#ffffff!important;--card-border:#e2e8f0!important;--card-shadow:0 4px 14px -2px rgba(0,0,0,0.06)!important;--line:#e2e8f0!important;--acc:#2563eb!important;--acc-hover:#1d4ed8!important;--acc-glow:rgba(37,99,235,0.12)!important;--tag-bg:#f1f5f9!important;--tag-fg:#334155!important}
[data-theme="dark"]{--bg:#0b0f19!important;--fg:#f8fafc!important;--mut:#94a3b8!important;--card:#131b2e!important;--card-border:#1e293b!important;--card-shadow:0 4px 20px -2px rgba(0,0,0,0.35)!important;--line:#1e293b!important;--acc:#38bdf8!important;--acc-hover:#0284c7!important;--acc-glow:rgba(56,189,248,0.2)!important;--tag-bg:#1e293b!important;--tag-fg:#cbd5e1!important}
*{box-sizing:border-box}body{margin:0;font:16px/1.6 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg);-webkit-font-smoothing:antialiased}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
main,header>div{max-width:1040px;margin:0 auto;padding:1.5rem 1rem}
header{border-bottom:1px solid var(--line);background:var(--card);backdrop-filter:blur(8px);position:sticky;top:0;z-index:100}
header>div{display:flex;align-items:center;justify-content:flex-end;padding:.75rem 1rem}
.theme-btn{background:transparent;border:1px solid var(--card-border);color:var(--fg);padding:.35rem .75rem;border-radius:8px;cursor:pointer;font-size:.85rem;font-weight:500;display:inline-flex;align-items:center;gap:.4rem;transition:background .15s ease,border-color .15s ease}
.theme-btn:hover{background:var(--tag-bg);border-color:var(--acc)}
.hero-box{background:var(--card);border:1px solid var(--card-border);border-radius:16px;padding:2.5rem 2rem;margin-bottom:2.5rem;box-shadow:var(--card-shadow)}
.hero-box h1{margin:0 0 .5rem 0;font-size:2.25rem;letter-spacing:-0.03em}.hero-box p.lead{font-size:1.15rem;color:var(--mut);margin:0 0 1.5rem 0;max-width:780px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1.25rem;margin-top:1rem}
.card,.hero-box,details,.card-box{transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease,background .25s ease}
.card:hover,.hero-box:hover,details:hover,.card-box:hover{transform:translateY(-4px);box-shadow:0 14px 30px -4px rgba(37,99,235,0.14),0 4px 12px -2px rgba(15,23,42,0.06);border-color:var(--acc)!important;background:var(--card)}
[data-theme="light"] .card:hover,[data-theme="light"] .hero-box:hover,[data-theme="light"] details:hover,[data-theme="light"] .card-box:hover{background:#ffffff!important;border-color:var(--acc)!important;box-shadow:0 14px 30px -4px rgba(37,99,235,0.14),0 4px 12px -2px rgba(15,23,42,0.06)!important}
[data-theme="dark"] .card:hover,[data-theme="dark"] .hero-box:hover,[data-theme="dark"] details:hover,[data-theme="dark"] .card-box:hover{background:#182238!important;box-shadow:0 12px 32px -4px rgba(56,189,248,0.25),0 0 24px 0 rgba(56,189,248,0.15)!important;border-color:#38bdf8!important}
@media(prefers-color-scheme:dark){
  :root[data-theme="light"] .card:hover,
  :root[data-theme="light"] .hero-box:hover,
  :root[data-theme="light"] details:hover,
  :root[data-theme="light"] .card-box:hover{background:#ffffff!important;border-color:var(--acc)!important;box-shadow:0 14px 30px -4px rgba(37,99,235,0.14),0 4px 12px -2px rgba(15,23,42,0.06)!important}
  :root:not([data-theme="light"]) .card:hover,
  :root:not([data-theme="light"]) .hero-box:hover,
  :root:not([data-theme="light"]) details:hover,
  :root:not([data-theme="light"]) .card-box:hover{background:#182238!important;box-shadow:0 12px 32px -4px rgba(56,189,248,0.25),0 0 24px 0 rgba(56,189,248,0.15)!important;border-color:#38bdf8!important}
}
.card{background:var(--card);border:1px solid var(--card-border);border-radius:14px;padding:1.25rem;box-shadow:var(--card-shadow);display:flex;flex-direction:column}
.app-card{padding:1.25rem;display:flex;flex-direction:column;justify-content:space-between;height:100%}
.app-card-top{display:flex;flex-direction:column;gap:0.65rem}
.app-card-header{display:flex;align-items:flex-start;justify-content:space-between;gap:0.75rem}
.app-icon-wrapper{width:44px;height:44px;border-radius:12px;background:var(--tag-bg);border:1px solid var(--card-border);display:flex;align-items:center;justify-content:center;flex-shrink:0;box-shadow:0 2px 6px rgba(0,0,0,0.04)}
.app-icon-wrapper img{width:32px;height:32px;object-fit:contain;border-radius:6px}
.app-badges{display:flex;flex-direction:column;align-items:flex-end;gap:0.3rem}
.app-badge-cat{font-size:0.72rem;font-weight:600;padding:0.2rem 0.55rem;border-radius:20px;background:var(--tag-bg);color:var(--tag-fg);border:1px solid var(--card-border);white-space:nowrap}
.app-badge-dpm{font-size:0.7rem;font-weight:600;padding:0.18rem 0.5rem;border-radius:20px;background:rgba(37,99,235,0.1);color:var(--acc);border:1px solid rgba(37,99,235,0.25);white-space:nowrap}
[data-theme="dark"] .app-badge-dpm{background:rgba(56,189,248,0.12);color:#38bdf8;border-color:rgba(56,189,248,0.3)}
.app-title-group{margin:0}
.app-main-title{font-size:1.15rem;font-weight:700;line-height:1.3;margin:0;letter-spacing:-0.01em}
.app-main-title a{color:var(--fg);text-decoration:none}.app-main-title a:hover{color:var(--acc)}
.app-subtitle{font-size:0.82rem;font-weight:600;color:var(--acc);margin-top:0.15rem;line-height:1.35}
.app-description{color:var(--mut);font-size:0.875rem;line-height:1.5;margin:0;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.app-chips{display:flex;flex-wrap:wrap;gap:0.35rem;margin-top:0.15rem}
.app-chip{font-size:0.72rem;font-weight:500;padding:0.18rem 0.5rem;border-radius:6px;background:var(--tag-bg);color:var(--tag-fg);border:1px solid var(--card-border)}
.app-card-footer{display:flex;align-items:center;justify-content:space-between;margin-top:1rem;padding-top:0.75rem;border-top:1px dashed var(--line);gap:0.5rem}
.app-footer-left{display:flex;align-items:center;gap:0.4rem}
.app-footer-right{display:flex;align-items:center;gap:0.4rem}
.app-chip-store{display:inline-flex;align-items:center;gap:0.2rem;font-size:0.72rem;font-weight:600;padding:0.2rem 0.55rem;border-radius:6px;background:rgba(16,185,129,0.1);color:#059669!important;border:1px solid rgba(16,185,129,0.25);text-decoration:none!important;transition:all .15s ease}
.app-chip-store:hover{background:#10b981;color:#ffffff!important;border-color:#10b981;text-decoration:none!important}
[data-theme="dark"] .app-chip-store{background:rgba(52,211,153,0.12);color:#34d399!important;border-color:rgba(52,211,153,0.3)}
[data-theme="dark"] .app-chip-store:hover{background:#34d399;color:#0b0f19!important;border-color:#34d399;text-decoration:none!important}
.app-chip-open{font-size:0.72rem;font-weight:600;padding:0.2rem 0.55rem;border-radius:6px;background:rgba(99,102,241,0.1);color:#6366f1;border:1px solid rgba(99,102,241,0.25)}
[data-theme="dark"] .app-chip-open{background:rgba(129,140,248,0.12);color:#818cf8;border-color:rgba(129,140,248,0.3)}
.btn-details{display:inline-flex;align-items:center;gap:0.25rem;font-size:0.83rem;font-weight:600;color:var(--acc);padding:0.3rem 0.7rem;border-radius:6px;background:var(--tag-bg);border:1px solid var(--card-border);transition:all .15s ease}
.btn-details:hover{background:var(--acc);color:#fff!important;border-color:var(--acc);text-decoration:none}
.btn-source{display:inline-flex;align-items:center;gap:0.25rem;font-size:0.78rem;font-weight:500;color:var(--mut);padding:0.3rem 0.6rem;border-radius:6px;border:1px solid var(--card-border);transition:all .15s ease}
.btn-source:hover{color:var(--fg)!important;border-color:var(--mut);text-decoration:none}
.comp-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:1.25rem;margin-top:1rem}
.comp-card{background:var(--card);border:1px solid var(--card-border);border-radius:14px;padding:1.25rem;box-shadow:var(--card-shadow);display:flex;flex-direction:column;gap:0.75rem;transition:all .25s ease}
.comp-card:hover{transform:translateY(-3px);border-color:var(--acc);box-shadow:0 12px 28px -4px rgba(37,99,235,0.12);background:var(--card)}
[data-theme="light"] .comp-card:hover{background:#ffffff!important;border-color:var(--acc)!important}
@media(prefers-color-scheme:dark){.comp-card:hover{background:#182238!important;border-color:#38bdf8!important;box-shadow:0 12px 28px -4px rgba(56,189,248,0.25)}}
[data-theme="dark"] .comp-card:hover{background:#182238!important;border-color:#38bdf8!important;box-shadow:0 12px 28px -4px rgba(56,189,248,0.25)}
.comp-header{margin:0}
.comp-title{font-size:1.05rem;font-weight:700;color:var(--fg);display:flex;align-items:center;justify-content:space-between}
.comp-count{font-size:0.72rem;font-weight:600;padding:0.15rem 0.5rem;border-radius:12px;background:var(--tag-bg);color:var(--mut);border:1px solid var(--card-border)}
.comp-chips{display:flex;flex-wrap:wrap;gap:0.35rem}
.comp-chip{font-size:0.76rem;font-weight:500;padding:0.22rem 0.55rem;border-radius:6px;background:var(--tag-bg);color:var(--tag-fg);border:1px solid var(--card-border);transition:all .15s ease}
.comp-chip:hover{border-color:var(--acc);color:var(--acc)}
.comp-chip.highlight{background:rgba(37,99,235,0.08);color:var(--acc);border-color:rgba(37,99,235,0.25);font-weight:600}
[data-theme="dark"] .comp-chip.highlight{background:rgba(56,189,248,0.12);color:#38bdf8;border-color:rgba(56,189,248,0.3)}
.exp-card{background:var(--card);border:1px solid var(--card-border);border-radius:14px;padding:1.5rem;box-shadow:var(--card-shadow);transition:all .25s ease;position:relative}
.exp-card:hover{border-color:var(--acc);transform:translateY(-2px);box-shadow:0 10px 25px -4px rgba(37,99,235,0.12);background:var(--card)}
[data-theme="light"] .exp-card:hover{background:#ffffff!important;border-color:var(--acc)!important}
[data-theme="dark"] .exp-card:hover{background:#182238!important;border-color:#38bdf8!important}
.exp-note{font-size:0.85rem;color:var(--mut);font-style:italic;margin-bottom:1rem;padding:0.5rem 0.75rem;background:var(--tag-bg);border-left:3px solid var(--acc);border-radius:0 8px 8px 0}
.exp-list{margin:0;padding-left:1.2rem;color:var(--fg);line-height:1.65;font-size:0.925rem}
.exp-list li{margin-bottom:0.5rem}
.exp-list li:last-child{margin-bottom:0}
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
table{border-collapse:separate;border-spacing:0;width:100%;margin:1.5rem 0;border-radius:12px;overflow:hidden;border:1px solid var(--card-border);background:var(--card);box-shadow:var(--card-shadow)}
th{background:var(--tag-bg);color:var(--fg);font-weight:700;font-size:.85rem;text-transform:uppercase;letter-spacing:.5px;padding:.85rem 1rem;border-bottom:2px solid var(--line)}
td{border-bottom:1px solid var(--line);padding:.85rem 1rem;text-align:left;font-size:.925rem}
tr:last-child td{border-bottom:none}
tr:nth-child(even){background:rgba(0,0,0,0.02)}
[data-theme="dark"] tr:nth-child(even){background:rgba(255,255,255,0.02)}
tr:hover{background:var(--acc-glow)!important;transition:background .15s ease}
.badge-yes{display:inline-flex;align-items:center;gap:.3rem;font-size:.78rem;font-weight:600;background:rgba(16,185,129,0.12);color:#059669;border:1px solid rgba(16,185,129,0.3);border-radius:20px;padding:.2rem .65rem;white-space:nowrap}
[data-theme="dark"] .badge-yes{background:rgba(16,185,129,0.18);color:#34d399;border-color:rgba(52,211,153,0.35)}
.badge-no{display:inline-flex;align-items:center;gap:.3rem;font-size:.78rem;font-weight:600;background:rgba(239,68,68,0.12);color:#dc2626;border:1px solid rgba(239,68,68,0.3);border-radius:20px;padding:.2rem .65rem;white-space:nowrap}
[data-theme="dark"] .badge-no{background:rgba(239,68,68,0.18);color:#f87171;border-color:rgba(248,113,113,0.35)}
.badge-warn{display:inline-flex;align-items:center;gap:.3rem;font-size:.78rem;font-weight:600;background:rgba(245,158,11,0.12);color:#d97706;border:1px solid rgba(245,158,11,0.3);border-radius:20px;padding:.2rem .65rem;white-space:nowrap}
[data-theme="dark"] .badge-warn{background:rgba(245,158,11,0.18);color:#fbbf24;border-color:rgba(251,191,36,0.35)}
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
<header><div><button id="theme-toggle" class="theme-btn" aria-label="Toggle dark/light theme"><span id="theme-icon">☀️</span> <span id="theme-label" class="mut">Theme</span></button></div></header>
<main>{body}</main>
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
        links.append(f"<a class='btn' href='{esc(p['play_store_url'])}' target='_blank' rel='noopener noreferrer'>Get it on Google Play</a>")
    if p.get("visibility") == "public" and p.get("repo"):
        links.append(f"<a class='btn alt' href='https://github.com/{esc(p['repo'])}'>Source code</a>")
    if (root / "license.md").exists():
        links.append(f"<a class='btn alt' href='{site.url(f'{pid}/license/')}'>License information</a>")
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
    desc = md_to_html(p.get("description", ""))
    tags = "".join(f"<span class='tag'>{esc(t)}</span>" for t in p.get("tags", []))

    header_html = f"<div class='proj-header'>{icon_hdr}<div><h1 style='margin:0 0 .25rem 0'>{esc(p['name'])}</h1><p class='mut' style='font-size:1.1rem;margin:0 0 .75rem 0'>{esc(p.get('tagline'))}</p>{tags}</div></div>"
    body = f"{header_html}<div style='margin:1.5rem 0'>{desc}</div><div style='margin-bottom:2rem'>{''.join(links)}</div>"



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
    if (root / "license.md").exists():
        site.write(f"{pid}/license/index.html", site.page(f"{p['name']} License Information",
                   md_to_html((root / "license.md").read_text(encoding="utf-8")), icon_url=tab_icon_url))
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
        ptype = p.get("type", "app")
        badge = f"v{esc(versions[0]['version_name'])}" if versions else ""

        DEFAULT_SUBTITLES = {
            "studycompanion": "AI Quiz, Flashcards & TTS Tutoring",
            "officetimecounter": "Automated Attendance & Geofencing",
            "mockupmaster": "Mock Data & ADB CLI Generator",
            "timespanselectorview": "Radial & Linear Duration Picker",
            "tomcatvault": "AES-256-GCM Credential Vault",
            "jitforge": "In-Memory Bytecode JIT Engine",
            "spindb": "13 Containerized DB & Lakehouse CLI",
            "agenticinventory": "Polyglot Microservices & AI Engine",
        }

        raw_name = p['name']
        if " — " in raw_name:
            main_title, sub_title = raw_name.split(" — ", 1)
        elif " – " in raw_name:
            main_title, sub_title = raw_name.split(" – ", 1)
        else:
            main_title, sub_title = raw_name, DEFAULT_SUBTITLES.get(pid, "")

        if ptype == "app":
            cat_badge = "📱 Android App"
        elif ptype == "library":
            cat_badge = "📦 Android SDK"
        else:
            if pid == "agenticinventory":
                cat_badge = "⚡ Microservices & AI"
            elif pid == "spindb":
                cat_badge = "🛠️ Developer CLI"
            elif pid == "jitforge":
                cat_badge = "⚡ JVM JIT Engine"
            elif pid == "tomcatvault":
                cat_badge = "🔒 Cryptographic Vault"
            else:
                cat_badge = "⚙️ System Tool"

        do = p.get("device_owner", {})
        is_dpm = do.get("enabled", False)
        dpm_badge_html = "<span class='app-badge-dpm'>🛡️ Device Owner (DPM)</span>" if is_dpm else ""

        icon_card = ""
        if (root / "assets" / "icon.svg").exists():
            icon_url = site.url(f"{pid}/assets/icon.svg")
            icon_card = f"<img src='{icon_url}' alt='{esc(main_title)} icon'>"
        elif (root / "assets" / "icon.png").exists():
            icon_url = site.url(f"{pid}/assets/icon_tab.svg")
            icon_card = f"<img src='{icon_url}' alt='{esc(main_title)} icon'>"

        proj_url = site.url(f"{pid}/")

        raw_tags = p.get("tags", [])
        ignored_tags = {"android app", "android library", "system utility"}
        filtered_tags = [t for t in raw_tags if t.lower() not in ignored_tags]
        display_tags = filtered_tags[:5] if filtered_tags else raw_tags[:5]
        chips_html = "".join(f"<span class='app-chip'>{esc(t)}</span>" for t in display_tags)

        footer_left = []
        if p.get("play_store_url"):
            footer_left.append(f"<a href='{esc(p['play_store_url'])}' target='_blank' rel='noopener noreferrer' class='app-chip-store'>Google Play</a>")
        elif badge:
            footer_left.append(f"<span class='app-chip'>{badge}</span>")
        elif p.get("visibility") == "public":
            footer_left.append("<span class='app-chip-open'>Open Source</span>")

        footer_right = []
        if p.get("visibility") == "public" and p.get("repo"):
            footer_right.append(f"<a href='https://github.com/{esc(p['repo'])}' target='_blank' class='btn-source'>GitHub &nearr;</a>")
        footer_right.append(f"<a href='{proj_url}' class='btn-details'>Details &rarr;</a>")

        subtitle_html = f"<div class='app-subtitle'>{esc(sub_title)}</div>" if sub_title else ""

        card_markup = (
            f"<div class='card app-card'>"
            f"  <div class='app-card-top'>"
            f"    <div class='app-card-header'>"
            f"      <div class='app-icon-wrapper'>{icon_card}</div>"
            f"      <div class='app-badges'>"
            f"        <span class='app-badge-cat'>{esc(cat_badge)}</span>"
            f"        {dpm_badge_html}"
            f"      </div>"
            f"    </div>"
            f"    <div class='app-title-group'>"
            f"      <h3 class='app-main-title'><a href='{proj_url}'>{esc(main_title)}</a></h3>"
            f"      {subtitle_html}"
            f"    </div>"
            f"    <p class='app-description'>{esc(p.get('tagline'))}</p>"
            f"    <div class='app-chips'>{chips_html}</div>"
            f"  </div>"
            f"  <div class='app-card-footer'>"
            f"    <div class='app-footer-left'>{''.join(footer_left)}</div>"
            f"    <div class='app-footer-right'>{''.join(footer_right)}</div>"
            f"  </div>"
            f"</div>"
        )
        sections.get(ptype, sections["other"]).append(card_markup)

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
    <div style="font-size:0.85rem;color:var(--mut);font-weight:500">Years Systems Experience</div>
  </div>
  <div>
    <div style="font-size:1.75rem;font-weight:700;color:var(--acc)">100M+</div>
    <div style="font-size:0.85rem;color:var(--mut);font-weight:500">Devices Secured (Knox)</div>
  </div>
  <div>
    <div style="font-size:1.75rem;font-weight:700;color:var(--acc)">99.999%</div>
    <div style="font-size:0.85rem;color:var(--mut);font-weight:500">Platform Availability</div>
  </div>
</div>
</div>"""

    exp_html = """<section style="margin-top:3.5rem">
<h2 style="font-size:1.75rem;margin-bottom:0.25rem">Professional Experience</h2>
<p class="mut" style="margin-top:0;margin-bottom:1.5rem">A 15+ year track record of architecting JVM internals, mobile security platforms, and enterprise solutions at global scale.</p>

<div style="display:flex;flex-direction:column;gap:1.5rem">

  <div class="exp-card">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.5rem">
      <div>
        <h3 style="margin:0;font-size:1.25rem;font-weight:700">Principal Software Engineer</h3>
        <div style="color:var(--acc);font-weight:600;font-size:1rem;margin-top:0.15rem">Pegasystems</div>
      </div>
      <div class="tag" style="font-weight:600">Mar 2025 &mdash; Present</div>
    </div>
    <div class="exp-note">
      Transitioned from Cognizant Contractor to Pega FTE via negotiated management release to drive platform architecture for AU / global time zone enterprise operations.
    </div>
    <ul class="exp-list">
      <li><b>Core JVM Runtime Architecture:</b> Architected low-level Infinity Engine internals, including custom hierarchical class loaders, memory passivation algorithms, and lock-free concurrency, eliminating thread contention bottlenecks and sustaining <b>99.999% platform availability</b> across global enterprise client deployments.</li>
      <li><b>Cold-Start Elimination &amp; Priming:</b> Pioneered pre-emptive class-load priming at container startup, eliminating JVM cold-start latency spikes and enabling auto-scaled Kubernetes pods to handle peak production traffic immediately, cutting scale-up latency by <b>~85%</b>.</li>
      <li><b>3x Throughput Distributed ID Generator:</b> Architected a distributed, batch-based unique ID generation engine across multi-tenant nodes, decoupling database locks and dependency bottlenecks to achieve over <b>3x throughput gains</b> under peak concurrent workloads with zero collision risk.</li>
      <li><b>Enterprise Data Privacy &amp; PII Governance:</b> Led engineering-wide PII data governance architecture (dynamic masking, cryptographic tokenization, access policy enforcement) across distributed engine logs and telemetry traces, ensuring zero sensitive data exposure and full enterprise compliance.</li>
      <li><b>Unified Hashing Modernization:</b> Spearheaded the consolidation of fragmented legacy hashing algorithms into a centralized, extensible cryptographic library, reducing future upgrade overhead by <b>~40%</b> across distributed microservices.</li>
      <li><b>High-Performance APIs &amp; Connection Pooling:</b> Engineered robust database connection pooling (HikariCP/custom adapters) and high-throughput RESTful integration APIs, hardening database resource recycling under high-concurrency failover conditions.</li>
      <li><b>Incident Command &amp; 30% MTTR Reduction:</b> Served as Tier-3 Incident Commander and RCA lead for high-severity customer escalations; led systemic architectural remediations that slashed mean time to resolution (MTTR) by <b>30%</b> alongside 24/7 mission-critical on-call production governance.</li>
      <li><b>Engineering Multiplier &amp; Quality Modernization:</b> Chaired architectural reviews, authored technical RFCs, and modernized automated integration testing lifecycles with JUnit and Mockito, reducing regression cycles by <b>20%</b> while mentoring senior engineers on JVM memory and concurrency patterns.</li>
    </ul>
  </div>

  <div class="exp-card">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.5rem">
      <div>
        <h3 style="margin:0;font-size:1.25rem;font-weight:700">Lead Architect <span style="font-size:0.95rem;font-weight:500;color:var(--mut)">(Manager &ndash; Projects)</span></h3>
        <div style="color:var(--acc);font-weight:600;font-size:1rem;margin-top:0.15rem">Cognizant</div>
      </div>
      <div class="tag" style="font-weight:600">Sep 2021 &mdash; Mar 2025</div>
    </div>
    <div class="exp-note">
      Embedded full-time with Pegasystems as Principal Technical Lead &amp; Contractor Architecture Governance.
    </div>
    <ul class="exp-list">
      <li><b>Technical Program Delivery &amp; Architecture:</b> Directed technical architecture and engineering delivery for core engine initiatives at Pegasystems, aligning cross-functional software development, QA, and platform reliability engineering squads across global delivery centers.</li>
      <li><b>Core Engine SLA &amp; Passivation Governance:</b> Owned architectural enhancements for low-level passivation strategies, thread-pool allocation, and database connectivity, ensuring strict performance benchmark compliance and SLA adherence across multi-tenant enterprise accounts.</li>
      <li><b>CI/CD &amp; Deployment Acceleration:</b> Architected end-to-end CI/CD release pipelines and automated regression test suites, cutting release cycle times by <b>35%</b> and enforcing automated code quality gates across all contractor deliverables.</li>
      <li><b>Systemic Incident RCA &amp; 25&ndash;30% MTTR Reduction:</b> Led cross-functional incident triage and Root Cause Analysis (RCA) for critical enterprise production issues, engineering preventative runtime safeguards that reduced customer MTTR by <b>25&ndash;30%</b>.</li>
      <li><b>Developer Toolchain Modernization:</b> Drove enterprise-scale developer infrastructure modernizations, including Vagrant-to-WSL2 environment migrations and Bitbucket-to-GitHub transitions, standardizing developer workflows and slashing engineering onboarding time by <b>50%</b>.</li>
    </ul>
  </div>

  <div class="exp-card">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.5rem">
      <div>
        <h3 style="margin:0;font-size:1.25rem;font-weight:700">Staff Engineer <span style="font-size:0.95rem;font-weight:500;color:var(--mut)">(Systems &amp; Mobile Security)</span></h3>
        <div style="color:var(--acc);font-weight:600;font-size:1rem;margin-top:0.15rem">Samsung R&amp;D</div>
      </div>
      <div class="tag" style="font-weight:600">Jul 2011 &mdash; Sep 2021</div>
    </div>
    <div class="exp-note">
      Samsung Knox Platform &amp; Enterprise Mobile Security R&amp;D.
    </div>
    <ul class="exp-list">
      <li><b>Samsung Knox Security Architecture:</b> Architected and scaled core platform security frameworks (Samsung Knox Guard and Knox Configure), deploying system-level Mobile Device Management (MDM) policy enforcement, hardware attestation, and biometric authentication across <b>100M+ global devices</b>.</li>
      <li><b>Systems R&amp;D &amp; Patented Innovations:</b> Led systems R&D, OS-level security hardening, and proof-of-concept initiatives, translating novel research into patented mobile security innovations and achieving feature parity across global flagship device lineups.</li>
      <li><b>Global Cross-Region Architectural Alignment:</b> Served as principal technical liaison between South Korea R&D headquarters and international engineering teams, harmonizing technical specifications and strict performance benchmarks across <b>50+ global telecommunication carriers</b>.</li>
      <li><b>Test Automation Harness Architecture:</b> Built comprehensive multi-threaded test automation and integration testing frameworks (UI Automator, custom device harnesses), accelerating Agile delivery cycles by <b>40%</b> and elevating release stability.</li>
    </ul>
  </div>

</div>
</section>"""

    comp_html = """<section style="margin-top:3.5rem">
<h2 style="font-size:1.75rem;margin-bottom:0.25rem">Core Competencies &amp; Technical Skills</h2>
<p class="mut" style="margin-top:0;margin-bottom:1.5rem">Systematic domain expertise, runtime architectures, and enterprise technologies from 15+ years of systems engineering.</p>

<div class="comp-grid">
  <div class="comp-card">
    <div class="comp-header">
      <div class="comp-title">
        <span>⚡ Core Systems &amp; JVM</span>
        <span class="comp-count">8 Skills</span>
      </div>
    </div>
    <div class="comp-chips">
      <span class="comp-chip highlight">JVM Internals</span>
      <span class="comp-chip highlight">Custom Hierarchical Class Loaders</span>
      <span class="comp-chip">In-Memory JIT Compilation</span>
      <span class="comp-chip highlight">Java 21+ Virtual Threads (Loom)</span>
      <span class="comp-chip">Lock-Free Concurrency</span>
      <span class="comp-chip">Passivation Algorithms</span>
      <span class="comp-chip">Memory &amp; GC Pause Tuning</span>
      <span class="comp-chip">Kotlin</span>
    </div>
  </div>

  <div class="comp-card">
    <div class="comp-header">
      <div class="comp-title">
        <span>🛡️ Mobile Security &amp; MDM</span>
        <span class="comp-count">7 Skills</span>
      </div>
    </div>
    <div class="comp-chips">
      <span class="comp-chip highlight">Android SDK &amp; Frameworks</span>
      <span class="comp-chip highlight">Samsung Knox Guard &amp; Knox Configure</span>
      <span class="comp-chip highlight">Device Policy Manager (DPM MDM)</span>
      <span class="comp-chip">Hardware Attestation</span>
      <span class="comp-chip">Biometric Authentication</span>
      <span class="comp-chip">Jetpack Compose</span>
      <span class="comp-chip">Material 3 UI</span>
    </div>
  </div>

  <div class="comp-card">
    <div class="comp-header">
      <div class="comp-title">
        <span>🔐 Security &amp; Cryptography</span>
        <span class="comp-count">7 Skills</span>
      </div>
    </div>
    <div class="comp-chips">
      <span class="comp-chip highlight">AES-256-GCM Encryption</span>
      <span class="comp-chip highlight">PII Dynamic Data Masking &amp; Redaction</span>
      <span class="comp-chip">Cryptographic Tokenization</span>
      <span class="comp-chip">Unified Hashing Frameworks</span>
      <span class="comp-chip">JMX Credential Masking</span>
      <span class="comp-chip">AWS Secrets Manager</span>
      <span class="comp-chip">HashiCorp Vault</span>
    </div>
  </div>

  <div class="comp-card">
    <div class="comp-header">
      <div class="comp-title">
        <span>🌐 Distributed Systems &amp; Backend</span>
        <span class="comp-count">7 Skills</span>
      </div>
    </div>
    <div class="comp-chips">
      <span class="comp-chip highlight">Distributed Systems Architecture</span>
      <span class="comp-chip highlight">Spring Boot</span>
      <span class="comp-chip">PEGA Infinity Core Engine</span>
      <span class="comp-chip highlight">Apache Kafka Event Streaming</span>
      <span class="comp-chip">High-Throughput RESTful APIs</span>
      <span class="comp-chip highlight">3x Distributed ID Generator</span>
      <span class="comp-chip">Cold-Start Elimination &amp; Priming</span>
    </div>
  </div>

  <div class="comp-card">
    <div class="comp-header">
      <div class="comp-title">
        <span>💾 Databases &amp; Observability</span>
        <span class="comp-count">9 Skills</span>
      </div>
    </div>
    <div class="comp-chips">
      <span class="comp-chip highlight">PostgreSQL</span>
      <span class="comp-chip">Oracle</span>
      <span class="comp-chip">SQL Server</span>
      <span class="comp-chip">MySQL &amp; DB2</span>
      <span class="comp-chip highlight">Redis Multi-Tier Caching</span>
      <span class="comp-chip">pgvector AI Lakehouse</span>
      <span class="comp-chip highlight">HikariCP &amp; DBCP2 Connection Pools</span>
      <span class="comp-chip">Grafana</span>
      <span class="comp-chip">Distributed Tracing &amp; Telemetry</span>
    </div>
  </div>

  <div class="comp-card">
    <div class="comp-header">
      <div class="comp-title">
        <span>☸️ Cloud, Containers &amp; DevOps</span>
        <span class="comp-count">8 Skills</span>
      </div>
    </div>
    <div class="comp-chips">
      <span class="comp-chip highlight">Rootless Podman</span>
      <span class="comp-chip">Docker</span>
      <span class="comp-chip highlight">Kubernetes (K8s Operators)</span>
      <span class="comp-chip">Self-Healing Pod Architecture</span>
      <span class="comp-chip">Helm Charts</span>
      <span class="comp-chip">AWS &amp; GCP</span>
      <span class="comp-chip">CI/CD (Git, Jenkins)</span>
      <span class="comp-chip">Gradle &amp; Maven</span>
    </div>
  </div>

  <div class="comp-card">
    <div class="comp-header">
      <div class="comp-title">
        <span>🤖 AI &amp; Agentic Systems</span>
        <span class="comp-count">6 Skills</span>
      </div>
    </div>
    <div class="comp-chips">
      <span class="comp-chip highlight">Autonomous Multi-Agent Orchestration</span>
      <span class="comp-chip">LLM Prompt Engineering</span>
      <span class="comp-chip">Spec-Kit Framework</span>
      <span class="comp-chip">ML Intent Classification (Scikit-Learn)</span>
      <span class="comp-chip highlight">Gemini &amp; Claude Integration</span>
      <span class="comp-chip">GitHub &amp; Microsoft Copilot</span>
    </div>
  </div>

  <div class="comp-card">
    <div class="comp-header">
      <div class="comp-title">
        <span>🎯 Leadership &amp; Governance</span>
        <span class="comp-count">6 Skills</span>
      </div>
    </div>
    <div class="comp-chips">
      <span class="comp-chip highlight">Architecture Review Board (ARB)</span>
      <span class="comp-chip">RFC &amp; Technical Proposals</span>
      <span class="comp-chip highlight">Systemic RCA (30% MTTR Reduction)</span>
      <span class="comp-chip">Enterprise SLA Governance (99.999%)</span>
      <span class="comp-chip">Cross-Region R&amp;D Mentorship</span>
      <span class="comp-chip">Tier-3 Incident Command</span>
    </div>
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
