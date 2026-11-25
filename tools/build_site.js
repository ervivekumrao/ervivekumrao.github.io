const fs = require('fs');
const path = require('path');
const http = require('http');

const ROOT = path.resolve(__dirname, '..');
const CATALOG = path.join(ROOT, 'catalog');
const STATIC = path.join(ROOT, 'static');

function esc(v) {
  if (v === null || v === undefined) return '';
  return String(v)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function humanSize(bytes) {
  return (bytes / 1048576).toFixed(1) + ' MB';
}

function getProjectTitles(p) {
  const explicitSub = p.subtitle;
  const rawName = p.name || '';
  let mainTitle = rawName;
  let nameSub = '';
  if (rawName.includes(' — ')) {
    [mainTitle, nameSub] = rawName.split(' — ');
  } else if (rawName.includes(' – ')) {
    [mainTitle, nameSub] = rawName.split(' – ');
  }
  const subtitle = explicitSub !== undefined && explicitSub !== null ? explicitSub : nameSub;
  return [mainTitle, subtitle];
}

function getProjectCategoryBadge(p) {
  if (p.category_badge) return p.category_badge;
  const ptype = p.type || 'app';
  if (ptype === 'app') return '📱 Android App';
  if (ptype === 'library') return '📦 Android Library';
  return '⚙️ System Tool';
}

function mdToHtml(text) {
  if (!text) return '';
  text = text.trim();
  if (text.startsWith('<')) return text;

  function parseInline(str) {
    let s = esc(str);
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
    s = s.replace(/(\*\*|__)(.*?)\1/g, '<strong>$2</strong>');
    s = s.replace(/(\*|_)(.*?)\1/g, '<em>$2</em>');
    s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, label, url) => {
      const target = url.startsWith('http') ? ' target="_blank" rel="noopener noreferrer"' : '';
      return `<a href="${url}"${target}>${label}</a>`;
    });
    return s;
  }

  const lines = text.split(/\r?\n/);
  const blocks = [];
  let inCode = false;
  let codeLines = [];
  let inList = false;
  let listItems = [];

  function flushList() {
    if (inList && listItems.length) {
      blocks.push(`<ul>${listItems.join('')}</ul>`);
      listItems = [];
      inList = false;
    }
  }

  for (const line of lines) {
    const stripped = line.trim();

    if (stripped.startsWith('```')) {
      if (inCode) {
        blocks.push(`<pre><code>${esc(codeLines.join('\n'))}</code></pre>`);
        codeLines = [];
        inCode = false;
      } else {
        flushList();
        inCode = true;
        codeLines = [];
      }
      continue;
    }

    if (inCode) {
      codeLines.push(line);
      continue;
    }

    if (!stripped) {
      flushList();
      continue;
    }

    if (stripped === '---' || stripped === '***' || stripped === '___') {
      flushList();
      blocks.push('<hr>');
      continue;
    }

    if (stripped.startsWith('# ')) {
      flushList();
      blocks.push(`<h1>${parseInline(stripped.slice(2))}</h1>`);
      continue;
    }
    if (stripped.startsWith('## ')) {
      flushList();
      blocks.push(`<h2>${parseInline(stripped.slice(3))}</h2>`);
      continue;
    }
    if (stripped.startsWith('### ')) {
      flushList();
      blocks.push(`<h3>${parseInline(stripped.slice(4))}</h3>`);
      continue;
    }
    if (stripped.startsWith('#### ')) {
      flushList();
      blocks.push(`<h4>${parseInline(stripped.slice(5))}</h4>`);
      continue;
    }

    if (stripped.startsWith('> ')) {
      flushList();
      blocks.push(`<blockquote>${parseInline(stripped.slice(2))}</blockquote>`);
      continue;
    }

    if (stripped.startsWith('- ') || stripped.startsWith('* ') || stripped.startsWith('+ ')) {
      inList = true;
      listItems.push(`<li>${parseInline(stripped.slice(2))}</li>`);
      continue;
    }

    flushList();
    blocks.push(`<p>${parseInline(stripped)}</p>`);
  }

  flushList();
  if (inCode && codeLines.length) {
    blocks.push(`<pre><code>${esc(codeLines.join('\n'))}</code></pre>`);
  }

  return blocks.join('\n');
}

