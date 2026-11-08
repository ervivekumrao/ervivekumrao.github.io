# Architecture Assessment Findings Ledger: ervivekumrao.github.io

---

### Finding ID: ARCH-01
- **Title**: Hardcoded Resume & Competency Content Embedded in CLI Entrypoint Code
- **Category**: Layering & Separation of Concerns / Evolvability
- **Severity**: High
- **Confidence**: High (Observed)
- **File & Line**: `tools/build_site.py:155-322`
- **Code Snippet**:
```python
# tools/build_site.py:155-175
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
...
```
- **Consequence**: Content updates (such as adding a job, updating technical skills, or changing profile text) require modifying executable Python code in `tools/build_site.py`. This violates the Separation of Content and Presentation, makes content editing error-prone, and increases risk of introducing syntax bugs during routine resume updates.
- **Recommendation**: Move hero text, work experience history, and core competency skill groups into structured JSON catalog files (e.g., `catalog/profile.json` or `catalog/experience.json`) and update builder tools to render them declaratively.

---

### Finding ID: ARCH-02
- **Title**: Duplicated Project Category & Badge Determination Logic
- **Category**: Code Reuse & Modularization / DRY Violation
- **Severity**: Medium
- **Confidence**: High (Observed)
- **File & Line**: `tools/build_site.py:65-75` and `tools/builder/renderers.py:183-193`
- **Code Snippet**:
```python
# tools/build_site.py:65-75
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
```
- **Consequence**: The mapping logic from project metadata to category badge label is duplicated word-for-word in two separate files. Any changes or additions to categories must be updated in both files, leading to UI inconsistencies if one is updated without the other.
- **Recommendation**: Extract category badge determination into a single helper function in `tools/builder/utils.py` or `renderers.py` and call it consistently.

---

### Finding ID: ARCH-03
- **Title**: Hardcoded Project ID Conditional Branching in Core Rendering Pipeline
- **Category**: Evolvability & Domain Boundaries
- **Severity**: Medium
- **Confidence**: High (Observed)
- **File & Line**: `tools/build_site.py:68-75` and `tools/builder/renderers.py:187-193`
- **Code Snippet**:
```python
# tools/builder/renderers.py:187-193
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
```
- **Consequence**: Adding a new project with custom category requirements requires adding `if pid == "..."` branches inside the generator code. This hardcoding couples the generator logic directly to specific catalog data instances instead of supporting metadata-driven configuration (e.g. `category_badge` or `category` field in `project.json`).
- **Recommendation**: Support an optional `category_badge` attribute directly in `project.json` schema, falling back to a clean default based on project `type`.

---

### Finding ID: ARCH-04
- **Title**: CSS Asset Encapsulated as Multi-line Python String Constant
- **Category**: Maintainability & Asset Management
- **Severity**: Medium
- **Confidence**: High (Observed)
- **File & Line**: `tools/builder/styles.py:3-167`
- **Code Snippet**:
```python
# tools/builder/styles.py:3-10
CSS = """
:root{--bg:#f8fafc;--fg:#0f172a;--mut:#64748b;--card:#ffffff;--card-border:#e2e8f0;--card-shadow:0 4px 14px -2px rgba(0,0,0,0.06);--line:#e2e8f0;--acc:#2563eb;--acc-hover:#1d4ed8;--acc-glow:rgba(37,99,235,0.12);--tag-bg:#f1f5f9;--tag-fg:#334155}
@media(prefers-color-scheme:dark){:root{--bg:#0b0f19;--fg:#f8fafc;--mut:#94a3b8;--card:#131b2e;--card-border:#1e293b;--card-shadow:0 4px 20px -2px rgba(0,0,0,0.35);--line:#1e293b;--acc:#38bdf8;--acc-hover:#0284c7;--acc-glow:rgba(56,189,248,0.2);--tag-bg:#1e293b;--tag-fg:#cbd5e1}}
...
"""
```
- **Consequence**: Developers lose CSS editor syntax highlighting, formatting, static analysis, and CSS minification/linting tools. Editing styles requires modifying python code files, and prevents external web development toolchains from interacting with site assets.
- **Recommendation**: Move `styles.py` string content to a standalone CSS file `static/style.css` (or `tools/templates/style.css`), allowing the generator to copy or serve static CSS directly.

---

