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

    def page(
        self,
        title: str,
        body: str,
        desc: str = "",
        icon_url: str = "",
        breadcrumbs: Optional[list] = None,
        show_home_brand: bool = False,
        project_info: Optional[dict] = None
    ) -> str:
        s = self.cfg
        icon_href = icon_url if icon_url else self.url("favicon.svg")
        icon_type = "image/svg+xml" if icon_href.endswith(".svg") else "image/png"

        theme_toggle_btn = """
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
      </button>"""

        if project_info:
            pid = project_info["id"]
            main_title = project_info["title"]
            p_icon = project_info.get("icon_url") or self.url("favicon.svg")
            ver_str = project_info.get("version", "")
            kind = project_info.get("kind", "app")
            has_shots = project_info.get("has_screenshots", False)
            has_priv = project_info.get("has_privacy", False)
            has_lic = project_info.get("has_license", False)
            curr_sub = project_info.get("current_subpage", "overview")

            base_proj = self.url(f"{pid}/")
            overview_href = base_proj if curr_sub != "overview" else "#overview"
            showcase_href = f"{base_proj}#showcase" if curr_sub != "overview" else "#showcase"
            details_href = f"{base_proj}#details" if curr_sub != "overview" else "#details"
            action_href = f"{base_proj}#download" if curr_sub != "overview" else "#download"
            if kind == "library":
                action_href = f"{base_proj}#installation" if curr_sub != "overview" else "#installation"
            elif kind == "other":
                action_href = f"{base_proj}#quickstart" if curr_sub != "overview" else "#quickstart"

            action_label = "Releases" if kind == "app" else ("Setup" if kind == "library" else "Quickstart")

            ver_badge_html = f"<span class='app-badge-ver'>{esc(ver_str)}</span>" if ver_str else ""
            shots_nav_html = f"<a href='{showcase_href}' class='project-nav-link'>Showcase</a>" if has_shots else ""
            priv_nav_html = f"<a href='{self.url(f'{pid}/privacy/')}' class='project-nav-link {'nav-active' if curr_sub == 'privacy' else ''}'>Privacy</a>" if has_priv else ""
            lic_nav_html = f"<a href='{self.url(f'{pid}/license/')}' class='project-nav-link {'nav-active' if curr_sub == 'license' else ''}'>License</a>" if has_lic else ""

            header_html = f"""<header class="site-header project-header">
  <div class="header-inner">
    <div class="header-left">
      <a href="{base_proj}" class="project-brand">
        <div class="project-header-icon"><img src="{p_icon}" alt="{esc(main_title)} icon"></div>
        <div class="project-header-text">
          <span class="project-header-title">{esc(main_title)}</span>
          {ver_badge_html}
        </div>
      </a>
      <nav class="project-nav" aria-label="{esc(main_title)} Navigation">
        <a href="{overview_href}" class="project-nav-link {'nav-active' if curr_sub == 'overview' else ''}">Overview</a>
        {shots_nav_html}
        <a href="{details_href}" class="project-nav-link">Details</a>
        <a href="{action_href}" class="project-nav-link">{action_label}</a>
        {priv_nav_html}
        {lic_nav_html}
      </nav>
    </div>
    <div class="header-right">
      <a href="https://github.com/ervivekumrao" target="_blank" rel="noopener noreferrer" class="dev-portfolio-badge" title="Developer GitHub Profile">
        <span class="dev-avatar-sm">VU</span>
        <span class="dev-label">Developer GitHub &nearr;</span>
      </a>
      {theme_toggle_btn}
    </div>
  </div>
</header>"""

            priv_foot = f"<a href='{self.url(f'{pid}/privacy/')}'>Privacy Policy</a>" if has_priv else ""
            lic_foot = f"<a href='{self.url(f'{pid}/license/')}'>License Information</a>" if has_lic else ""

            footer_html = f"""<footer class="site-footer project-footer">
  <div class="footer-inner">
    <div class="footer-brand">
      <div class="proj-footer-icon"><img src="{p_icon}" alt="{esc(main_title)} icon"></div>
      <div>
        <strong>{esc(main_title)}</strong> &bull; {esc(project_info.get('cat_badge', ''))}
        <div class="footer-tagline">{esc(project_info.get('tagline', ''))}</div>
      </div>
    </div>
    <div class="footer-links">
      {priv_foot}
      {lic_foot}
      <a href="https://github.com/ervivekumrao" target="_blank" rel="noopener noreferrer" class="footer-dev-link">Built by <strong>Vivek Umrao</strong> &nearr;</a>
      <a href="#" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}}); return false;" class="back-to-top">&uarr; Back to Top</a>
    </div>
  </div>
</footer>"""

        else:
            header_html = f"""<header class="site-header main-header">
  <div class="header-inner">
    <div class="header-left">
      <a href="{self.url('')}" class="portfolio-brand">
        <span class="brand-avatar">VU</span>
        <div class="brand-info">
          <span class="brand-name">{esc(s.get('name', 'Vivek Umrao'))}</span>
          <span class="brand-role">System Architect</span>
        </div>
      </a>
      <nav class="portfolio-nav" aria-label="Portfolio Navigation">
        <a href="{self.url('#overview')}" class="nav-link nav-active" data-section="overview"><span>⚡ Overview</span></a>
        <a href="{self.url('#experience')}" class="nav-link" data-section="experience"><span>Experience</span></a>
        <a href="{self.url('#competencies')}" class="nav-link" data-section="competencies"><span>Skills</span></a>
        <a href="{self.url('#projects')}" class="nav-link" data-section="projects"><span>Projects</span></a>
      </nav>
    </div>
    <div class="header-right">
      {theme_toggle_btn}
    </div>
  </div>
</header>"""

            footer_html = f"""<footer class="site-footer">
  <div class="footer-inner">
    <div class="footer-brand">
      <span class="brand-avatar-sm">VU</span>
      <div>
        <strong>{esc(s.get('name', 'Vivek Umrao'))}</strong> &bull; System Architect
        <div class="footer-tagline">JVM Internals &bull; Mobile Security Frameworks &bull; Enterprise Scale</div>
      </div>
    </div>
    <div class="footer-links">
      <a href="https://github.com/ervivekumrao" target="_blank" rel="noopener noreferrer">GitHub</a>
      <a href="https://www.linkedin.com/in/ervivekumrao/" target="_blank" rel="noopener noreferrer">LinkedIn</a>
      <a href="mailto:vivekumraomain@gmail.com">Email</a>
      <a href="#" onclick="window.scrollTo({{top: 0, behavior: 'smooth'}}); return false;" class="back-to-top">&uarr; Back to Top</a>
    </div>
  </div>
</footer>"""

        script_js = f"""<script>
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

  var sections = ["overview", "experience", "competencies", "projects"];
  var navLinks = document.querySelectorAll(".portfolio-nav .nav-link[data-section]");
  if(navLinks && navLinks.length){{
    function updateProgress(){{
      var scrollPos = window.scrollY + 140;
      var activeIdx = 0;
      for(var i = 0; i < sections.length; i++){{
        var el = document.getElementById(sections[i]);
        if(el && el.offsetTop <= scrollPos){{
          activeIdx = i;
        }}
      }}
      navLinks.forEach(function(link){{
        var sec = link.getAttribute("data-section");
        var idx = sections.indexOf(sec);
        if(idx === activeIdx){{
          link.classList.add("nav-active");
        }} else {{
          link.classList.remove("nav-active");
        }}
      }});
    }}
    window.addEventListener("scroll", updateProgress, {{passive: true}});
    updateProgress();
  }}

  // Interactive Project Search & Category Filtering
  var searchInput = document.getElementById("project-search");
  var filterTabs = document.querySelectorAll(".filter-tab");
  var cardWrappers = document.querySelectorAll(".app-card-wrapper");
  var sectionWrappers = document.querySelectorAll(".project-section-wrapper");

  function filterProjects(){{
    var query = searchInput ? searchInput.value.toLowerCase().trim() : "";
    var activeTab = document.querySelector(".filter-tab.active");
    var activeCat = activeTab ? activeTab.getAttribute("data-filter") : "all";

    cardWrappers.forEach(function(wrapper){{
      var cat = wrapper.getAttribute("data-category");
      var searchData = wrapper.getAttribute("data-search") || "";

      var matchesCat = (activeCat === "all" || cat === activeCat);
      var matchesQuery = (!query || searchData.indexOf(query) !== -1);

      if(matchesCat && matchesQuery){{
        wrapper.style.display = "";
      }} else {{
        wrapper.style.display = "none";
      }}
    }});

    sectionWrappers.forEach(function(sec){{
      var catKey = sec.getAttribute("data-sec-category");
      var visibleCards = sec.querySelectorAll(".app-card-wrapper:not([style*='display: none'])");
      if(activeCat !== "all" && catKey !== activeCat){{
        sec.style.display = "none";
      }} else if(visibleCards.length === 0){{
        sec.style.display = "none";
      }} else {{
        sec.style.display = "";
      }}
    }});
  }}

  if(searchInput){{
    searchInput.addEventListener("input", filterProjects);
  }}

  if(filterTabs && filterTabs.length){{
    filterTabs.forEach(function(tab){{
      tab.addEventListener("click", function(){{
        filterTabs.forEach(function(t){{ t.classList.remove("active"); }});
        tab.classList.add("active");
        filterProjects();
      }});
    }});
  }}

  // Interactive Screenshot Lightbox Modal
  var shots = document.querySelectorAll(".shots-scroll img");
  if(shots && shots.length){{
    var modal = document.createElement("div");
    modal.className = "lightbox-modal";
    modal.innerHTML = '<button class="lightbox-close" aria-label="Close modal">&times;</button><img class="lightbox-content" src="" alt="Screenshot preview">';
    document.body.appendChild(modal);

    var modalImg = modal.querySelector(".lightbox-content");
    var closeBtn = modal.querySelector(".lightbox-close");

    shots.forEach(function(img){{
      img.addEventListener("click", function(){{
        modalImg.src = img.src;
        modalImg.alt = img.alt || "Preview";
        modal.classList.add("active");
      }});
    }});

    function closeModal(){{
      modal.classList.remove("active");
    }}

    if(closeBtn) closeBtn.addEventListener("click", closeModal);
    modal.addEventListener("click", function(e){{
      if(e.target === modal || e.target === closeBtn) closeModal();
    }});
    document.addEventListener("keydown", function(e){{
      if(e.key === "Escape" && modal.classList.contains("active")) closeModal();
    }});
  }}

  window.copyCodeBlock = function(btn){{
    var block = btn.closest(".code-block") || btn.closest("pre") || (btn.parentElement ? btn.parentElement.closest(".code-block") : null);
    var code = block ? block.querySelector("code") : null;
    if(!code) return;
    var text = code.innerText || code.textContent;
    if(navigator.clipboard && navigator.clipboard.writeText){{
      navigator.clipboard.writeText(text).then(function(){{
        showCopied(btn);
      }}).catch(function(){{
        fallbackCopy(text, btn);
      }});
    }} else {{
      fallbackCopy(text, btn);
    }}
  }};

  function showCopied(btn){{
    var orig = btn.innerHTML;
    btn.innerHTML = "✅ Copied!";
    btn.classList.add("copied");
    setTimeout(function(){{
      btn.innerHTML = orig;
      btn.classList.remove("copied");
    }}, 2000);
  }}

  function fallbackCopy(text, btn){{
    var textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-9999px";
    document.body.appendChild(textArea);
    textArea.select();
    try{{
      document.execCommand("copy");
      showCopied(btn);
    }}catch(e){{
      console.error("Copy failed", e);
    }}
    document.body.removeChild(textArea);
  }}

  document.querySelectorAll(".code-block, pre").forEach(function(el){{
    if(el.tagName.toLowerCase() === "pre" && el.closest(".code-block")) return;
    if(el.querySelector(".copy-btn")) return;
    var btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.type = "button";
    btn.innerHTML = "📋 Copy";
    btn.onclick = function(){{ copyCodeBlock(btn); }};
    var header = el.querySelector(".code-header");
    if(header){{
      header.appendChild(btn);
    }} else {{
      el.style.position = "relative";
      btn.style.position = "absolute";
      btn.style.top = "0.5rem";
      btn.style.right = "0.5rem";
      el.appendChild(btn);
    }}
  }});
}})();
</script>"""

        return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<script>(function(){{var t;try{{t=localStorage.getItem("theme");}}catch(e){{}}if(!t){{t="dark";}}document.documentElement.setAttribute("data-theme",t);}})();</script>
