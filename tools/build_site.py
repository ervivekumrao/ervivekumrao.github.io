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

from tools.builder.utils import esc, get_project_titles
from tools.builder.github_api import fetch_manifests
from tools.builder.styles import CSS
from tools.builder.renderers import Site, render_project


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