function page(cfg, title, body, desc = '', iconUrl = '', projectInfo = null) {
  const iconHref = iconUrl ? iconUrl : '/favicon.svg';
  const iconType = iconHref.endsWith('.svg') ? 'image/svg+xml' : 'image/png';

  const themeToggleBtn = `
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
      </button>`;

  let headerHtml = '';
  let footerHtml = '';

  if (projectInfo) {
    const pid = projectInfo.id;
    const mainTitle = projectInfo.title;
    const pIcon = projectInfo.iconUrl || '/favicon.svg';
    const verStr = projectInfo.version || '';
    const kind = projectInfo.kind || 'app';
    const hasShots = !!projectInfo.hasScreenshots;
    const hasPriv = !!projectInfo.hasPrivacy;
    const hasLic = !!projectInfo.hasLicense;
    const currSub = projectInfo.currentSubpage || 'overview';

    const baseProj = `/${pid}/`;
    const overviewHref = currSub !== 'overview' ? baseProj : '#overview';
    const showcaseHref = currSub !== 'overview' ? `${baseProj}#showcase` : '#showcase';
    const detailsHref = currSub !== 'overview' ? `${baseProj}#details` : '#details';
    let actionHref = currSub !== 'overview' ? `${baseProj}#download` : '#download';
    if (kind === 'library') actionHref = currSub !== 'overview' ? `${baseProj}#installation` : '#installation';
    else if (kind === 'other') actionHref = currSub !== 'overview' ? `${baseProj}#quickstart` : '#quickstart';

    const actionLabel = kind === 'app' ? 'Releases' : (kind === 'library' ? 'Setup' : 'Quickstart');
    const verBadgeHtml = verStr ? `<span class='app-badge-ver'>${esc(verStr)}</span>` : '';
    const shotsNavHtml = hasShots ? `<a href='${showcaseHref}' class='project-nav-link'>Showcase</a>` : '';
    const privNavHtml = hasPriv ? `<a href='/${pid}/privacy/' class='project-nav-link ${currSub === 'privacy' ? 'nav-active' : ''}'>Privacy</a>` : '';
    const licNavHtml = hasLic ? `<a href='/${pid}/license/' class='project-nav-link ${currSub === 'license' ? 'nav-active' : ''}'>License</a>` : '';

    headerHtml = `<header class="site-header project-header">
  <div class="header-inner">
    <div class="header-left">
      <a href="${baseProj}" class="project-brand">
        <div class="project-header-icon"><img src="${pIcon}" alt="${esc(mainTitle)} icon"></div>
        <div class="project-header-text">
          <span class="project-header-title">${esc(mainTitle)}</span>
          ${verBadgeHtml}
        </div>
      </a>
      <nav class="project-nav" aria-label="${esc(mainTitle)} Navigation">
        <a href="${overviewHref}" class="project-nav-link ${currSub === 'overview' ? 'nav-active' : ''}">Overview</a>
        ${shotsNavHtml}
        <a href="${detailsHref}" class="project-nav-link">Details</a>
        <a href="${actionHref}" class="project-nav-link">${actionLabel}</a>
        ${privNavHtml}
        ${licNavHtml}
      </nav>
    </div>
    <div class="header-right">
      <a href="https://github.com/ervivekumrao" target="_blank" rel="noopener noreferrer" class="dev-portfolio-badge" title="Developer GitHub Profile">
        <span class="dev-avatar-sm">VU</span>
        <span class="dev-label">Developer GitHub &nearr;</span>
      </a>
      ${themeToggleBtn}
    </div>
  </div>
</header>`;

    const privFoot = hasPriv ? `<a href='/${pid}/privacy/'>Privacy Policy</a>` : '';
    const licFoot = hasLic ? `<a href='/${pid}/license/'>License Information</a>` : '';

    footerHtml = `<footer class="site-footer project-footer">
  <div class="footer-inner">
    <div class="footer-brand">
      <div class="proj-footer-icon"><img src="${pIcon}" alt="${esc(mainTitle)} icon"></div>
      <div>
        <strong>${esc(mainTitle)}</strong> &bull; ${esc(projectInfo.catBadge || '')}
        <div class="footer-tagline">${esc(projectInfo.tagline || '')}</div>
      </div>
    </div>
    <div class="footer-links">
      ${privFoot}
      ${licFoot}
      <a href="https://github.com/ervivekumrao" target="_blank" rel="noopener noreferrer" class="footer-dev-link">Built by <strong>Vivek Umrao</strong> &nearr;</a>
      <a href="#" onclick="window.scrollTo({top: 0, behavior: 'smooth'}); return false;" class="back-to-top">&uarr; Back to Top</a>
    </div>
  </div>
</footer>`;

  } else {
    headerHtml = `<header class="site-header main-header">
  <div class="header-inner">
    <div class="header-left">
      <a href="/" class="portfolio-brand">
        <span class="brand-avatar">VU</span>
        <div class="brand-info">
          <span class="brand-name">${esc(cfg.name || 'Vivek Umrao')}</span>
          <span class="brand-role">System Architect</span>
        </div>
      </a>
      <nav class="portfolio-nav" aria-label="Portfolio Navigation">
        <a href="#overview" class="nav-link nav-active" data-section="overview"><span>⚡ Overview</span></a>
        <a href="#experience" class="nav-link" data-section="experience"><span>Experience</span></a>
        <a href="#competencies" class="nav-link" data-section="competencies"><span>Skills</span></a>
        <a href="#projects" class="nav-link" data-section="projects"><span>Projects</span></a>
      </nav>
    </div>
    <div class="header-right">
      ${themeToggleBtn}
    </div>
  </div>
</header>`;

    footerHtml = `<footer class="site-footer">
  <div class="footer-inner">
    <div class="footer-brand">
      <span class="brand-avatar-sm">VU</span>
      <div>
        <strong>${esc(cfg.name || 'Vivek Umrao')}</strong> &bull; System Architect
        <div class="footer-tagline">JVM Internals &bull; Mobile Security Frameworks &bull; Enterprise Scale</div>
      </div>
    </div>
    <div class="footer-links">
      <a href="https://github.com/ervivekumrao" target="_blank" rel="noopener noreferrer">GitHub</a>
      <a href="https://www.linkedin.com/in/ervivekumrao/" target="_blank" rel="noopener noreferrer">LinkedIn</a>
      <a href="mailto:vivekumraomain@gmail.com">Email</a>
      <a href="#" onclick="window.scrollTo({top: 0, behavior: 'smooth'}); return false;" class="back-to-top">&uarr; Back to Top</a>
    </div>
  </div>
</footer>`;
  }

  const scriptJs = `<script>
(function(){
  var btn = document.getElementById("theme-toggle");
  var mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

  function getTheme(){
    var d = document.documentElement.getAttribute("data-theme");
    if(d === "dark" || d === "light") return d;
    try{
      var t = localStorage.getItem("theme");
      if(t) return t;
    }catch(e){}
    return mediaQuery.matches ? "dark" : "light";
  }

  function setTheme(next){
    document.documentElement.setAttribute("data-theme", next);
    try{
      localStorage.setItem("theme", next);
    }catch(e){}
  }

  if(btn){
    btn.addEventListener("click", function(){
      var current = getTheme();
      var next = current === "dark" ? "light" : "dark";
      setTheme(next);
    });
  }

  if(mediaQuery && mediaQuery.addEventListener){
    mediaQuery.addEventListener("change", function(e){
      var hasCustom = false;
      try{
        hasCustom = !!localStorage.getItem("theme");
      }catch(err){}
      if(!hasCustom){
        setTheme(e.matches ? "dark" : "light");
      }
    });
  }

  var sections = ["overview", "experience", "competencies", "projects"];
  var navLinks = document.querySelectorAll(".portfolio-nav .nav-link[data-section]");
  if(navLinks && navLinks.length){
    function updateProgress(){
      var scrollPos = window.scrollY + 140;
      var activeIdx = 0;
      for(var i = 0; i < sections.length; i++){
        var el = document.getElementById(sections[i]);
        if(el && el.offsetTop <= scrollPos){
          activeIdx = i;
        }
      }
      navLinks.forEach(function(link){
        var sec = link.getAttribute("data-section");
        var idx = sections.indexOf(sec);
        if(idx === activeIdx){
          link.classList.add("nav-active");
        } else {
          link.classList.remove("nav-active");
        }
      });
    }
    window.addEventListener("scroll", updateProgress, {passive: true});
    updateProgress();
  }

  // Interactive Project Search & Category Filtering
  var searchInput = document.getElementById("project-search");
  var filterTabs = document.querySelectorAll(".filter-tab");
  var cardWrappers = document.querySelectorAll(".app-card-wrapper");
  var sectionWrappers = document.querySelectorAll(".project-section-wrapper");

  function filterProjects(){
    var query = searchInput ? searchInput.value.toLowerCase().trim() : "";
    var activeTab = document.querySelector(".filter-tab.active");
    var activeCat = activeTab ? activeTab.getAttribute("data-filter") : "all";

    cardWrappers.forEach(function(wrapper){
      var cat = wrapper.getAttribute("data-category");
      var searchData = wrapper.getAttribute("data-search") || "";

      var matchesCat = (activeCat === "all" || cat === activeCat);
      var matchesQuery = (!query || searchData.indexOf(query) !== -1);

      if(matchesCat && matchesQuery){
        wrapper.style.display = "";
      } else {
        wrapper.style.display = "none";
      }
    });

    sectionWrappers.forEach(function(sec){
      var catKey = sec.getAttribute("data-sec-category");
      var visibleCards = sec.querySelectorAll(".app-card-wrapper:not([style*='display: none'])");
      if(activeCat !== "all" && catKey !== activeCat){
        sec.style.display = "none";
      } else if(visibleCards.length === 0){
        sec.style.display = "none";
      } else {
        sec.style.display = "";
      }
    });
  }

  if(searchInput){
    searchInput.addEventListener("input", filterProjects);
  }

  if(filterTabs && filterTabs.length){
    filterTabs.forEach(function(tab){
      tab.addEventListener("click", function(){
        filterTabs.forEach(function(t){ t.classList.remove("active"); });
        tab.classList.add("active");
        filterProjects();
      });
    });
  }

  // Interactive Screenshot Lightbox Modal
  var shots = document.querySelectorAll(".shots-scroll img");
  if(shots && shots.length){
    var modal = document.createElement("div");
    modal.className = "lightbox-modal";
    modal.innerHTML = '<button class="lightbox-close" aria-label="Close modal">&times;</button><img class="lightbox-content" src="" alt="Screenshot preview">';
    document.body.appendChild(modal);

    var modalImg = modal.querySelector(".lightbox-content");
    var closeBtn = modal.querySelector(".lightbox-close");

    shots.forEach(function(img){
      img.addEventListener("click", function(){
        modalImg.src = img.src;
        modalImg.alt = img.alt || "Preview";
        modal.classList.add("active");
      });
    });

    function closeModal(){
      modal.classList.remove("active");
    }

    if(closeBtn) closeBtn.addEventListener("click", closeModal);
    modal.addEventListener("click", function(e){
      if(e.target === modal || e.target === closeBtn) closeModal();
    });
    document.addEventListener("keydown", function(e){
      if(e.key === "Escape" && modal.classList.contains("active")) closeModal();
    });
  }

  window.copyCodeBlock = function(btn){
    var block = btn.closest(".code-block") || btn.closest("pre") || (btn.parentElement ? btn.parentElement.closest(".code-block") : null);
    var code = block ? block.querySelector("code") : null;
    if(!code) return;
    var text = code.innerText || code.textContent;
    if(navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(function(){
        showCopied(btn);
      }).catch(function(){
        fallbackCopy(text, btn);
      });
    } else {
      fallbackCopy(text, btn);
    }
  };

  function showCopied(btn){
    var orig = btn.innerHTML;
    btn.innerHTML = "✅ Copied!";
    btn.classList.add("copied");
    setTimeout(function(){
      btn.innerHTML = orig;
      btn.classList.remove("copied");
    }, 2000);
  }

  function fallbackCopy(text, btn){
    var textArea = document.createElement("textarea");
    textArea.value = text;
    textArea.style.position = "fixed";
    textArea.style.left = "-9999px";
    document.body.appendChild(textArea);
    textArea.select();
    try{
      document.execCommand("copy");
      showCopied(btn);
    }catch(e){
      console.error("Copy failed", e);
    }
    document.body.removeChild(textArea);
  }

  document.querySelectorAll(".code-block, pre").forEach(function(el){
    if(el.tagName.toLowerCase() === "pre" && el.closest(".code-block")) return;
    if(el.querySelector(".copy-btn")) return;
    var btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.type = "button";
    btn.innerHTML = "📋 Copy";
    btn.onclick = function(){ copyCodeBlock(btn); };
    var header = el.querySelector(".code-header");
    if(header){
      header.appendChild(btn);
    } else {
      el.style.position = "relative";
      btn.style.position = "absolute";
      btn.style.top = "0.5rem";
      btn.style.right = "0.5rem";
      el.appendChild(btn);
    }
  });
})();
</script>`;

  return `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<script>(function(){var t;try{t=localStorage.getItem("theme");}catch(e){}if(!t){t="dark";}document.documentElement.setAttribute("data-theme",t);})();</script>
<title>${esc(title)} &bull; ${esc(cfg.name)}</title><meta name="description" content="${esc(desc || cfg.tagline)}">
<link rel="icon" type="${iconType}" href="${iconHref}">
<link rel="apple-touch-icon" href="${iconHref}">
<link rel="stylesheet" href="/style.css"></head><body>
${headerHtml}
<main>
${body}
</main>
${footerHtml}
${scriptJs}
</body></html>`;
}