<title>{esc(title)} &bull; {esc(s.get('name'))}</title><meta name="description" content="{esc(desc or s.get('tagline'))}">
<link rel="icon" type="{icon_type}" href="{icon_href}">
<link rel="apple-touch-icon" href="{icon_href}">
<link rel="stylesheet" href="{self.url('style.css')}"></head><body>
{header_html}
<main>
{body}
</main>
{footer_html}
{script_js}
</body></html>"""


def render_download(_site: Site, p: dict, versions: list[dict]) -> str:
    """Renders the build version, binary checksums, and DPM provisioning QR code for app pages."""
    if not versions:
        return """
<section class="proj-section" id="download">
  <h2 class="proj-section-title">📲 Version &amp; Security Metadata</h2>
  <p class="mut" style="margin:0">No binary release has been published yet. You can inspect the source code or install via Google Play above.</p>
</section>
"""
    m = versions[0]
    h = [
        f"""
<section class="proj-section" id="download">
  <h2 class="proj-section-title">📲 Version &amp; Security Metadata</h2>
  <div class="download-hero">
    <div class="download-card">
      <div>
        <div style="font-size:0.82rem;font-weight:600;color:var(--mut);text-transform:uppercase;letter-spacing:0.5px">Latest Release Build</div>
        <div style="font-size:1.75rem;font-weight:800;color:var(--fg);margin:0.25rem 0">v{esc(m['version_name'])}</div>
        <div style="font-size:0.88rem;color:var(--mut)">Size: <strong>{human_size(m['size_bytes'])}</strong> &bull; Min Android: <strong>API {esc(m['min_sdk'])}+</strong></div>
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
      <strong>Factory-Reset Enrollment:</strong> Power on factory-reset Android device. Tap the welcome screen 6 times to trigger QR scanner, then scan code below.
    </p>
    {qr_svg_html}
    <details style="width:100%;max-width:640px;margin-top:0.75rem;text-align:left"><summary style="cursor:pointer;font-weight:600;color:var(--acc);font-size:0.85rem">View Provisioning JSON Payload</summary><pre style="margin-top:0.5rem;font-size:0.75rem;white-space:pre-wrap;word-break:break-all">{esc(payload)}</pre></details>
  </div>
