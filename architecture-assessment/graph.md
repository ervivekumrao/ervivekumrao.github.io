# Dependency Graph & Module Import Analysis

## Python Dependency Tree

```
tools/build_site.py
  ├── imports standard library: argparse, json, os, shutil, sys, pathlib.Path
  ├── imports tools.builder.utils: esc, get_project_titles
  ├── imports tools.builder.github_api: fetch_manifests
  ├── imports tools.builder.styles: CSS
  └── imports tools.builder.renderers: Site, render_project

tools/builder/renderers.py
  ├── imports standard library: base64, json, shutil, pathlib.Path, typing
  ├── imports tools.builder.utils: esc, human_size, md_to_html, get_project_titles
  └── optional import: segno (QR code generator)

tools/builder/github_api.py
  └── imports standard library: json, sys, urllib.request, typing.Optional

tools/builder/styles.py
  └── no internal imports (exports string constant `CSS`)

tools/builder/utils.py
  ├── imports standard library: html, sys
  └── optional import: markdown

tests/test_builder.py
  ├── imports standard library: json, shutil, tempfile, unittest, pathlib.Path, unittest.mock.patch
  ├── imports tools.builder.utils: esc, human_size, md_to_html, get_project_titles
  ├── imports tools.builder.github_api: fetch_manifests
  └── imports tools.builder.renderers: Site, enrollment_payload
```

## Dependency Coupling Matrix

| Source Module | Target Module | Dependency Type | Risk / Note |
|---|---|---|---|
| `build_site.py` | `utils.py` | Function import (`esc`, `get_project_titles`) | Low |
| `build_site.py` | `github_api.py` | Function import (`fetch_manifests`) | Low |
| `build_site.py` | `styles.py` | Variable import (`CSS`) | Low |
| `build_site.py` | `renderers.py` | Class/Function import (`Site`, `render_project`) | High - `build_site.py` duplicates card & badge rendering logic from `renderers.py` |
| `renderers.py` | `utils.py` | Function import (`esc`, `human_size`, `md_to_html`, `get_project_titles`) | Low |
| `github_api.py` | None (Internal) | Standard Library | Low |
| `styles.py` | None (Internal) | None | Medium - CSS embedded in Python source |

## Cyclic Dependencies
- **Result**: No cyclic imports detected between Python files.