function renderProfileSections(cfg, profile, experience) {
  const profileUrl = profile.profile_image || '/profile.jpg';
  const socialBtns = (profile.social_links || []).map(link => {
    const btnClass = link.primary ? 'btn' : 'btn alt';
    const target = link.url.startsWith('http') ? ' target="_blank" rel="noopener noreferrer"' : '';
    return `<a href="${esc(link.url)}" class="${btnClass}"${target}>${esc(link.label)}</a>`;
  }).join('');

  const statsHtml = (profile.stats || []).map(stat => `
    <div class="stat-item">
      <div class="stat-value">${esc(stat.value)}</div>
      <div class="stat-label">${esc(stat.label)}</div>
    </div>
  `).join('');

  const statusBadgeHtml = profile.status_badge ? `
    <div class="status-badge">
      <span class="status-dot"></span>
      ${esc(profile.status_badge)}
    </div>` : '';

  const heroHtml = `<div class="hero-box" id="overview">
<div style="display:flex;gap:2rem;align-items:center;flex-wrap:wrap">
  <div style="flex:1;min-width:280px">
    ${statusBadgeHtml}
    <h1 class="hero-headline">${esc(profile.headline || "Hi, I'm Vivek Umrao.")}</h1>
    <div class="hero-quote">${esc(profile.quote || '')}</div>
    <p class="hero-summary">
      ${esc(profile.summary || '')}
    </p>
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:1.25rem">
      ${socialBtns}
      <a href="#projects" class="btn alt">Browse Projects &darr;</a>
    </div>
  </div>
  <div style="flex-shrink:0">
    <img src="${profileUrl}" alt="${esc(profile.name || 'Vivek Umrao')}" class="hero-avatar">
  </div>
</div>
<div class="stats-grid">
  ${statsHtml}
</div>
</div>`;

  const roleCards = (experience.roles || []).map(role => {
    const titleSub = role.title_sub ? ` <span style="font-size:0.95rem;font-weight:500;color:var(--mut)">${esc(role.title_sub)}</span>` : '';
    const noteHtml = role.note ? `<div class="exp-note">${esc(role.note)}</div>` : '';
    const bullets = (role.highlights || []).map(h => `<li>${h}</li>`).join('');
    return `
      <div class="exp-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem;margin-bottom:0.5rem">
          <div>
            <h3 style="margin:0;font-size:1.25rem;font-weight:700">${esc(role.title)}${titleSub}</h3>
            <div style="color:var(--acc);font-weight:600;font-size:1rem;margin-top:0.15rem">${esc(role.company)}</div>
          </div>
          <div class="tag" style="font-weight:600">${esc(role.period)}</div>
        </div>
        ${noteHtml}
        <ul class="exp-list">${bullets}</ul>
      </div>
    `;
  }).join('');

  const expHtml = `<section id="experience" style="margin-top:3.5rem">
<h2 style="font-size:1.85rem;font-weight:800;margin-bottom:0.25rem;letter-spacing:-0.02em">Professional Experience</h2>
<p class="mut" style="margin-top:0;margin-bottom:1.5rem">A 15+ year track record of architecting JVM internals, mobile security platforms, and enterprise solutions at global scale.</p>

<div style="display:flex;flex-direction:column;gap:1.5rem">
  ${roleCards}
</div>
</section>`;

  const compCards = (experience.competencies || []).map(comp => {
    const chips = (comp.chips || []).map(chip => {
      const cls = chip.highlight ? 'comp-chip highlight' : 'comp-chip';
      return `<span class="${cls}">${esc(chip.name)}</span>`;
    }).join('');
    return `
      <div class="comp-card">
        <div class="comp-header">
          <div class="comp-title">
            <span>${esc(comp.icon)} ${esc(comp.category)}</span>
            <span class="comp-count">${esc(comp.count_label)}</span>
          </div>
        </div>
        <div class="comp-chips">${chips}</div>
      </div>
    `;
  }).join('');

  const compHtml = `<section id="competencies" style="margin-top:3.5rem">
<h2 style="font-size:1.85rem;font-weight:800;margin-bottom:0.25rem;letter-spacing:-0.02em">Core Competencies &amp; Technical Skills</h2>
<p class="mut" style="margin-top:0;margin-bottom:1.5rem">Systematic domain expertise, runtime architectures, and enterprise technologies from 15+ years of systems engineering.</p>

<div class="comp-grid">
  ${compCards}
</div>
</section>`;

  return heroHtml + expHtml + compHtml;
}

