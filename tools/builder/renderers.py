"""HTML Page, Component, and Project Rendering Logic."""
from __future__ import annotations
import base64
import json
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from tools.builder.utils import esc, human_size, md_to_html, get_project_titles, get_project_category_badge

try:
    import segno
except ImportError:
    segno = None


def enrollment_payload(p: dict, m: dict) -> dict:
    """Generates the enterprise DPM provisioning payload for Android Device Owner enrollment."""
    do = p.get("device_owner", {})
    return {
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME": do["admin_component"],
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_PACKAGE_DOWNLOAD_LOCATION": m["url_latest"],
        "android.app.extra.PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM": m["cert_sha256_b64url"],
    }


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

    def page(self, title: str, body: str, desc: str = "", icon_url: str = "", breadcrumbs: Optional[list] = None, show_home_brand: bool = False) -> str:
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
<script>(function(){{var t;try{{t=localStorage.getItem("theme");}}catch(e){{}}if(!t){{t="dark";}}document.documentElement.setAttribute("data-theme",t);}})();</script>
<title>{esc(title)} · {esc(s.get('name'))}</title><meta name="description" content="{esc(desc or s.get('tagline'))}">
<link rel="icon" type="{icon_type}" href="{icon_href}">
<link rel="apple-touch-icon" href="{icon_href}">
<link rel="stylesheet" href="{self.url('style.css')}"></head><body>
<header>
  <div>
    {brand_html}
    <button id="theme-toggle" class="theme-switch" aria-label="Toggle dark/light theme" type="button">
      <span class="switch-track">
        <span class="track-icon track-sun">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="4"></circle>
            <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"></path>
          </svg>
        </span>
        <span class="track-icon track-moon">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
          </svg>
        </span>
        <span class="switch-knob">
          <svg class="icon-sun" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="4"></circle>
            <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"></path>
          </svg>
          <svg class="icon-moon" viewBox="0 0 24 24" width="13" height="13" fill="currentColor">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
          </svg>
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
  var mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

  function getTheme(){{
    var d = document.documentElement.getAttribute("data-theme");
    if(d === "dark" || d === "light") return d;
    try{{
      var t = localStorage.getItem("theme");
      if(t) return t;
    }}catch(e){{}}
    return mediaQuery.matches ? "dark" : "light";
  }}

  function setTheme(next){{
    document.documentElement.setAttribute("data-theme", next);
    try{{
      localStorage.setItem("theme", next);
    }}catch(e){{}}
  }}

  if(btn){{
    btn.addEventListener("click", function(){{
      var current = getTheme();
      var next = current === "dark" ? "light" : "dark";
      setTheme(next);
    }});
  }}

  if(mediaQuery && mediaQuery.addEventListener){{
    mediaQuery.addEventListener("change", function(e){{
      var hasCustom = false;
      try{{
        hasCustom = !!localStorage.getItem("theme");
      }}catch(err){{}}
      if(!hasCustom){{
        setTheme(e.matches ? "dark" : "light");
      }}
    }});
  }}
}})();
</script>
</body></html>"""


def render_download(_site: Site, p: dict, versions: list[dict]) -> str:
    """Renders the download section, binary checksums, and DPM provisioning QR code for app pages."""
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
    """Renders a complete project detail page (index.html, license/index.html, privacy/index.html)."""
    kind = p.get("type", "app")
    pid = p["id"]

    main_title, sub_title = get_project_titles(p)
    cat_badge = get_project_category_badge(p)

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


def render_profile_sections(site: Site, profile: dict, experience: dict) -> str:
    """Renders the portfolio home page Hero box, Professional Experience, and Core Competencies HTML sections."""
    profile_url = site.url(profile.get("profile_image", "profile.jpg"))

    social_btns = []
    for link in profile.get("social_links", []):
        btn_class = "btn" if link.get("primary") else "btn alt"
        target = " target='_blank'" if link["url"].startswith("http") else ""
        social_btns.append(f"<a href='{esc(link['url'])}' class='{btn_class}'{target}>{esc(link['label'])}</a>")

    stats_html = []
    for stat in profile.get("stats", []):
        stats_html.append(
            f"<div>"
            f"  <div style='font-size:1.75rem;font-weight:700;color:var(--acc)'>{esc(stat['value'])}</div>"
            f"  <div style='font-size:0.85rem;color:var(--mut);font-weight:500'>{esc(stat['label'])}</div>"
            f"</div>"
        )

    hero_html = f"""<div class="hero-box">
