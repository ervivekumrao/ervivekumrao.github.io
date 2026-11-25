"""Architecture Fitness Functions & Invariant Enforcers for the App Hub SSG."""
from __future__ import annotations
import json
import re
import unittest
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.builder.github_api import http_json


class TestArchitectureFitness(unittest.TestCase):
    """Executable fitness functions to prevent architectural regression."""

    def test_no_hardcoded_project_ids_in_renderers_and_utils(self):
        renderers_code = (ROOT / "tools" / "builder" / "renderers.py").read_text(encoding="utf-8")
        utils_code = (ROOT / "tools" / "builder" / "utils.py").read_text(encoding="utf-8")
        js_code = (ROOT / "tools" / "build_site.js").read_text(encoding="utf-8")

        pattern = r'pid\s*===\s*["\'](agenticinventory|spindb|jitforge|tomcatvault)["\']|pid\s*==\s*["\'](agenticinventory|spindb|jitforge|tomcatvault)["\']'
        self.assertIsNone(re.search(pattern, renderers_code), "Found hardcoded project IDs in renderers.py")
        self.assertIsNone(re.search(pattern, utils_code), "Found hardcoded project IDs in utils.py")
        self.assertIsNone(re.search(pattern, js_code), "Found hardcoded project IDs in build_site.js")

    def test_no_embedded_resume_html_in_cli(self):
        cli_code = (ROOT / "tools" / "build_site.py").read_text(encoding="utf-8")
        forbidden_tokens = ["hero_html =", "exp_html =", "comp_html ="]
        for token in forbidden_tokens:
            self.assertNotIn(token, cli_code, f"Forbidden embedded content token '{token}' found in build_site.py")

    def test_single_category_badge_definition(self):
        cli_code = (ROOT / "tools" / "build_site.py").read_text(encoding="utf-8")
        renderers_code = (ROOT / "tools" / "builder" / "renderers.py").read_text(encoding="utf-8")

        self.assertNotIn('cat_badge = "📱 Android App"', cli_code, "Category badge logic duplicated in build_site.py")
        self.assertNotIn('cat_badge = "📱 Android App"', renderers_code, "Category badge logic duplicated in renderers.py")

    def test_github_api_header_sanitization(self):
        with self.assertRaises(ValueError):
            http_json("https://example.com/api", token="secret_token")

    def test_catalog_project_ids_and_assets_exist(self):
        """Invariant: Project IDs must be lowercase and referenced assets must exist on disk."""
        for p_json in (ROOT / "catalog" / "projects").glob("*/project.json"):
            p = json.loads(p_json.read_text(encoding="utf-8"))
            pid = p["id"]
            self.assertEqual(pid, pid.lower(), f"Project ID '{pid}' must be lowercase.")
            self.assertTrue(pid.isalnum() or "-" in pid or "_" in pid, f"Project ID '{pid}' contains invalid characters.")

            p_dir = p_json.parent
            assets_dir = p_dir / "assets"
            self.assertTrue(assets_dir.is_dir(), f"Assets folder missing for project '{pid}'")

            if p.get("icon_dark"):
                self.assertTrue((assets_dir / p["icon_dark"]).exists(), f"Icon {p['icon_dark']} missing in {pid}")
            if p.get("icon_light"):
                self.assertTrue((assets_dir / p["icon_light"]).exists(), f"Icon {p['icon_light']} missing in {pid}")

            for shot in p.get("screenshots", []):
                self.assertTrue((assets_dir / shot).exists(), f"Screenshot {shot} missing in {pid}")


if __name__ == "__main__":
    unittest.main()