""")

    rows = "".join(f"<tr><td><strong>v{esc(v['version_name'])}</strong></td><td>{esc(v['released_at'][:10])}</td></tr>" for v in versions[:15])
    h.append(f"""
  <h3 style="margin:1.75rem 0 0.75rem 0;font-size:1.15rem">Release History</h3>
  <div class='wrap'><table><thead><tr><th>Version</th><th>Release Date</th></tr></thead><tbody>{rows}</tbody></table></div>
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

    icon_dark = p.get("icon_dark") or ("icon_dark.svg" if (assets_dir / "icon_dark.svg").exists() else None)
    icon_light = p.get("icon_light") or ("icon_light.svg" if (assets_dir / "icon_light.svg").exists() else None)

    tab_icon_url = ""
    icon_hdr = ""

    if icon_dark and icon_light and icon_dark != icon_light:
        dark_url = site.url(f"{pid}/assets/{icon_dark}")
        light_url = site.url(f"{pid}/assets/{icon_light}")
        tab_icon_url = dark_url
        icon_hdr = f"""
<img class='proj-icon-img theme-dark-only' src='{dark_url}' alt='{esc(main_title)} icon'>
<img class='proj-icon-img theme-light-only' src='{light_url}' alt='{esc(main_title)} icon'>
"""
    elif (assets_dir / "icon.svg").exists():
        tab_icon_url = site.url(f"{pid}/assets/icon.svg")
        icon_hdr = f"<img class='proj-icon-img' src='{tab_icon_url}' alt='{esc(main_title)} icon'>"
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
        icon_hdr = f"<img class='proj-icon-img' src='{tab_icon_url}' alt='{esc(main_title)} icon'>"

    tags_html = "".join(f"<span class='tag'>{esc(t)}</span>" for t in p.get("tags", []))

    links = []
    if p.get("play_store_url"):
        links.append(f"<a class='btn btn-play' href='{esc(p['play_store_url'])}' target='_blank' rel='noopener noreferrer'>Get it on Google Play &nearr;</a>")
    if p.get("visibility") == "public" and p.get("repo"):
        links.append(f"<a class='btn alt' href='https://github.com/{esc(p['repo'])}' target='_blank' rel='noopener noreferrer'>View Source Code &nearr;</a>")
    if p.get("library", {}).get("docs_url"):
        links.append(f"<a class='btn alt' href='{esc(p['library']['docs_url'])}' target='_blank' rel='noopener noreferrer'>API Documentation &nearr;</a>")
    if (root / "privacy.md").exists():
        links.append(f"<a class='btn alt' href='{site.url(f'{pid}/privacy/')}'>Privacy Policy</a>")
    if (root / "license.md").exists():
        links.append(f"<a class='btn alt' href='{site.url(f'{pid}/license/')}'>License Information</a>")

    subtitle_html = f"<div class='proj-hero-subtitle'>{esc(sub_title)}</div>" if sub_title else ""
    version_badge = f"<span class='app-badge-ver'>v{esc(versions[0]['version_name'])}</span>" if versions else ""
    visibility_badge = "<span class='app-badge-open'>Open Source</span>" if p.get("visibility") == "public" else ""

    banner_dark = p.get("banner_dark") or p.get("banner") or p.get("banner_image")
    banner_light = p.get("banner_light") or p.get("banner") or p.get("banner_image")

    hero_banner_html = ""
    if banner_dark and banner_light and banner_dark != banner_light:
        hero_banner_html = f"""
  <div class="proj-hero-banner-wrap" style="margin:1.5rem 0 1.25rem 0;border-radius:14px;overflow:hidden;border:1px solid var(--card-border)">
    <img src="{site.url(f'{pid}/assets/{banner_dark}')}" class="theme-dark-only" alt="{esc(main_title)} Banner" style="width:100%;height:auto;display:block">
    <img src="{site.url(f'{pid}/assets/{banner_light}')}" class="theme-light-only" alt="{esc(main_title)} Banner" style="width:100%;height:auto;display:block">
  </div>
"""
    elif banner_dark:
        hero_banner_html = f"""
  <div class="proj-hero-banner-wrap" style="margin:1.5rem 0 1.25rem 0;border-radius:14px;overflow:hidden;border:1px solid var(--card-border)">
    <img src="{site.url(f'{pid}/assets/{banner_dark}')}" alt="{esc(main_title)} Banner" style="width:100%;height:auto;display:block">
  </div>
"""

    hero_html = f"""
<div class="proj-hero-card" id="overview">
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
  {hero_banner_html}
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
<section class="proj-section shots-container" id="showcase">
  <h2 class="proj-section-title">🖼️ Visual Showcase &amp; Highlights</h2>
  <div class="shots-scroll">
    {shot_imgs}
  </div>
</section>
"""

    desc_content = md_to_html(p.get("description", ""))
    desc_section = f"""
<section class="proj-section" id="details">
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
<section class="proj-section" id="installation">
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
        repo_btn = f"<a class='btn alt' href='{repo_url}' target='_blank' rel='noopener noreferrer'>View Repository on GitHub &nearr;</a>" if repo_url else ""
        extra_section = f"""