### Finding ID: ARCH-05
- **Title**: Sequential Synchronous HTTP Request Loop in GitHub API Release Fetcher
- **Category**: Scalability, Performance & Reliability
- **Severity**: Low
- **Confidence**: High (Observed)
- **File & Line**: `tools/builder/github_api.py:18-35`
- **Code Snippet**:
```python
# tools/builder/github_api.py:18-34
def fetch_manifests(repo: str, token: Optional[str]) -> list[dict]:
    """Fetches manifest.json assets from non-draft, non-prerelease releases in the GitHub repo."""
    out, page = [], 1
    while True:
        rels = http_json(f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}", token)
        if not rels:
            break
        for rel in rels:
            if rel.get("draft") or rel.get("prerelease"):
                continue
            asset = next((a for a in rel.get("assets", []) if a["name"] == "manifest.json"), None)
            if asset:
                try:
                    out.append(http_json(asset["browser_download_url"]))
                except Exception as e:
                    print(f"warn: skipping {rel.get('tag_name')}: {e}", file=sys.stderr)
        page += 1
    return out
```
- **Consequence**: `fetch_manifests` sequentially executes blocking `http_json` requests for every release containing a manifest. As the number of releases grows, site build times scale linearly (`O(N)` network roundtrips). A single slow response stalls the build.
- **Recommendation**: Implement concurrent asset fetching using `concurrent.futures.ThreadPoolExecutor` or `asyncio`, bounded by a worker pool size (e.g. 5-10 threads), and add timeouts.

---

### Finding ID: ARCH-06
- **Title**: Defense-in-Depth Authorization Header Risk in `http_json` Utility
- **Category**: Security Architecture & Data Protection
- **Severity**: Low
- **Confidence**: Medium (Observed / Inferred)
- **File & Line**: `tools/builder/github_api.py:10-14`
- **Code Snippet**:
```python
# tools/builder/github_api.py:10-14
def http_json(url: str, token: Optional[str] = None):
    """Fetches a JSON response from an HTTP URL, supporting optional Bearer auth token."""
    headers = {"User-Agent": "app-hub-builder"}
    if token:  # only for api.github.com, never for download redirects
        headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
```
- **Consequence**: Standard Python `urllib.request.urlopen` automatically follows HTTP redirects (such as 302 redirects from `api.github.com` or `github.com` to AWS S3 storage `objects.githubusercontent.com`). If a caller accidentally passes `token` to `http_json` for a URL that redirects off GitHub's API domain, `urllib` will re-send the `Authorization: Bearer <token>` header to the redirected host.
- **Recommendation**: Add a hostname check inside `http_json` ensuring `Authorization` headers are only attached if the URL scheme and domain match `https://api.github.com/`.

---

### Finding ID: ARCH-07
- **Title**: Missing End-to-End Build Integration Test & Catalog Schema Validation
- **Category**: Testing Strategy & Gaps / Quality Gate
- **Severity**: Medium
- **Confidence**: High (Observed)
- **File & Line**: `tests/test_builder.py:1-156`
- **Code Snippet**:
```python
# tests/test_builder.py:115-136
class TestSiteRendering(unittest.TestCase):
    """Integration test for site output generation."""
    ...
    def test_site_write_and_page(self):
        page_html = self.site.page("Test Page", "<h1>Content</h1>", show_home_brand=True)
        self.site.write("test.html", page_html)
        ...
```
- **Consequence**: `tests/test_builder.py` tests individual utility functions and a basic `Site` object mock, but does not test running `build_site.py` against actual project catalog entries (`catalog/projects/`). A syntax error in `project.json` or broken image path in catalog data will pass unit tests but break site generation in CI.
- **Recommendation**: Add a full end-to-end integration test in `test_builder.py` that invokes `build_site.main()` with `--out` targeting a temporary directory and `--fixture` targeting sample manifests, verifying that all HTML files, assets, and JSON endpoints are correctly generated.

---

### Finding ID: ARCH-08
- **Title**: Inline Python Scripting in Reusable GitHub Actions Release Workflow
- **Category**: CI/CD & Maintainability
- **Severity**: Low
- **Confidence**: High (Observed)
- **File & Line**: `.github/workflows/android-release.yml:58-90`
- **Code Snippet**:
```yaml
      - name: Build manifest, checksums, release notes
        run: |
          python3 - <<'PY'
          import base64, hashlib, json, os, re, subprocess, datetime
          t = os.environ["RUNNER_TEMP"]; bt = os.environ["BUILD_TOOLS"]
          ...
          PY
```
- **Consequence**: 35+ lines of inline Python code embedded in a multiline YAML heredoc string cannot be linted, unit-tested, or type-checked locally. Modifying manifest generation logic requires pushing changes to CI to test.
- **Recommendation**: Move the release manifest builder Python script to a standalone CLI script in `tools/generate_manifest.py` and call it from `android-release.yml`.
