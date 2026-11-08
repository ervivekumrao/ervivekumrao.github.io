# Architecture Fitness Functions: ervivekumrao.github.io

This document defines executable architecture fitness functions and compliance rules to ensure architectural invariants are automatically enforced in CI/CD.

---

## Fitness Rule 1: No Hardcoded Project IDs in Core Renderers
- **Objective**: Ensure that `tools/builder/renderers.py` and `tools/builder/utils.py` do not contain hardcoded project ID strings (e.g. `if pid == "agenticinventory"`). Project metadata must be driven entirely by catalog declarations.
- **Enforcement Test**: `test_no_hardcoded_project_ids()` in `tests/test_architecture_fitness.py`.

```python
import re
from pathlib import Path

def test_no_hardcoded_project_ids():
    renderer_code = Path("tools/builder/renderers.py").read_text()
    utils_code = Path("tools/builder/utils.py").read_text()
    
    # Matches hardcoded project IDs like pid == "agenticinventory"
    pattern = r'pid\s*==\s*["\'](agenticinventory|spindb|jitforge|tomcatvault)["\']'
    assert not re.search(pattern, renderer_code), "Found hardcoded project IDs in renderers.py"
    assert not re.search(pattern, utils_code), "Found hardcoded project IDs in utils.py"
```

---

## Fitness Rule 2: Complete Separation of Catalog Content & Presentation Code
- **Objective**: Ensure `tools/build_site.py` does not contain inline HTML resume strings (`hero_html`, `exp_html`, `comp_html`). Content must reside in `catalog/`.
- **Enforcement Test**: `test_no_embedded_resume_html_in_cli()` in `tests/test_architecture_fitness.py`.

```python
from pathlib import Path

def test_no_embedded_resume_html_in_cli():
    cli_code = Path("tools/build_site.py").read_text()
    forbidden_tokens = ["hero_html =", "exp_html =", "comp_html =", "Pegasystems", "Samsung R&D"]
    for token in forbidden_tokens:
        assert token not in cli_code, f"Forbidden hardcoded content '{token}' found in build_site.py"
```

---

## Fitness Rule 3: Single Source of Truth for Category Badges
- **Objective**: Ensure category badge mapping logic is defined in a single function in `tools/builder/utils.py` and not duplicated across `build_site.py` and `renderers.py`.
- **Enforcement Test**: `test_single_category_badge_definition()` in `tests/test_architecture_fitness.py`.

```python
from pathlib import Path

def test_single_category_badge_definition():
    cli_code = Path("tools/build_site.py").read_text()
    renderers_code = Path("tools/builder/renderers.py").read_text()
    
    assert 'cat_badge = "📱 Android App"' not in cli_code, "Category badge logic duplicated in build_site.py"
    assert 'cat_badge = "📱 Android App"' not in renderers_code, "Category badge logic duplicated in renderers.py"
```

---

## Fitness Rule 4: Domain Isolation for Bearer Auth Tokens
- **Objective**: Prevent Bearer authorization tokens from being passed to non-GitHub API endpoints.
- **Enforcement Test**: `test_github_api_header_sanitization()` in `tests/test_architecture_fitness.py`.

```python
from tools.builder.github_api import http_json
import pytest

def test_github_api_header_sanitization():
    # Attempting to send token to non-api.github.com domain should fail or strip header
    with pytest.raises(ValueError, match="Bearer tokens are strictly restricted to api.github.com"):
        http_json("https://example.com/api", token="secret_token")
```
