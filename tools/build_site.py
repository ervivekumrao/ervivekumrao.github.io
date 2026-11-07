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
main,header>div{max-width:1080px;margin:0 auto;padding:1.5rem 1rem}
header{border-bottom:1px solid var(--line);background:var(--card);backdrop-filter:blur(8px);position:sticky;top:0;z-index:100}
header>div{display:flex;align-items:center;justify-content:space-between;padding:.75rem 1rem}
.nav-brand-home{display:inline-flex;align-items:center;justify-content:center;width:38px;height:38px;border-radius:10px;background:var(--tag-bg);border:1px solid var(--card-border);color:var(--fg);transition:all .15s ease;text-decoration:none!important}
.nav-brand-home:hover{background:var(--acc);color:#ffffff!important;border-color:var(--acc)}

.theme-switch{background:transparent;border:none;padding:0;cursor:pointer;display:inline-flex;align-items:center;outline:none;user-select:none;-webkit-tap-highlight-color:transparent}
.switch-track{position:relative;width:64px;height:32px;border-radius:99px;background:#bae6fd;border:2px solid #7dd3fc;box-shadow:inset 0 2px 4px rgba(0,0,0,0.12);display:flex;align-items:center;padding:3px;transition:background-color .35s ease,border-color .35s ease,box-shadow .35s ease}
[data-theme="dark"] .switch-track{background:#0f172a;border-color:#1e293b;box-shadow:inset 0 2px 6px rgba(0,0,0,0.5)}
.switch-knob{position:absolute;top:2px;left:2px;width:24px;height:24px;border-radius:50%;background:#334155;box-shadow:0 2px 6px rgba(0,0,0,0.25);display:flex;align-items:center;justify-content:center;transform:translateX(32px);transition:transform .35s cubic-bezier(0.34,1.56,0.64,1),background-color .35s ease,box-shadow .35s ease}
[data-theme="dark"] .switch-knob{transform:translateX(0px);background:#1e293b;box-shadow:0 2px 6px rgba(0,0,0,0.4),0 0 10px rgba(56,189,248,0.2)}
.knob-icon{position:absolute;display:flex;align-items:center;justify-content:center;color:#ffffff;transition:opacity .25s ease,transform .35s ease}
.icon-sun{opacity:1;transform:scale(1) rotate(0deg)}
.icon-moon{opacity:0;transform:scale(0.6) rotate(-90deg)}
[data-theme="dark"] .icon-sun{opacity:0;transform:scale(0.6) rotate(90deg)}
[data-theme="dark"] .icon-moon{opacity:1;transform:scale(1) rotate(0deg);color:#38bdf8}
.theme-switch:hover .switch-track{border-color:var(--acc)}

.breadcrumb{display:flex;align-items:center;gap:.4rem;font-size:.85rem;color:var(--mut);margin-bottom:1.25rem;flex-wrap:wrap}
.breadcrumb a{color:var(--mut);text-decoration:none}.breadcrumb a:hover{color:var(--acc);text-decoration:underline}
.breadcrumb .sep{color:var(--mut);opacity:0.6;font-size:.8rem}
.breadcrumb .current{color:var(--fg);font-weight:600}

.hero-box{background:var(--card);border:1px solid var(--card-border);border-radius:16px;padding:2.5rem 2rem;margin-bottom:2.5rem;box-shadow:var(--card-shadow)}
.hero-box h1{margin:0 0 .5rem 0;font-size:2.25rem;letter-spacing:-0.03em}.hero-box p.lead{font-size:1.15rem;color:var(--mut);margin:0 0 1.5rem 0;max-width:780px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:1.25rem;margin-top:1rem}
.card,.hero-box,details,.card-box,.proj-hero-card,.proj-section,.shot-item{transition:transform .25s ease,box-shadow .25s ease,border-color .25s ease,background .25s ease}
.card:hover,.hero-box:hover,details:hover,.card-box:hover,.proj-hero-card:hover{transform:translateY(-3px);box-shadow:0 14px 30px -4px rgba(37,99,235,0.14),0 4px 12px -2px rgba(15,23,42,0.06);border-color:var(--acc)!important;background:var(--card)}
[data-theme="light"] .card:hover,[data-theme="light"] .hero-box:hover,[data-theme="light"] details:hover,[data-theme="light"] .card-box:hover,[data-theme="light"] .proj-hero-card:hover{background:#ffffff!important;border-color:var(--acc)!important;box-shadow:0 14px 30px -4px rgba(37,99,235,0.14),0 4px 12px -2px rgba(15,23,42,0.06)!important}
[data-theme="dark"] .card:hover,[data-theme="dark"] .hero-box:hover,[data-theme="dark"] details:hover,[data-theme="dark"] .card-box:hover,[data-theme="dark"] .proj-hero-card:hover{background:#182238!important;box-shadow:0 12px 32px -4px rgba(56,189,248,0.25),0 0 24px 0 rgba(56,189,248,0.15)!important;border-color:#38bdf8!important}

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
.app-badge-ver{font-size:0.7rem;font-weight:600;padding:0.18rem 0.5rem;border-radius:20px;background:rgba(16,185,129,0.1);color:#059669;border:1px solid rgba(16,185,129,0.25);white-space:nowrap}
[data-theme="dark"] .app-badge-ver{background:rgba(52,211,153,0.12);color:#34d399;border-color:rgba(52,211,153,0.3)}
.app-badge-open{font-size:0.7rem;font-weight:600;padding:0.18rem 0.5rem;border-radius:20px;background:rgba(99,102,241,0.1);color:#6366f1;border:1px solid rgba(99,102,241,0.25);white-space:nowrap}
[data-theme="dark"] .app-badge-open{background:rgba(129,140,248,0.12);color:#818cf8;border-color:rgba(129,140,248,0.3)}

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

/* Project Detail Page Elements */
.proj-hero-card{background:var(--card);border:1px solid var(--card-border);border-radius:18px;padding:2rem;margin-bottom:2rem;box-shadow:var(--card-shadow)}
.proj-hero-top{display:flex;gap:1.5rem;align-items:flex-start;flex-wrap:wrap}
.proj-icon-wrapper{width:80px;height:80px;border-radius:18px;background:var(--tag-bg);border:1px solid var(--card-border);display:flex;align-items:center;justify-content:center;flex-shrink:0;box-shadow:0 4px 12px rgba(0,0,0,0.06)}
.proj-icon-wrapper img{width:60px;height:60px;object-fit:contain;border-radius:12px}
.proj-hero-info{flex:1;min-width:260px}
.proj-badges{display:flex;align-items:center;flex-wrap:wrap;gap:0.4rem;margin-bottom:0.6rem}
.proj-hero-title{font-size:2rem;font-weight:800;margin:0 0 0.2rem 0;letter-spacing:-0.02em;line-height:1.2;color:var(--fg)}
.proj-hero-subtitle{font-size:1rem;font-weight:600;color:var(--acc);margin-bottom:0.6rem}
.proj-hero-tagline{font-size:1.05rem;line-height:1.6;color:var(--mut);margin:0 0 1rem 0}
.proj-hero-tags{display:flex;flex-wrap:wrap;gap:0.4rem}
.proj-action-bar{display:flex;flex-wrap:wrap;gap:0.6rem;align-items:center;padding-top:1.25rem;border-top:1px dashed var(--line);margin-top:1.25rem}

.proj-section{background:var(--card);border:1px solid var(--card-border);border-radius:16px;padding:1.75rem;margin-bottom:2rem;box-shadow:var(--card-shadow)}
.proj-section-title{font-size:1.35rem;font-weight:700;margin:0 0 1.25rem 0;display:flex;align-items:center;gap:0.5rem;color:var(--fg);border-bottom:1px solid var(--line);padding-bottom:0.6rem}

.shots-container{margin-bottom:2rem}
.shots-scroll{display:flex;gap:1.25rem;overflow-x:auto;padding:0.5rem 0.25rem 1.25rem 0.25rem;scrollbar-width:thin;scroll-snap-type:x mandatory}
.shot-item{flex:0 0 auto;scroll-snap-align:start}
.shot-item:hover{transform:translateY(-4px)}
.shot-item img{height:300px;border-radius:12px;border:1px solid var(--card-border);box-shadow:var(--card-shadow);display:block;background:var(--bg)}

.download-hero{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1.25rem;margin-bottom:1.5rem}
.download-card{background:var(--tag-bg);border:1px solid var(--card-border);border-radius:14px;padding:1.25rem;display:flex;flex-direction:column;justify-content:space-between}
.qr-container{display:flex;flex-direction:column;align-items:center;text-align:center;background:var(--card);border:1px solid var(--card-border);border-radius:14px;padding:1.5rem;margin-top:1.25rem}

.install-card{background:var(--tag-bg);border:1px solid var(--card-border);border-radius:14px;padding:1.25rem;margin-bottom:1.25rem}
.install-card pre{margin:0.75rem 0 0 0;background:#0f172a;color:#f8fafc;border:1px solid #1e293b}
[data-theme="dark"] .install-card pre{background:#080c14;border-color:#1e293b}

.proj-footer-nav{display:flex;justify-content:space-between;align-items:center;padding-top:1.5rem;margin-top:2rem;border-top:1px solid var(--line);flex-wrap:wrap;gap:1rem}

.card-title{display:flex;align-items:center;margin:0 0 .5rem 0;font-size:1.15rem;font-weight:600}
.card-title img{width:32px;height:32px;border-radius:8px;margin-right:.75rem;object-fit:contain;flex-shrink:0}
.card p{color:var(--mut);font-size:.925rem;margin:0 0 1rem 0;flex-grow:1;line-height:1.5}
.card-footer{display:flex;align-items:center;justify-content:space-between;margin-top:auto;padding-top:.75rem;border-top:1px dashed var(--line)}
.mut{color:var(--mut)}.tag{display:inline-block;font-size:.75rem;font-weight:500;background:var(--tag-bg);color:var(--tag-fg);border-radius:6px;padding:.2rem .6rem;margin:0 .3rem .3rem 0}
.btn{display:inline-flex;align-items:center;justify-content:center;background:var(--acc);color:#fff!important;font-weight:600;font-size:.9rem;padding:.6rem 1.25rem;border-radius:8px;text-decoration:none!important;margin:.25rem .5rem .25rem 0;transition:background .15s ease,transform .1s ease}
.btn:hover{background:var(--acc-hover);transform:translateY(-1px)}.btn.alt{background:transparent;color:var(--acc)!important;border:1px solid var(--acc)}
.btn.alt:hover{background:var(--acc-glow)}
.btn-play{background:#10b981;border-color:#10b981}.btn-play:hover{background:#059669}
.btn-download{background:#6366f1;border-color:#6366f1}.btn-download:hover{background:#4f46e5}

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

    def page(self, title: str, body: str, desc: str = "", icon_url: str = "", breadcrumbs: list[tuple[str, str]] = None, show_home_brand: bool = False) -> str:
        s = self.cfg
        icon_href = icon_url if icon_url else self.url("favicon.svg")
        icon_type = "image/svg+xml" if icon_href.endswith(".svg") else "image/png"

        crumb_html = ""
        if breadcrumbs:
            crumbs_rendered = []
            for label, link in breadcrumbs:
                if link:
                    crumbs_rendered.append(f"<a href='{esc(link)}'>{esc(label)}</a>")
                else:
                    crumbs_rendered.append(f"<span class='current'>{esc(label)}</span>")
            crumb_html = f"<nav class='breadcrumb' aria-label='Breadcrumb'>{' <span class=\"sep\">&rsaquo;</span> '.join(crumbs_rendered)}</nav>"

        home_icon_svg = """<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>"""
        brand_html = f"""<a href="{self.url('/')}" class="nav-brand-home" aria-label="Home">{home_icon_svg}</a>""" if show_home_brand else "<div></div>"

        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<script>(function(){{var t=localStorage.getItem("theme");if(t){{document.documentElement.setAttribute("data-theme",t);}}}})();</script>
<title>{esc(title)} · {esc(s.get('name'))}</title><meta name="description" content="{esc(desc or s.get('tagline'))}">
<link rel="icon" type="{icon_type}" href="{icon_href}">
<link rel="apple-touch-icon" href="{icon_href}">
<link rel="stylesheet" href="{self.url('style.css')}"></head><body>
<header>
  <div>
    {brand_html}
    <button id="theme-toggle" class="theme-switch" aria-label="Toggle dark/light theme" type="button">
      <span class="switch-track">
        <span class="switch-knob">
          <span class="knob-icon icon-sun">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="4"></circle>
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"></path>
            </svg>
          </span>
          <span class="knob-icon icon-moon">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
            </svg>
          </span>
        </span>
      </span>
    </button>
  </div>
</header>
<main>
{crumb_html}
{body}
</main>
<script>
(function(){{
  var btn = document.getElementById("theme-toggle");
  if(!btn) return;
  function getTheme(){{
    var d = document.documentElement.getAttribute("data-theme");
    if(d) return d;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }}
  btn.addEventListener("click", function(){{
    var current = getTheme();
    var next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("theme", next);
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
        return """
<section class="proj-section">
  <h2 class="proj-section-title">📲 Download &amp; Releases</h2>
  <p class="mut" style="margin:0">No binary release has been published to GitHub Releases yet. You can inspect the source code or install via Google Play above.</p>
</section>
"""
    m = versions[0]
    h = [
        f"""
<section class="proj-section">
  <h2 class="proj-section-title">📲 Download &amp; Releases</h2>
  <div class="download-hero">
    <div class="download-card">
      <div>
        <div style="font-size:0.82rem;font-weight:600;color:var(--mut);text-transform:uppercase;letter-spacing:0.5px">Latest Stable Build</div>
        <div style="font-size:1.75rem;font-weight:800;color:var(--fg);margin:0.25rem 0">v{esc(m['version_name'])}</div>
        <div style="font-size:0.88rem;color:var(--mut)">Size: <strong>{human_size(m['size_bytes'])}</strong> &bull; Min Android: <strong>API {esc(m['min_sdk'])}+</strong></div>
      </div>
      <div style="margin-top:1.25rem;display:flex;gap:0.5rem;flex-wrap:wrap">
        <a class='btn btn-download' href='{esc(m['url_latest'])}'>⚡ Download APK (latest)</a>
        <a class='btn alt' href='{esc(m['url_versioned'])}'>Download v{esc(m['version_name'])}</a>
      </div>
    </div>
    
    <div class="download-card">
      <div style="font-size:0.82rem;font-weight:600;color:var(--mut);text-transform:uppercase;letter-spacing:0.5px">Cryptographic Integrity</div>
      <div style="font-size:0.82rem;margin-top:0.5rem;color:var(--mut)">
        <strong>Binary SHA-256:</strong><br>
        <code style="display:block;word-break:break-all;margin-top:0.2rem;font-size:0.75rem">{esc(m['sha256'])}</code>
      </div>
      <div style="font-size:0.82rem;margin-top:0.5rem;color:var(--mut)">
        <strong>Signing Certificate SHA-256:</strong><br>
        <code style="display:block;word-break:break-all;margin-top:0.2rem;font-size:0.75rem">{esc(m['cert_sha256_hex'])}</code>
      </div>
    </div>
  </div>
"""
    ]

    do = p.get("device_owner", {})
    if do.get("enabled") and do.get("admin_component"):
        payload = json.dumps(enrollment_payload(p, m), separators=(",", ":"))
        qr_svg_html = ""
        if segno:
            qr = segno.make(payload, error="l")
            svg = qr.svg_inline(scale=6, border=2)
            qr_svg_html = f"<div class='qr' style='margin:1rem 0'>{svg}</div>"
        
        h.append(f"""
  <div class="qr-container">
    <h3 style="margin:0 0 0.5rem 0;font-size:1.2rem">🛡️ Device-Owner (DPM) Enterprise Provisioning QR</h3>
    <p class="mut" style="font-size:0.9rem;max-width:600px;margin:0 0 0.5rem 0">
      <strong>Factory-Reset Enrollment:</strong> Power on factory-reset Android device. Tap the welcome screen 6 times to trigger QR scanner, then scan code below. Always installs the latest signed build.
    </p>
    {qr_svg_html}
    <details style="width:100%;max-width:640px;margin-top:0.75rem;text-align:left"><summary style="cursor:pointer;font-weight:600;color:var(--acc);font-size:0.85rem">View Provisioning JSON Payload</summary><pre style="margin-top:0.5rem;font-size:0.75rem;white-space:pre-wrap;word-break:break-all">{esc(payload)}</pre></details>
  </div>
""")

    rows = "".join(f"<tr><td><strong>v{esc(v['version_name'])}</strong></td><td>{esc(v['released_at'][:10])}</td>"
                   f"<td><a class='btn alt' style='padding:0.25rem 0.6rem;font-size:0.78rem' href='{esc(v['url_versioned'])}'>Download APK</a></td></tr>" for v in versions[:15])
    h.append(f"""
  <h3 style="margin:1.75rem 0 0.75rem 0;font-size:1.15rem">Release History</h3>
  <div class='wrap'><table><thead><tr><th>Version</th><th>Release Date</th><th>File Link</th></tr></thead><tbody>{rows}</tbody></table></div>
</section>
""")
    return "".join(h)



def render_project(site: Site, p: dict, versions: list[dict], root: Path):
    kind = p.get("type", "app")
    pid = p["id"]

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

    if kind == "app":
        cat_badge = "📱 Android App"
        cat_name = "Apps"
    elif kind == "library":
        cat_badge = "📦 Android SDK"
        cat_name = "Libraries & SDKs"
    else:
        cat_name = "Tools & Systems"
        if pid == "agenticinventory":
            cat_badge = "⚡ Microservices & AI"
        elif pid == "spindb":
            cat_badge = "🛠️ Developer CLI"
        elif pid == "jitforge":
            cat_badge = "⚡ JVM JIT Engine"
        elif pid == "tomcatvault":
            cat_badge = "🔒 Cryptographic Vault"
        else:
            cat_badge = "⚙️ System Utility"

    do = p.get("device_owner", {})
    is_dpm = do.get("enabled", False)
    dpm_badge_html = "<span class='app-badge-dpm'>🛡️ Device Owner (DPM)</span>" if is_dpm else ""

    assets_dir = root / "assets"
    out_assets_dir = site.out / pid / "assets"

    if assets_dir.is_dir():
        shutil.copytree(assets_dir, out_assets_dir, dirs_exist_ok=True)

    tab_icon_url = ""
    icon_hdr = ""

    if (assets_dir / "icon.svg").exists():
        tab_icon_url = site.url(f"{pid}/assets/icon.svg")
        icon_hdr = f"<img class='proj-icon-img' style='width:60px;height:60px;object-fit:contain;border-radius:12px' src='{tab_icon_url}' alt='{esc(main_title)} icon'>"
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
        icon_hdr = f"<img class='proj-icon-img' style='width:60px;height:60px;object-fit:contain;border-radius:12px' src='{tab_icon_url}' alt='{esc(main_title)} icon'>"

    tags_html = "".join(f"<span class='tag'>{esc(t)}</span>" for t in p.get("tags", []))

    links = []
    if p.get("play_store_url"):
        links.append(f"<a class='btn btn-play' href='{esc(p['play_store_url'])}' target='_blank' rel='noopener noreferrer'>Get it on Google Play &nearr;</a>")
    if versions and versions[0].get("url_latest"):
        links.append(f"<a class='btn btn-download' href='{esc(versions[0]['url_latest'])}'>⚡ Download APK (v{esc(versions[0]['version_name'])})</a>")
    if p.get("visibility") == "public" and p.get("repo"):
        links.append(f"<a class='btn alt' href='https://github.com/{esc(p['repo'])}' target='_blank' rel='noopener noreferrer'>View Source Code &nearr;</a>")
    if p.get("library", {}).get("docs_url"):
        links.append(f"<a class='btn alt' href='{esc(p['library']['docs_url'])}' target='_blank' rel='noopener noreferrer'>API Documentation &nearr;</a>")
    if (root / "license.md").exists():
        links.append(f"<a class='btn alt' href='{site.url(f'{pid}/license/')}'>License Information</a>")
    if (root / "privacy.md").exists():
        links.append(f"<a class='btn alt' href='{site.url(f'{pid}/privacy/')}'>Privacy Policy</a>")

    subtitle_html = f"<div class='proj-hero-subtitle'>{esc(sub_title)}</div>" if sub_title else ""
    version_badge = f"<span class='app-badge-ver'>v{esc(versions[0]['version_name'])}</span>" if versions else ""
    visibility_badge = "<span class='app-badge-open'>Open Source</span>" if p.get("visibility") == "public" else ""

    hero_html = f"""
<div class="proj-hero-card">
  <div class="proj-hero-top">
    <div class="proj-icon-wrapper">
      {icon_hdr}
    </div>
    <div class="proj-hero-info">
      <div class="proj-badges">
        <span class="app-badge-cat">{esc(cat_badge)}</span>
        {dpm_badge_html}
        {version_badge}
        {visibility_badge}
      </div>
      <h1 class="proj-hero-title">{esc(main_title)}</h1>
      {subtitle_html}
      <p class="proj-hero-tagline">{esc(p.get('tagline'))}</p>
      <div class="proj-hero-tags">{tags_html}</div>
    </div>
  </div>
  <div class="proj-action-bar">
    {''.join(links)}
  </div>
</div>
"""

    screenshots = p.get("screenshots", [])
    shots_section = ""
    if screenshots:
        shot_imgs = "".join(
            f"<div class='shot-item'><img loading='lazy' alt='{esc(main_title)} visual preview' src='{site.url(f'{pid}/assets/{s}')}'></div>"
            for s in screenshots
        )
        shots_section = f"""
<section class="proj-section shots-container">
  <h2 class="proj-section-title">🖼️ Visual Showcase &amp; Highlights</h2>
  <div class="shots-scroll">
    {shot_imgs}
  </div>
</section>
"""

    desc_content = md_to_html(p.get("description", ""))
    desc_section = f"""
<section class="proj-section">
  {desc_content}
</section>
"""

    extra_section = ""
    if kind == "app":
        extra_section = render_download(site, p, versions)
    elif kind == "library":
        lib = p.get("library", {})
        jit = lib.get("jitpack", "")
        ver = lib.get("latest_version", "TAG")
        extra_section = f"""
<section class="proj-section">
  <h2 class="proj-section-title">📦 Library Installation &amp; Setup</h2>
  <div class="install-card">
    <h3 style="margin:0 0 0.5rem 0;font-size:1.1rem">1. Add JitPack Repository</h3>
    <p style="color:var(--mut);font-size:0.9rem;margin:0 0 0.5rem 0">Add JitPack to your <code>settings.gradle.kts</code> or root <code>build.gradle</code> file:</p>
    <pre><code>dependencyResolutionManagement {{
    repositories {{
        mavenCentral()
        maven {{ url = uri("https://jitpack.io") }}
    }}
}}</code></pre>
  </div>

  <div class="install-card" style="margin-bottom:0">
    <h3 style="margin:0 0 0.5rem 0;font-size:1.1rem">2. Add Gradle Dependency</h3>
    <p style="color:var(--mut);font-size:0.9rem;margin:0 0 0.5rem 0">Add the dependency to your app-level <code>build.gradle.kts</code>:</p>
    <pre><code>dependencies {{
    implementation("{esc(jit)}:{esc(ver)}")
}}</code></pre>
  </div>
</section>
"""
    else:
        repo = p.get("repo", "")
        repo_url = f"https://github.com/{esc(repo)}" if repo else ""
        repo_btn = f"<a class='btn alt' href='{repo_url}' target='_blank'>View Repository on GitHub &nearr;</a>" if repo_url else ""
        extra_section = f"""
<section class="proj-section">
  <h2 class="proj-section-title">⚡ Developer Quickstart &amp; Source Access</h2>
  <div class="install-card" style="margin-bottom:0">
    <p style="color:var(--mut);font-size:0.95rem;line-height:1.6;margin:0 0 1rem 0">
      This enterprise system tool is fully configured for cloud-native containerized execution (Podman, Docker, Helm) and local development workflows.
    </p>
    <div>
      {repo_btn}
    </div>
  </div>
</section>
"""

    footer_nav = f"""
<div class="proj-footer-nav" style="justify-content:flex-end">
  <a href="#" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}}); return false;" class="btn alt">&uarr; Back to Top</a>
</div>
"""

    body = hero_html + shots_section + desc_section + extra_section + footer_nav

    site.write(f"{pid}/index.html", site.page(p["name"], body, p.get("tagline", ""), icon_url=tab_icon_url, show_home_brand=False))

    if (root / "license.md").exists():
        lic_body = f"""
<div class="proj-hero-card" style="margin-bottom:1.5rem">
  <h1 class="proj-hero-title">{esc(main_title)}</h1>
  <div class="proj-hero-subtitle">License Information &amp; Copyright Notice</div>
</div>
<section class="proj-section">
  {md_to_html((root / "license.md").read_text(encoding="utf-8"))}
</section>
<div class="proj-footer-nav">
  <a href="{site.url(f'{pid}/')}" class="btn alt">&larr; Back to {esc(main_title)} Page</a>
  <a href="#" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}}); return false;" class="btn alt">&uarr; Back to Top</a>
</div>
"""
        lic_breadcrumbs = [
            (main_title, site.url(f"{pid}/")),
            ("License Information", "")
        ]
        site.write(f"{pid}/license/index.html", site.page(f"{p['name']} License Information", lic_body, icon_url=tab_icon_url, breadcrumbs=lic_breadcrumbs, show_home_brand=False))

    if (root / "privacy.md").exists():
        priv_body = f"""
<div class="proj-hero-card" style="margin-bottom:1.5rem">
  <h1 class="proj-hero-title">{esc(main_title)}</h1>
  <div class="proj-hero-subtitle">Privacy Policy &amp; Security Compliance</div>
</div>
<section class="proj-section">
  {md_to_html((root / "privacy.md").read_text(encoding="utf-8"))}
</section>
<div class="proj-footer-nav">
  <a href="{site.url(f'{pid}/')}" class="btn alt">&larr; Back to {esc(main_title)} Page</a>
  <a href="#" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}}); return false;" class="btn alt">&uarr; Back to Top</a>
</div>
"""
        priv_breadcrumbs = [
            (main_title, site.url(f"{pid}/")),
            ("Privacy Policy", "")
        ]
        site.write(f"{pid}/privacy/index.html", site.page(f"{p['name']} Privacy Policy", priv_body, icon_url=tab_icon_url, breadcrumbs=priv_breadcrumbs, show_home_brand=False))



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

    site.write("index.html", site.page(cfg.get("name", "Home"), body, cfg.get("tagline", ""), show_home_brand=True))

    site.write("api/catalog.json", json.dumps({
        "projects": [p for p, _ in projects],
        "latest": {k: v[0] for k, v in by_app.items()}}, indent=2))
    print(f"built {len(projects)} projects, {len(manifests)} releases -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
