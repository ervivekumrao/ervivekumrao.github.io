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

function page(cfg, title, body, desc = '', iconUrl = '', breadcrumbs = null, showHomeBrand = false) {
  const iconHref = iconUrl ? iconUrl : '/favicon.svg';
  const iconType = iconHref.endsWith('.svg') ? 'image/svg+xml' : 'image/png';

  const ribbonItems = [];
  if (breadcrumbs && breadcrumbs.length) {
    const totalCrumbs = breadcrumbs.length;
    breadcrumbs.forEach((crumb, i) => {
      const label = crumb[0];
      const link = crumb[1];
      const isCurrent = crumb.length > 2 ? !!crumb[2] : (link === '');

      const isFirst = i === 0;
      const isLast = i === totalCrumbs - 1;

      const classes = ['ribbon-item'];
      if (isFirst) classes.push('ribbon-first');
      if (isLast) classes.push('ribbon-last');
      if (isCurrent) classes.push('ribbon-current');
      else classes.push('ribbon-sublink');

      const classStr = classes.join(' ');
      const content = `<span>${esc(label)}</span>`;

      if (link && link !== '') {
        ribbonItems.push(`<a href='${esc(link)}' class='${classStr}'>${content}</a>`);
      } else {
        ribbonItems.push(`<span class='${classStr}'>${content}</span>`);
      }
    });
  } else {
    const homeSections = [
      ['⚡ Overview', '#overview', 'overview'],
      ['Experience', '#experience', 'experience'],
      ['Core Skills', '#competencies', 'competencies'],
      ['Featured Projects', '#projects', 'projects']
    ];
    const totalSections = homeSections.length;
    homeSections.forEach(([label, link, secId], i) => {
      const isFirst = i === 0;
      const isLast = i === totalSections - 1;
      const classes = ['ribbon-item ribbon-section'];
      if (isFirst) classes.push('ribbon-first ribbon-active');
      if (isLast) classes.push('ribbon-last');
      const classStr = classes.join(' ');
      ribbonItems.push(`<a href='${esc(link)}' class='${classStr}' data-section='${secId}'><span>${esc(label)}</span></a>`);
    });
  }

  const crumbHtml = `<nav class='ribbon-nav' aria-label='Breadcrumb'>${ribbonItems.join('')}</nav>`;

  return `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<script>(function(){var t;try{t=localStorage.getItem("theme");}catch(e){}if(!t){t="dark";}document.documentElement.setAttribute("data-theme",t);})();</script>
<title>${esc(title)} · ${esc(cfg.name)}</title><meta name="description" content="${esc(desc || cfg.tagline)}">
<link rel="icon" type="${iconHref}">
<link rel="apple-touch-icon" href="${iconHref}">
<link rel="stylesheet" href="/style.css"></head><body>
<header>
  <div>
    <div class="header-left">
      ${crumbHtml}
    </div>
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
${body}
</main>
<script>
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
  var navLinks = document.querySelectorAll(".ribbon-section[data-section]");
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
        if(idx <= activeIdx){
          link.classList.add("ribbon-active");
        } else {
          link.classList.remove("ribbon-active");
        }
      });
    }
    window.addEventListener("scroll", updateProgress, {passive: true});
    updateProgress();
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
</script>
</body></html>`;
}