function buildSite(outDir, customFixturePath) {
  if (fs.existsSync(outDir)) {
    fs.rmSync(outDir, { recursive: true, force: true });
  }
  fs.mkdirSync(outDir, { recursive: true });

  const cfg = JSON.parse(fs.readFileSync(path.join(CATALOG, 'site.json'), 'utf8'));
  const profile = fs.existsSync(path.join(CATALOG, 'profile.json')) ? JSON.parse(fs.readFileSync(path.join(CATALOG, 'profile.json'), 'utf8')) : {};
  const experience = fs.existsSync(path.join(CATALOG, 'experience.json')) ? JSON.parse(fs.readFileSync(path.join(CATALOG, 'experience.json'), 'utf8')) : {};

  // Copy static assets
  if (fs.existsSync(STATIC)) {
    fs.cpSync(STATIC, outDir, { recursive: true });
  }

  // Load offline fixtures
  const fixturePath = customFixturePath || path.join(ROOT, 'tools', 'fixtures', 'manifests.sample.json');
  const manifests = fs.existsSync(fixturePath) ? JSON.parse(fs.readFileSync(fixturePath, 'utf8')) : [];
  const byApp = {};
  for (const m of manifests) {
    if (!byApp[m.app_id]) byApp[m.app_id] = [];
    byApp[m.app_id].push(m);
  }

  // Load project catalog
  const projectsDir = path.join(CATALOG, 'projects');
  const projectEntries = fs.readdirSync(projectsDir);
  const projects = [];
  for (const dir of projectEntries) {
    const pjPath = path.join(projectsDir, dir, 'project.json');
    if (fs.existsSync(pjPath)) {
      const p = JSON.parse(fs.readFileSync(pjPath, 'utf8'));
      if (p.published !== false) {
        projects.push({ p, dirPath: path.join(projectsDir, dir) });
      }
    }
  }

  projects.sort((a, b) => {
    const orderA = a.p.order || 100;
    const orderB = b.p.order || 100;
    if (orderA !== orderB) return orderA - orderB;
    return a.p.name.localeCompare(b.p.name);
  });

  const sections = { app: [], library: [], other: [] };

  for (const { p, dirPath } of projects) {
    const versions = byApp[p.id] || [];
    const pid = p.id;
    const ptype = p.type || 'app';
    const [mainTitle, subTitle] = getProjectTitles(p);
    const catBadge = getProjectCategoryBadge(p);
    const badge = versions.length ? `v${esc(versions[0].version_name)}` : '';
    const projUrl = `/${pid}/`;
    const isDpm = p.device_owner && p.device_owner.enabled;
    const dpmBadgeHtml = isDpm ? `<span class='app-badge-dpm'>🛡️ Device Owner (DPM)</span>` : '';

    const iconDark = p.icon_dark || (fs.existsSync(path.join(dirPath, 'assets', 'icon_dark.svg')) ? 'icon_dark.svg' : null);
    const iconLight = p.icon_light || (fs.existsSync(path.join(dirPath, 'assets', 'icon_light.svg')) ? 'icon_light.svg' : null);

    let tabIconUrl = '';
    let iconCard = '';
    if (iconDark && iconLight && iconDark !== iconLight) {
      tabIconUrl = `/${pid}/assets/${iconDark}`;
      iconCard = `
        <img src='/${pid}/assets/${iconDark}' class='theme-dark-only' alt='${esc(mainTitle)} icon'>
        <img src='/${pid}/assets/${iconLight}' class='theme-light-only' alt='${esc(mainTitle)} icon'>
      `;
    } else if (fs.existsSync(path.join(dirPath, 'assets', 'icon.svg'))) {
      tabIconUrl = `/${pid}/assets/icon.svg`;
      iconCard = `<img src='/${pid}/assets/icon.svg' alt='${esc(mainTitle)} icon'>`;
    } else if (fs.existsSync(path.join(dirPath, 'assets', 'icon.png'))) {
      tabIconUrl = `/${pid}/assets/icon.png`;
      iconCard = `<img src='/${pid}/assets/icon.png' alt='${esc(mainTitle)} icon'>`;
    }

    const rawTags = p.tags || [];
    const ignoredTags = new Set(['android app', 'android library', 'system utility']);
    const filteredTags = rawTags.filter(t => !ignoredTags.has(t.toLowerCase()));
    const displayTags = (filteredTags.length ? filteredTags : rawTags).slice(0, 5);
    const chipsHtml = displayTags.map(t => `<span class='app-chip'>${esc(t)}</span>`).join('');

    const footerLeft = [];
    if (p.play_store_url) {
      footerLeft.push(`<a href='${esc(p.play_store_url)}' target='_blank' rel='noopener noreferrer' class='app-chip-store'>Google Play</a>`);
    } else if (badge) {
      footerLeft.push(`<span class='app-chip'>${badge}</span>`);
    } else if (p.visibility === 'public') {
      footerLeft.push(`<span class='app-chip-open'>Open Source</span>`);
    }

    const footerRight = [];
    if (p.visibility === 'public' && p.repo) {
      footerRight.push(`<a href='https://github.com/${esc(p.repo)}' target='_blank' class='btn-source'>GitHub &nearr;</a>`);
    }
    footerRight.push(`<a href='${projUrl}' class='btn-details'>Explore Product &rarr;</a>`);

    const subtitleHtml = subTitle ? `<div class='app-subtitle'>${esc(subTitle)}</div>` : '';

    const searchTerms = `${mainTitle} ${subTitle} ${p.tagline || ''} ${(p.tags || []).join(' ')}`.toLowerCase();

    const cardMarkup = `
      <div class='app-card-wrapper' data-category='${ptype}' data-search='${esc(searchTerms)}'>
        <div class='card app-card'>
          <div class='app-card-top'>
            <div class='app-card-header'>
              <div class='app-icon-wrapper'>${iconCard}</div>
              <div class='app-badges'>
                <span class='app-badge-cat'>${esc(catBadge)}</span>
                ${dpmBadgeHtml}
              </div>
            </div>
            <div class='app-title-group'>
              <h3 class='app-main-title'><a href='${projUrl}'>${esc(mainTitle)}</a></h3>
              ${subtitleHtml}
            </div>
            <p class='app-description'>${esc(p.tagline || '')}</p>
            <div class='app-chips'>${chipsHtml}</div>
          </div>
          <div class='app-card-footer'>
            <div class='app-footer-left'>${footerLeft.join('')}</div>
            <div class='app-footer-right'>${footerRight.join('')}</div>
          </div>
        </div>
      </div>
    `;

    const targetSec = sections[ptype] ? ptype : 'other';
    sections[targetSec].push(cardMarkup);

    // Copy project assets & render project page
    const projOutDir = path.join(outDir, pid);
    fs.mkdirSync(projOutDir, { recursive: true });
    const projAssetsDir = path.join(dirPath, 'assets');
    if (fs.existsSync(projAssetsDir)) {
      fs.cpSync(projAssetsDir, path.join(projOutDir, 'assets'), { recursive: true });
    }

    const projTagsHtml = (p.tags || []).map(t => `<span class='tag'>${esc(t)}</span>`).join('');
    const projLinks = [];
    if (p.play_store_url) {
      projLinks.push(`<a class='btn btn-play' href='${esc(p.play_store_url)}' target='_blank' rel='noopener noreferrer'>Get it on Google Play &nearr;</a>`);
    }
    if (p.visibility === 'public' && p.repo) {
      projLinks.push(`<a class='btn alt' href='https://github.com/${esc(p.repo)}' target='_blank' rel='noopener noreferrer'>View Source Code &nearr;</a>`);
    }
    if (fs.existsSync(path.join(dirPath, 'privacy.md'))) {
      projLinks.push(`<a class='btn alt' href='/${pid}/privacy/'>Privacy Policy</a>`);
    }
    if (fs.existsSync(path.join(dirPath, 'license.md'))) {
      projLinks.push(`<a class='btn alt' href='/${pid}/license/'>License Information</a>`);
    }

    const bannerDark = p.banner_dark || p.banner || p.banner_image;
    const bannerLight = p.banner_light || p.banner || p.banner_image;

    let heroBannerHtml = '';
    if (bannerDark && bannerLight && bannerDark !== bannerLight) {
      heroBannerHtml = `
        <div class="proj-hero-banner-wrap" style="margin:1.5rem 0 1.25rem 0;border-radius:14px;overflow:hidden;border:1px solid var(--card-border);">
          <img src="/${pid}/assets/${bannerDark}" class="theme-dark-only" alt="${esc(mainTitle)} Banner" style="width:100%;height:auto;display:block;">
          <img src="/${pid}/assets/${bannerLight}" class="theme-light-only" alt="${esc(mainTitle)} Banner" style="width:100%;height:auto;display:block;">
        </div>
      `;
    } else if (bannerDark) {
      heroBannerHtml = `
        <div class="proj-hero-banner-wrap" style="margin:1.5rem 0 1.25rem 0;border-radius:14px;overflow:hidden;border:1px solid var(--card-border);">
          <img src="/${pid}/assets/${bannerDark}" alt="${esc(mainTitle)} Banner" style="width:100%;height:auto;display:block;">
        </div>
      `;
    }

    const verBadge = versions.length ? `<span class='app-badge-ver'>v${esc(versions[0].version_name)}</span>` : '';
    const visBadge = p.visibility === 'public' ? `<span class='app-badge-open'>Open Source</span>` : '';

    const projHeroHtml = `
      <div class="proj-hero-card" id="overview">
        <div class="proj-hero-top">
          <div class="proj-icon-wrapper">${iconCard}</div>
          <div class="proj-hero-info">
            <div class="proj-badges">
              <span class="app-badge-cat">${esc(catBadge)}</span>
              ${isDpm ? `<span class='app-badge-dpm'>🛡️ Device Owner (DPM)</span>` : ''}
              ${verBadge}
              ${visBadge}
            </div>
            <h1 class="proj-hero-title">${esc(mainTitle)}</h1>
            ${subtitleHtml}
            <p class="proj-hero-tagline">${esc(p.tagline || '')}</p>
            <div class="proj-hero-tags">${projTagsHtml}</div>
          </div>
        </div>
        ${heroBannerHtml}
        <div class="proj-action-bar">
          ${projLinks.join('')}
        </div>
      </div>
    `;

    const screenshots = p.screenshots || [];
    let shotsSection = '';
    if (screenshots.length) {
      const shotImgs = screenshots.map(s => `
        <div class='shot-item'><img loading='lazy' alt='${esc(mainTitle)} visual preview' src='/${pid}/assets/${s}'></div>
      `).join('');
      shotsSection = `
        <section class="proj-section shots-container" id="showcase">
          <h2 class="proj-section-title">🖼️ Visual Showcase &amp; Highlights</h2>
          <div class="shots-scroll">${shotImgs}</div>
        </section>
      `;
    }

    const descSection = `<section class="proj-section" id="details">${mdToHtml(p.description || '')}</section>`;

    let extraSection = '';
    if (ptype === 'app') {
      if (versions.length) {
        const m = versions[0];
        extraSection = `
          <section class="proj-section" id="download">
            <h2 class="proj-section-title">📲 Version &amp; Security Metadata</h2>
            <div class="download-hero">
              <div class="download-card">
                <div>
                  <div style="font-size:0.82rem;font-weight:600;color:var(--mut);text-transform:uppercase;letter-spacing:0.5px">Latest Release Build</div>
                  <div style="font-size:1.75rem;font-weight:800;color:var(--fg);margin:0.25rem 0">v${esc(m.version_name)}</div>
                  <div style="font-size:0.88rem;color:var(--mut)">Size: <strong>${humanSize(m.size_bytes)}</strong> &bull; Min Android: <strong>API ${esc(m.min_sdk)}+</strong></div>
                </div>
              </div>
              <div class="download-card">
                <div style="font-size:0.82rem;font-weight:600;color:var(--mut);text-transform:uppercase;letter-spacing:0.5px">Cryptographic Integrity</div>
                <div style="font-size:0.82rem;margin-top:0.5rem;color:var(--mut)">
                  <strong>Binary SHA-256:</strong><br>
                  <code style="display:block;word-break:break-all;margin-top:0.2rem;font-size:0.75rem">${esc(m.sha256)}</code>
                </div>
                <div style="font-size:0.82rem;margin-top:0.5rem;color:var(--mut)">
                  <strong>Signing Certificate SHA-256:</strong><br>
                  <code style="display:block;word-break:break-all;margin-top:0.2rem;font-size:0.75rem">${esc(m.cert_sha256_hex)}</code>
                </div>
              </div>
            </div>
          </section>
        `;
      } else {
        extraSection = `
          <section class="proj-section" id="download">
            <h2 class="proj-section-title">📲 Version &amp; Security Metadata</h2>
            <p class="mut" style="margin:0">No binary release has been published yet. You can inspect the source code or install via Google Play above.</p>
          </section>
        `;
      }
    } else if (ptype === 'library') {
      const lib = p.library || {};
      const jit = lib.jitpack || '';
      const ver = lib.latest_version || 'TAG';
      extraSection = `
        <section class="proj-section" id="installation">
          <h2 class="proj-section-title">📦 Library Installation &amp; Setup</h2>
          <div class="install-card">
            <h3 style="margin:0 0 0.5rem 0;font-size:1.1rem">1. Add JitPack Repository</h3>
            <p style="color:var(--mut);font-size:0.9rem;margin:0 0 0.5rem 0">Add JitPack to your <code>settings.gradle.kts</code> or root <code>build.gradle</code> file:</p>
            <pre><code>dependencyResolutionManagement {
    repositories {
        mavenCentral()
        maven { url = uri("https://jitpack.io") }
    }
}</code></pre>
          </div>
          <div class="install-card" style="margin-bottom:0">
            <h3 style="margin:0 0 0.5rem 0;font-size:1.1rem">2. Add Gradle Dependency</h3>
            <p style="color:var(--mut);font-size:0.9rem;margin:0 0 0.5rem 0">Add the dependency to your app-level <code>build.gradle.kts</code>:</p>
            <pre><code>dependencies {
    implementation("${esc(jit)}:${esc(ver)}")
}</code></pre>
          </div>
        </section>
      `;
    } else {
      const repo = p.repo || '';
      const repoUrl = repo ? `https://github.com/${esc(repo)}` : '';
      const repoBtn = repoUrl ? `<a class='btn alt' href='${repoUrl}' target='_blank' rel='noopener noreferrer'>View Repository on GitHub &nearr;</a>` : '';
      extraSection = `
        <section class="proj-section" id="quickstart">
          <h2 class="proj-section-title">⚡ Developer Quickstart &amp; Source Access</h2>
          <div class="install-card" style="margin-bottom:0">
            <p style="color:var(--mut);font-size:0.95rem;line-height:1.6;margin:0 0 1rem 0">
              This enterprise system tool is fully configured for cloud-native containerized execution (Podman, Docker, Helm) and local development workflows.
            </p>
            <div>${repoBtn}</div>
          </div>
        </section>
      `;
    }

    const projBody = projHeroHtml + shotsSection + descSection + extraSection;

    const projectInfo = {
      id: pid,
      title: mainTitle,
      iconUrl: tabIconUrl,
      version: versions.length ? `v${versions[0].version_name}` : '',
      kind: ptype,
      hasScreenshots: !!screenshots.length,
      hasPrivacy: fs.existsSync(path.join(dirPath, 'privacy.md')),
      hasLicense: fs.existsSync(path.join(dirPath, 'license.md')),
      tagline: p.tagline || '',
      catBadge: catBadge,
      currentSubpage: 'overview'
    };

    const projHtml = page(cfg, p.name, projBody, p.tagline || '', tabIconUrl, projectInfo);
    fs.writeFileSync(path.join(projOutDir, 'index.html'), projHtml, 'utf8');

    // Generate legacy alias redirects if defined
    const aliases = p.aliases || [];
    for (const alias of aliases) {
      const aliasOutDir = path.join(outDir, alias);
      fs.mkdirSync(aliasOutDir, { recursive: true });
      const redirectHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Redirecting to ${esc(mainTitle)}...</title>
  <link rel="canonical" href="/${pid}/">
  <meta http-equiv="refresh" content="0; url=/${pid}/">
  <script>window.location.replace("/${pid}/");</script>
</head>
<body style="font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;">
  <div style="text-align: center;">
    <h2>Project Renamed to ${esc(mainTitle)}</h2>
    <p>Redirecting to <a href="/${pid}/" style="color: #6366f1;">/${pid}/</a>...</p>
  </div>
</body>
</html>`;
      fs.writeFileSync(path.join(aliasOutDir, 'index.html'), redirectHtml, 'utf8');

      if (fs.existsSync(path.join(dirPath, 'privacy.md'))) {
        const aliasPrivDir = path.join(aliasOutDir, 'privacy');
        fs.mkdirSync(aliasPrivDir, { recursive: true });
        const privRedirectHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Redirecting to ${esc(mainTitle)} Privacy Policy...</title>
  <link rel="canonical" href="/${pid}/privacy/">
  <meta http-equiv="refresh" content="0; url=/${pid}/privacy/">
  <script>window.location.replace("/${pid}/privacy/");</script>
</head>
<body style="font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0;">
  <div style="text-align: center;">
    <h2>Project Renamed to ${esc(mainTitle)}</h2>
    <p>Redirecting to <a href="/${pid}/privacy/" style="color: #6366f1;">/${pid}/privacy/</a>...</p>
  </div>
</body>
</html>`;
        fs.writeFileSync(path.join(aliasPrivDir, 'index.html'), privRedirectHtml, 'utf8');
      }
    }

    if (fs.existsSync(path.join(dirPath, 'license.md'))) {
      const licDir = path.join(projOutDir, 'license');
      fs.mkdirSync(licDir, { recursive: true });
      const licContent = fs.readFileSync(path.join(dirPath, 'license.md'), 'utf8');
      const licBody = `
        <div class="proj-hero-card" style="margin-bottom:1.5rem">
          <div style="display:flex;align-items:center;gap:0.5rem;font-size:0.85rem;font-weight:600;color:var(--acc);margin-bottom:0.5rem">
            <span>📜 License &amp; Terms Compliance</span>
          </div>
          <h1 class="proj-hero-title">${esc(mainTitle)}</h1>
          <div class="proj-hero-subtitle">Open Source License Terms &amp; Copyright Notice</div>
        </div>
        <div class="doc-card">
          ${mdToHtml(licContent)}
        </div>
      `;
      const licProjectInfo = { ...projectInfo, currentSubpage: 'license' };
      const licHtml = page(cfg, `${p.name} License Information`, licBody, p.tagline || '', tabIconUrl, licProjectInfo);
      fs.writeFileSync(path.join(licDir, 'index.html'), licHtml, 'utf8');
    }

    if (fs.existsSync(path.join(dirPath, 'privacy.md'))) {
      const privDir = path.join(projOutDir, 'privacy');
      fs.mkdirSync(privDir, { recursive: true });
      const privContent = fs.readFileSync(path.join(dirPath, 'privacy.md'), 'utf8');
      const privBody = `
        <div class="proj-hero-card" style="margin-bottom:1.5rem">
          <div style="display:flex;align-items:center;gap:0.5rem;font-size:0.85rem;font-weight:600;color:var(--acc);margin-bottom:0.5rem">
            <span>🛡️ Data Privacy &amp; Security Compliance</span>
          </div>
          <h1 class="proj-hero-title">${esc(mainTitle)}</h1>
          <div class="proj-hero-subtitle">Privacy Policy &amp; Security Standards</div>
        </div>
        <div class="doc-card">
          ${mdToHtml(privContent)}
        </div>
      `;
      const privProjectInfo = { ...projectInfo, currentSubpage: 'privacy' };
      const privHtml = page(cfg, `${p.name} Privacy Policy`, privBody, p.tagline || '', tabIconUrl, privProjectInfo);
      fs.writeFileSync(path.join(privDir, 'index.html'), privHtml, 'utf8');
    }
  }

  // Render main index page
  let body = renderProfileSections(cfg, profile, experience);
  body += `
    <section id='projects' style='margin-top:3.5rem'>
      <h2 style='font-size:1.85rem;font-weight:800;margin-bottom:0.25rem;letter-spacing:-0.02em'>Featured Software &amp; Open Source Projects</h2>
      <p class='mut' style='margin-top:0;margin-bottom:1.5rem'>A portfolio of standalone Android applications, open-source libraries, and platform tools engineered by Vivek Umrao.</p>
      <div class='project-controls'>
        <div class='search-wrapper'>
          <span class='search-icon'>🔍</span>
          <input type='text' id='project-search' class='search-input' placeholder='Search projects by name, keyword, or tech tag...' aria-label='Search projects'>
        </div>
        <div class='filter-tabs' role='tablist' aria-label='Filter Projects'>
          <button class='filter-tab active' data-filter='all' type='button'>All Projects</button>
          <button class='filter-tab' data-filter='app' type='button'>📱 Android Apps</button>
          <button class='filter-tab' data-filter='library' type='button'>📦 Libraries &amp; SDKs</button>
          <button class='filter-tab' data-filter='other' type='button'>⚙️ Systems &amp; Tools</button>
        </div>
      </div>
  `;

  const sectionTitles = [
    ['app', 'Android Applications'],
    ['library', 'Libraries & SDKs'],
    ['other', 'Enterprise Systems & Tools']
  ];

  for (const [key, title] of sectionTitles) {
    if (sections[key] && sections[key].length) {
      body += `
        <div class='project-section-wrapper' data-sec-category='${key}'>
          <h3 style='margin-top:2.25rem;font-size:1.35rem;font-weight:700'>${title}</h3>
          <div class='grid'>${sections[key].join('')}</div>
        </div>
      `;
    }
  }
  body += '</section>';

  const indexHtml = page(cfg, cfg.name || 'Home', body, cfg.tagline || '', '', null);
  fs.writeFileSync(path.join(outDir, 'index.html'), indexHtml, 'utf8');

  // Write API Catalog
  fs.mkdirSync(path.join(outDir, 'api'), { recursive: true });
  fs.writeFileSync(path.join(outDir, 'api', 'catalog.json'), JSON.stringify({
    projects: projects.map(item => item.p),
    latest: Object.fromEntries(Object.entries(byApp).map(([k, v]) => [k, v[0]]))
  }, null, 2), 'utf8');

  console.log(`Successfully built ${projects.length} projects into ${outDir}`);
}