<section class="proj-section" id="quickstart">
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

    body = hero_html + shots_section + desc_section + extra_section

    project_info = {
        "id": pid,
        "title": main_title,
        "icon_url": tab_icon_url,
        "version": f"v{versions[0]['version_name']}" if versions else "",
        "kind": kind,
        "has_screenshots": bool(screenshots),
        "has_privacy": (root / "privacy.md").exists(),
        "has_license": (root / "license.md").exists(),
        "tagline": p.get("tagline", ""),
        "cat_badge": cat_badge,
        "current_subpage": "overview"
    }

    site.write(f"{pid}/index.html", site.page(p["name"], body, p.get("tagline", ""), icon_url=tab_icon_url, project_info=project_info))

    aliases = p.get("aliases", [])
    for alias in aliases:
        alias_out = site.out / alias
        alias_out.mkdir(parents=True, exist_ok=True)
        redirect_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Redirecting to {esc(main_title)}...</title>
  <link rel="canonical" href="{site.url(f'{pid}/')}">
  <meta http-equiv="refresh" content="0; url={site.url(f'{pid}/')}">
  <script>window.location.replace("{site.url(f'{pid}/')}");</script>
</head>
<body style="font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;">
  <div style="text-align: center;">
    <h2>Project Renamed to {esc(main_title)}</h2>
    <p>Redirecting to <a href="{site.url(f'{pid}/')}" style="color: #6366f1;">{site.url(f'{pid}/')}</a>...</p>
  </div>
