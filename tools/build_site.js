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
  const pid = p.id || '';
  if (ptype === 'app') return '📱 Android App';
  if (ptype === 'library') return '📦 Android SDK';
  if (pid === 'agenticinventory') return '⚡ Microservices & AI';
  if (pid === 'spindb') return '🛠️ Developer CLI';
  if (pid === 'jitforge') return '⚡ JVM JIT Engine';
  if (pid === 'tomcatvault') return '🔒 Cryptographic Vault';
  return '⚙️ System Tool';
}

function mdToHtml(text) {
  if (!text) return '';
  if (text.trim().startsWith('<')) return text;
  return `<pre>${esc(text)}</pre>`;
}

function page(cfg, title, body, desc = '', iconUrl = '', breadcrumbs = null, showHomeBrand = false) {
  const iconHref = iconUrl ? iconUrl : '/favicon.svg';
  const iconType = iconHref.endsWith('.svg') ? 'image/svg+xml' : 'image/png';
  let crumbHtml = '';
  if (breadcrumbs) {
    const crumbsRendered = breadcrumbs.map(([label, link]) => {
      return link ? `<a href='${esc(link)}'>${esc(label)}</a>` : `<span class='current'>${esc(label)}</span>`;
    });
    crumbHtml = `<nav class='breadcrumb' aria-label='Breadcrumb'>${crumbsRendered.join(' <span class="sep">&rsaquo;</span> ')}</nav>`;
  }
  const homeIconSvg = `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>`;
  const brandHtml = showHomeBrand ? `<a href="/" class="nav-brand-home" aria-label="Home">${homeIconSvg}</a>` : '<div></div>';

  return `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<script>(function(){var t;try{t=localStorage.getItem("theme");}catch(e){}if(!t){t=window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";}document.documentElement.setAttribute("data-theme",t);})();</script>
<title>${esc(title)} · ${esc(cfg.name)}</title><meta name="description" content="${esc(desc || cfg.tagline)}">
<link rel="icon" type="${iconHref}">
<link rel="apple-touch-icon" href="${iconHref}">
<link rel="stylesheet" href="/style.css"></head><body>
<header>
  <div>
    ${brandHtml}
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
${crumbHtml}
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

  const heroHtml = `<div class="hero-box">
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

  const expHtml = `<section style="margin-top:3.5rem">
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

  const compHtml = `<section style="margin-top:3.5rem">
<h2 style="font-size:1.75rem;margin-bottom:0.25rem">Core Competencies &amp; Technical Skills</h2>
<p class="mut" style="margin-top:0;margin-bottom:1.5rem">Systematic domain expertise, runtime architectures, and enterprise technologies from 15+ years of systems engineering.</p>

<div class="comp-grid">
  ${compCards}
</div>
</section>`;

  return heroHtml + expHtml + compHtml;
}

function buildSite(outDir) {
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
  const fixturePath = path.join(ROOT, 'tools', 'fixtures', 'manifests.sample.json');
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

    const iconCard = fs.existsSync(path.join(dirPath, 'assets', 'icon.svg'))
      ? `<img src='/${pid}/assets/icon.svg' alt='${esc(mainTitle)} icon'>`
      : fs.existsSync(path.join(dirPath, 'assets', 'icon.png'))
      ? `<img src='/${pid}/assets/icon.png' alt='${esc(mainTitle)} icon'>`
      : '';

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
        <div class="proj-action-bar">
          ${projLinks.join('')}
        </div>
      </div>
    `;

    const descSection = `<section class="proj-section">${p.description || ''}</section>`;
    const projBody = projHeroHtml + descSection;
    const projHtml = page(cfg, p.name, projBody, p.tagline || '');
    fs.writeFileSync(path.join(projOutDir, 'index.html'), projHtml, 'utf8');
  }

  // Render main index page
  let body = renderProfileSections(cfg, profile, experience);
  body += `<section style='margin-top:3rem'><h2 style='font-size:1.75rem;margin-bottom:0.25rem'>Featured Software & Open Source Projects</h2><p class='mut' style='margin-top:0;margin-bottom:1.5rem'>A portfolio of apps, open-source libraries, and tools built to solve specific platform engineering bottlenecks.</p>`;

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

// Build static site into dist/
const outDir = path.join(ROOT, 'dist');
buildSite(outDir);

// Serve static site via local HTTP server
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
