# Architectural Hotspots & Size / Complexity Analysis

## File Size & Complexity Hotspots

| Path | Lines of Code | Primary Concern |
|---|---|---|
| `tools/build_site.py` | 430 lines | High complexity, presentation logic mixing, hardcoded HTML blocks (160+ LOC of resume/hero HTML), duplicated category badge branching. |
| `tools/builder/renderers.py` | 412 lines | High complexity, inline HTML template strings, hardcoded project ID branches, embedded JavaScript strings. |
| `tools/builder/styles.py` | 167 lines | Asset encapsulation violation (225+ lines of raw CSS embedded as Python string). |
| `tests/test_builder.py` | 156 lines | Adequate unit testing, missing full end-to-end integration test of `build_site.py`. |
| `.github/workflows/android-release.yml` | 136 lines | Inline Python script step (40 lines) embedded inside YAML step without standalone module or linting. |

## Code Hotspot Analysis
1. **`build_site.py:155-322`**: Contains 167 lines of hardcoded HTML string literals representing Vivek Umrao's resume, experience, and competencies. Any content update requires editing Python script code.
2. **`renderers.py:183-193` & `build_site.py:65-75`**: Duplicated logic mapping `type` and `id` to category badges ("📱 Android App", "📦 Android SDK", "⚡ Microservices & AI", "🛠️ Developer CLI", "⚡ JVM JIT Engine", "🔒 Cryptographic Vault", "⚙️ System Tool").
3. **`github_api.py:18-35`**: Sequential network fetching loop over releases; single HTTP failure or slow response stalls the entire site build.