</body>
</html>"""
        (alias_out / "index.html").write_text(redirect_html, encoding="utf-8")
        if (root / "privacy.md").exists():
            alias_priv = alias_out / "privacy"
            alias_priv.mkdir(parents=True, exist_ok=True)
            priv_redirect_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Redirecting to {esc(main_title)} Privacy Policy...</title>
  <link rel="canonical" href="{site.url(f'{pid}/privacy/')}">
  <meta http-equiv="refresh" content="0; url={site.url(f'{pid}/privacy/')}">
  <script>window.location.replace("{site.url(f'{pid}/privacy/')}");</script>
</head>
<body style="font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;">
  <div style="text-align: center;">
    <h2>Project Renamed to {esc(main_title)}</h2>
    <p>Redirecting to <a href="{site.url(f'{pid}/privacy/')}" style="color: #6366f1;">{site.url(f'{pid}/privacy/')}</a>...</p>
  </div>
</body>
</html>"""
            (alias_priv / "index.html").write_text(priv_redirect_html, encoding="utf-8")

    if (root / "license.md").exists():
        lic_body = f"""
<div class="proj-hero-card" style="margin-bottom:1.5rem">
  <div style="display:flex;align-items:center;gap:0.5rem;font-size:0.85rem;font-weight:600;color:var(--acc);margin-bottom:0.5rem">
    <span>📜 License &amp; Terms Compliance</span>
  </div>
  <h1 class="proj-hero-title">{esc(main_title)}</h1>
  <div class="proj-hero-subtitle">Open Source License Terms &amp; Copyright Notice</div>
</div>
<div class="doc-card">
  {md_to_html((root / "license.md").read_text(encoding="utf-8"))}
</div>
"""
        lic_project_info = dict(project_info)
        lic_project_info["current_subpage"] = "license"
        site.write(f"{pid}/license/index.html", site.page(f"{p['name']} License Information", lic_body, icon_url=tab_icon_url, project_info=lic_project_info))

    if (root / "privacy.md").exists():
        priv_body = f"""
<div class="proj-hero-card" style="margin-bottom:1.5rem">
  <div style="display:flex;align-items:center;gap:0.5rem;font-size:0.85rem;font-weight:600;color:var(--acc);margin-bottom:0.5rem">
    <span>🛡️ Data Privacy &amp; Security Compliance</span>
  </div>
  <h1 class="proj-hero-title">{esc(main_title)}</h1>
  <div class="proj-hero-subtitle">Privacy Policy &amp; Security Standards</div>
</div>
<div class="doc-card">
  {md_to_html((root / "privacy.md").read_text(encoding="utf-8"))}
</div>
"""
        priv_project_info = dict(project_info)
        priv_project_info["current_subpage"] = "privacy"
        site.write(f"{pid}/privacy/index.html", site.page(f"{p['name']} Privacy Policy", priv_body, icon_url=tab_icon_url, project_info=priv_project_info))


