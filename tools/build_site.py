#!/usr/bin/env python3
"""Zero-cost static site generator for the app hub.

Inputs : catalog/site.json, catalog/projects/<id>/{project.json,privacy.md,assets/*}, static/*
         + release manifests (manifest.json assets) from this repo's GitHub Releases.
Outputs: <out>/index.html, apps/<id>/, libs/<id>/, api/catalog.json, style.css

Usage  : python tools/build_site.py --out dist                 (CI: reads Releases via API)
         python tools/build_site.py --out dist --fixture tools/fixtures/manifests.sample.json   (offline)
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CATALOG = ROOT / "catalog"

from tools.builder.utils import esc, get_project_titles, get_project_category_badge
from tools.builder.github_api import fetch_manifests
from tools.builder.styles import CSS
from tools.builder.renderers import Site, render_project, render_profile_sections


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
        manifests = fetch_manifests(os.environ.get("HUB_REPO", "ervivekumrao/ervivekumrao.github.io"), os.environ.get("GITHUB_TOKEN"))
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

        main_title, sub_title = get_project_titles(p)
        cat_badge = get_project_category_badge(p)

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

    # Load catalog profile and experience metadata
    profile = json.loads((CATALOG / "profile.json").read_text(encoding="utf-8")) if (CATALOG / "profile.json").exists() else {}
    experience = json.loads((CATALOG / "experience.json").read_text(encoding="utf-8")) if (CATALOG / "experience.json").exists() else {}

    body = render_profile_sections(site, profile, experience)
    body += "<section style='margin-top:3rem'><h2 style='font-size:1.75rem;margin-bottom:0.25rem'>Featured Software & Open Source Projects</h2><p class='mut' style='margin-top:0;margin-bottom:1.5rem'>A portfolio of apps, open-source libraries, and tools built to solve specific platform engineering bottlenecks.</p>"
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