<div style="display:flex;gap:2rem;align-items:center;flex-wrap:wrap">
  <div style="flex:1;min-width:280px">
    <div style="display:inline-flex;align-items:center;background:var(--tag-bg);color:var(--tag-fg);padding:0.3rem 0.8rem;border-radius:99px;font-size:0.85rem;font-weight:500;margin-bottom:1rem">
      <span style="width:8px;height:8px;background:#10b981;border-radius:50%;display:inline-block;margin-right:0.5rem"></span>
      {esc(profile.get('status_badge', 'Available for new opportunities'))}
    </div>
    <h1 style="margin:0 0 0.75rem 0;font-size:2.5rem;letter-spacing:-0.03em">{esc(profile.get('headline', "Hi, I'm Vivek Umrao."))}</h1>
    <p class="lead" style="font-size:1.1rem;line-height:1.65;color:var(--mut);margin-bottom:1.5rem">
      <em>{esc(profile.get('quote', ''))}</em> {esc(profile.get('summary', ''))}
    </p>
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap">
      {''.join(social_btns)}
    </div>
  </div>
  <div style="flex-shrink:0">
    <img src="{profile_url}" alt="{esc(profile.get('name', 'Vivek Umrao'))}" style="width:160px;height:160px;border-radius:50%;object-fit:cover;border:3px solid var(--card-border);box-shadow:var(--card-shadow)">
  </div>
</div>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-top:2rem;padding-top:1.5rem;border-top:1px solid var(--line)">
  {''.join(stats_html)}
</div>
</div>"""

    role_cards = []
    for role in experience.get("roles", []):
        title_sub_html = f" <span style='font-size:0.95rem;font-weight:500;color:var(--mut)'>{esc(role['title_sub'])}</span>" if role.get("title_sub") else ""
        note_html = f"<div class='exp-note'>{esc(role['note'])}</div>" if role.get("note") else ""
        bullets = "".join(f"<li>{bullet}</li>" for bullet in role.get("highlights", []))
        role_cards.append(
            f"<div class='exp-card'>"
            f"  <div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.5rem'>"
            f"    <div>"
            f"      <h3 style='margin:0;font-size:1.25rem;font-weight:700'>{esc(role['title'])}{title_sub_html}</h3>"
            f"      <div style='color:var(--acc);font-weight:600;font-size:1rem;margin-top:0.15rem'>{esc(role['company'])}</div>"
            f"    </div>"
            f"    <div class='tag' style='font-weight:600'>{esc(role['period'])}</div>"
            f"  </div>"
            f"  {note_html}"
            f"  <ul class='exp-list'>{bullets}</ul>"
            f"</div>"
        )

    exp_html = f"""<section style="margin-top:3.5rem">
<h2 style="font-size:1.75rem;margin-bottom:0.25rem">Professional Experience</h2>
<p class="mut" style="margin-top:0;margin-bottom:1.5rem">A 15+ year track record of architecting JVM internals, mobile security platforms, and enterprise solutions at global scale.</p>

<div style="display:flex;flex-direction:column;gap:1.5rem">
  {''.join(role_cards)}
</div>
</section>"""

    comp_cards = []
    for comp in experience.get("competencies", []):
        chips_html = []
        for chip in comp.get("chips", []):
            css_cls = "comp-chip highlight" if chip.get("highlight") else "comp-chip"
            chips_html.append(f"<span class='{css_cls}'>{esc(chip['name'])}</span>")
        comp_cards.append(
            f"<div class='comp-card'>"
            f"  <div class='comp-header'>"
            f"    <div class='comp-title'>"
            f"      <span>{esc(comp['icon'])} {esc(comp['category'])}</span>"
            f"      <span class='comp-count'>{esc(comp['count_label'])}</span>"
            f"    </div>"
            f"  </div>"
            f"  <div class='comp-chips'>{''.join(chips_html)}</div>"
            f"</div>"
        )

    comp_html = f"""<section style="margin-top:3.5rem">
<h2 style="font-size:1.75rem;margin-bottom:0.25rem">Core Competencies &amp; Technical Skills</h2>
<p class="mut" style="margin-top:0;margin-bottom:1.5rem">Systematic domain expertise, runtime architectures, and enterprise technologies from 15+ years of systems engineering.</p>

<div class="comp-grid">
  {''.join(comp_cards)}
</div>
</section>"""

    return hero_html + exp_html + comp_html