def render_profile_sections(site: Site, profile: dict, experience: dict) -> str:
    """Renders the portfolio home page Hero box, Professional Experience, and Core Competencies HTML sections."""
    profile_url = site.url(profile.get("profile_image", "profile.jpg"))

    social_btns = []
    for link in profile.get("social_links", []):
        btn_class = "btn" if link.get("primary") else "btn alt"
        target = " target='_blank' rel='noopener noreferrer'" if link["url"].startswith("http") else ""
        social_btns.append(f"<a href='{esc(link['url'])}' class='{btn_class}'{target}>{esc(link['label'])}</a>")

    social_btns.append(f"<a href='{site.url('#projects')}' class='btn alt'>Browse Projects &darr;</a>")

    stats_html = []
    for stat in profile.get("stats", []):
        stats_html.append(
            f"<div class='stat-item'>"
            f"  <div class='stat-value'>{esc(stat['value'])}</div>"
            f"  <div class='stat-label'>{esc(stat['label'])}</div>"
            f"</div>"
        )

    hero_html = f"""<div class="hero-box" id="overview">
<div style="display:flex;gap:2rem;align-items:center;flex-wrap:wrap">
  <div style="flex:1;min-width:280px">
    <h1 class="hero-headline">{esc(profile.get('headline', "Hi, I'm Vivek Umrao."))}</h1>
    <div class="hero-quote">{esc(profile.get('quote', ''))}</div>
    <p class="hero-summary">
      {esc(profile.get('summary', ''))}
    </p>
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:1.25rem">
      {''.join(social_btns)}
    </div>
  </div>
  <div style="flex-shrink:0">
    <img src="{profile_url}" alt="{esc(profile.get('name', 'Vivek Umrao'))}" class="hero-avatar">
  </div>
</div>
<div class="stats-grid">
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

    exp_html = f"""<section id="experience" style="margin-top:3.5rem">
<h2 style="font-size:1.85rem;font-weight:800;margin-bottom:0.25rem;letter-spacing:-0.02em">Professional Experience</h2>
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

    comp_html = f"""<section id="competencies" style="margin-top:3.5rem">
<h2 style="font-size:1.85rem;font-weight:800;margin-bottom:0.25rem;letter-spacing:-0.02em">Core Competencies &amp; Technical Skills</h2>
<p class="mut" style="margin-top:0;margin-bottom:1.5rem">Systematic domain expertise, runtime architectures, and enterprise technologies from 15+ years of systems engineering.</p>

<div class="comp-grid">
  {''.join(comp_cards)}
</div>
</section>"""

    return hero_html + exp_html + comp_html