function renderProfileSections(cfg, profile, experience) {
  const profileUrl = profile.profile_image || '/profile.jpg';
  const socialBtns = (profile.social_links || []).map(link => {
    const btnClass = link.primary ? 'btn' : 'btn alt';
    const target = link.url.startsWith('http') ? ' target="_blank"' : '';
    return `<a href="${esc(link.url)}" class="${btnClass}"${target}>${esc(link.label)}</a>`;
  }).join('');

  const statsHtml = (profile.stats || []).map(stat => `
    <div>
      <div style="font-size:1.75rem;font-weight:700;color:var(--acc)">${esc(stat.value)}</div>
      <div style="font-size:0.85rem;color:var(--mut);font-weight:500">${esc(stat.label)}</div>
    </div>
  `).join('');

  const heroHtml = `<div class="hero-box" id="overview">
<div style="display:flex;gap:2rem;align-items:center;flex-wrap:wrap">
  <div style="flex:1;min-width:280px">
    <div style="display:inline-flex;align-items:center;background:var(--tag-bg);color:var(--tag-fg);padding:0.3rem 0.8rem;border-radius:99px;font-size:0.85rem;font-weight:500;margin-bottom:1rem">
      <span style="width:8px;height:8px;background:#10b981;border-radius:50%;display:inline-block;margin-right:0.5rem"></span>
      ${esc(profile.status_badge || 'Available for new opportunities')}
    </div>
    <h1 style="margin:0 0 0.75rem 0;font-size:2.5rem;letter-spacing:-0.03em">${esc(profile.headline || "Hi, I'm Vivek Umrao.")}</h1>
    <p class="lead" style="font-size:1.1rem;line-height:1.65;color:var(--mut);margin-bottom:1.5rem">
      <em>${esc(profile.quote || '')}</em> ${esc(profile.summary || '')}
    </p>
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap">
      ${socialBtns}
    </div>
  </div>
  <div style="flex-shrink:0">
    <img src="${profileUrl}" alt="${esc(profile.name || 'Vivek Umrao')}" style="width:160px;height:160px;border-radius:50%;object-fit:cover;border:3px solid var(--card-border);box-shadow:var(--card-shadow)">
  </div>
</div>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-top:2rem;padding-top:1.5rem;border-top:1px solid var(--line)">
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
<h2 style="font-size:1.75rem;margin-bottom:0.25rem">Professional Experience</h2>
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
<h2 style="font-size:1.75rem;margin-bottom:0.25rem">Core Competencies &amp; Technical Skills</h2>
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

    let iconCard = '';
    if (iconDark && iconLight && iconDark !== iconLight) {
      iconCard = `
        <img src='/${pid}/assets/${iconDark}' class='theme-dark-only' alt='${esc(mainTitle)} icon'>
        <img src='/${pid}/assets/${iconLight}' class='theme-light-only' alt='${esc(mainTitle)} icon'>
      `;
    } else if (fs.existsSync(path.join(dirPath, 'assets', 'icon.svg'))) {
      iconCard = `<img src='/${pid}/assets/icon.svg' alt='${esc(mainTitle)} icon'>`;
    } else if (fs.existsSync(path.join(dirPath, 'assets', 'icon.png'))) {
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
    footerRight.push(`<a href='${projUrl}' class='btn-details'>Details &rarr;</a>`);

    const subtitleHtml = subTitle ? `<div class='app-subtitle'>${esc(subTitle)}</div>` : '';

    const cardMarkup = `
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
    if (versions.length && versions[0].url_latest) {
      projLinks.push(`<a class='btn btn-download' href='${esc(versions[0].url_latest)}'>⚡ Download APK (v${esc(versions[0].version_name)})</a>`);
    }
    if (p.visibility === 'public' && p.repo) {
      projLinks.push(`<a class='btn alt' href='https://github.com/${esc(p.repo)}' target='_blank' rel='noopener noreferrer'>View Source Code &nearr;</a>`);
    }

    if (ptype === 'library' || fs.existsSync(path.join(dirPath, 'license.md'))) {
      if (fs.existsSync(path.join(dirPath, 'license.md'))) {
        projLinks.push(`<a class='btn alt' href='/${pid}/license/'>License Information</a>`);
      }
      if (fs.existsSync(path.join(dirPath, 'privacy.md'))) {
        projLinks.push(`<a class='btn alt' href='/${pid}/privacy/'>Privacy Policy</a>`);
      }
    } else {
      if (fs.existsSync(path.join(dirPath, 'privacy.md'))) {
        projLinks.push(`<a class='btn alt' href='/${pid}/privacy/'>Privacy Policy</a>`);
      }
      if (fs.existsSync(path.join(dirPath, 'license.md'))) {
        projLinks.push(`<a class='btn alt' href='/${pid}/license/'>License Information</a>`);
      }
    }

    const bannerDark = p.banner_dark || p.banner || p.banner_image;
    const bannerLight = p.banner_light || p.banner || p.banner_image;

    let heroBannerHtml = '';
    if (bannerDark && bannerLight && bannerDark !== bannerLight) {
      heroBannerHtml = `
        <div class="proj-hero-banner-wrap" style="margin:1.5rem 0 1.25rem 0;border-radius:12px;overflow:hidden;border:1px solid var(--brd);">
          <img src="/${pid}/assets/${bannerDark}" class="theme-dark-only" alt="${esc(mainTitle)} Banner" style="width:100%;height:auto;display:block;">
          <img src="/${pid}/assets/${bannerLight}" class="theme-light-only" alt="${esc(mainTitle)} Banner" style="width:100%;height:auto;display:block;">
        </div>
      `;
    } else if (bannerDark) {
      heroBannerHtml = `
        <div class="proj-hero-banner-wrap" style="margin:1.5rem 0 1.25rem 0;border-radius:12px;overflow:hidden;border:1px solid var(--brd);">
          <img src="/${pid}/assets/${bannerDark}" alt="${esc(mainTitle)} Banner" style="width:100%;height:auto;display:block;">
        </div>
      `;
    }

    const projHeroHtml = `
      <div class="proj-hero-card">
        <div class="proj-hero-top">
          <div class="proj-icon-wrapper">${iconCard}</div>
          <div class="proj-hero-info">
            <div class="proj-badges">
              <span class="app-badge-cat">${esc(catBadge)}</span>
              ${dpmBadgeHtml}
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

    const descSection = `<section class="proj-section">${p.description || ''}</section>`;
    const projBody = projHeroHtml + descSection;

    const projBreadcrumbs = [[mainTitle, '', true]];
    if (ptype === 'library' || fs.existsSync(path.join(dirPath, 'license.md'))) {
      if (fs.existsSync(path.join(dirPath, 'license.md'))) {
        projBreadcrumbs.push(['License Information', `/${pid}/license/`, false]);
      }
      if (fs.existsSync(path.join(dirPath, 'privacy.md'))) {
        projBreadcrumbs.push(['Privacy Policy', `/${pid}/privacy/`, false]);
      }
    } else {
      if (fs.existsSync(path.join(dirPath, 'privacy.md'))) {
        projBreadcrumbs.push(['Privacy Policy', `/${pid}/privacy/`, false]);
      }
      if (fs.existsSync(path.join(dirPath, 'license.md'))) {
        projBreadcrumbs.push(['License Information', `/${pid}/license/`, false]);
      }
    }

    const projHtml = page(cfg, p.name, projBody, p.tagline || '', '', projBreadcrumbs);
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
        <div class="proj-footer-nav">
          <a href="/${pid}/" class="btn alt">&larr; Back to ${esc(mainTitle)} Overview</a>
          <a href="#" onclick="window.scrollTo({top: 0, behavior: 'smooth'}); return false;" class="btn alt">&uarr; Back to Top</a>
        </div>
      `;
      const licCrumbs = [[mainTitle, `/${pid}/`, true], ['License Information', '', true]];
      if (fs.existsSync(path.join(dirPath, 'privacy.md'))) {
        licCrumbs.push(['Privacy Policy', `/${pid}/privacy/`, false]);
      }
      const licHtml = page(cfg, `${p.name} License Information`, licBody, p.tagline || '', '', licCrumbs);
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
        <div class="proj-footer-nav">
          <a href="/${pid}/" class="btn alt">&larr; Back to ${esc(mainTitle)} Overview</a>
          <a href="#" onclick="window.scrollTo({top: 0, behavior: 'smooth'}); return false;" class="btn alt">&uarr; Back to Top</a>
        </div>
      `;
      const privCrumbs = [[mainTitle, `/${pid}/`, true], ['Privacy Policy', '', true]];
      if (fs.existsSync(path.join(dirPath, 'license.md'))) {
        privCrumbs.push(['License Information', `/${pid}/license/`, false]);
      }
      const privHtml = page(cfg, `${p.name} Privacy Policy`, privBody, p.tagline || '', '', privCrumbs);
      fs.writeFileSync(path.join(privDir, 'index.html'), privHtml, 'utf8');
    }
  }

  // Render main index page
  let body = renderProfileSections(cfg, profile, experience);
  body += `<section id='projects' style='margin-top:3rem'><h2 style='font-size:1.75rem;margin-bottom:0.25rem'>Featured Software & Open Source Projects</h2><p class='mut' style='margin-top:0;margin-bottom:1.5rem'>A portfolio of apps, open-source libraries, and tools built to solve specific platform engineering bottlenecks.</p>`;

  const sectionTitles = [
    ['app', 'Android Applications'],
    ['library', 'Libraries & SDKs'],
    ['other', 'Enterprise Systems & Tools']
  ];

  for (const [key, title] of sectionTitles) {
    if (sections[key] && sections[key].length) {
      body += `<h3 style='margin-top:2rem;font-size:1.35rem'>${title}</h3><div class='grid'>${sections[key].join('')}</div>`;
    }
  }
  body += '</section>';

  const indexHtml = page(cfg, cfg.name || 'Home', body, cfg.tagline || '', '', null, true);
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