let outDir = path.join(ROOT, 'dist');
let fixturePath = null;
let shouldServe = false;

const args = process.argv.slice(2);
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--out' && i + 1 < args.length) {
    outDir = path.resolve(ROOT, args[++i]);
  } else if (args[i] === '--fixture' && i + 1 < args.length) {
    fixturePath = path.resolve(ROOT, args[++i]);
  } else if (args[i] === '--serve') {
    shouldServe = true;
  }
}

// Build static site into target directory
buildSite(outDir, fixturePath);

// Serve static site via local HTTP server only if requested or run interactively
if (shouldServe || args.length === 0) {
  const PORT = 8000;
  const MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.svg': 'image/svg+xml',
    '.jpg': 'image/jpeg',
    '.png': 'image/png',
    '.ico': 'image/x-icon'
  };

  const server = http.createServer((req, res) => {
    let reqPath = req.url.split('?')[0];
    if (reqPath.endsWith('/')) {
      reqPath += 'index.html';
    }
    let filePath = path.join(outDir, reqPath);
    if (fs.existsSync(filePath) && fs.statSync(filePath).isDirectory()) {
      filePath = path.join(filePath, 'index.html');
    }

    if (!fs.existsSync(filePath)) {
      res.writeHead(404, { 'Content-Type': 'text/html' });
      res.end('<h1>404 Not Found</h1>');
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': contentType });
    fs.createReadStream(filePath).pipe(res);
  });

  server.listen(PORT, '127.0.0.1', () => {
    console.log(`\n🚀 Portfolio Site is live & ready to view!`);
    console.log(`👉 Open http://localhost:${PORT} in your browser.`);
  });
}
