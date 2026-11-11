"""Unit and Integration Test Suite for the App Hub Portfolio Builder."""
from __future__ import annotations
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.builder.utils import esc, human_size, md_to_html, get_project_titles, get_project_category_badge
from tools.builder.github_api import fetch_manifests, http_json
from tools.builder.renderers import Site, enrollment_payload
from tools.build_site import main as build_site_main


class TestBuilderUtils(unittest.TestCase):
    """Tests for string escaping, formatting, and title resolution utilities."""

    def test_esc_handles_none_and_types(self):
        self.assertEqual(esc(None), "")
        self.assertEqual(esc("Hello World"), "Hello World")
        self.assertEqual(esc("1 < 2 & 3 > 0"), "1 &lt; 2 &amp; 3 &gt; 0")
        self.assertEqual(esc('"quoted"'), "&quot;quoted&quot;")
        self.assertEqual(esc(100), "100")

    def test_human_size(self):
        self.assertEqual(human_size(1_048_576), "1.0 MB")
        self.assertEqual(human_size(5_242_880), "5.0 MB")
        self.assertEqual(human_size(10_485_760), "10.0 MB")

    def test_md_to_html(self):
        output = md_to_html("### Header Test")
        self.assertTrue("Header Test" in output)
        output_html = md_to_html("<p>Raw HTML</p>")
        self.assertEqual(output_html, "<p>Raw HTML</p>")

    def test_get_project_titles(self):
        # Explicit subtitle provided
        p1 = {"name": "Test App", "subtitle": "Explicit Subtitle"}
        main1, sub1 = get_project_titles(p1)
        self.assertEqual(main1, "Test App")
        self.assertEqual(sub1, "Explicit Subtitle")

        # Name with em-dash
        p2 = {"name": "Child Safe — Parental Control & Device Governance"}
        main2, sub2 = get_project_titles(p2)
        self.assertEqual(main2, "Child Safe")
        self.assertEqual(sub2, "Parental Control & Device Governance")

        # Name with en-dash
        p3 = {"name": "Career Crox – Calling Assistant"}
        main3, sub3 = get_project_titles(p3)
        self.assertEqual(main3, "Career Crox")
        self.assertEqual(sub3, "Calling Assistant")

        # Plain name without subtitle
        p4 = {"name": "SpinDB"}
        main4, sub4 = get_project_titles(p4)
        self.assertEqual(main4, "SpinDB")
        self.assertEqual(sub4, "")


class TestGitHubAPI(unittest.TestCase):
    """Tests for GitHub API manifest fetching and resilience."""

    @patch("tools.builder.github_api.http_json")
    def test_fetch_manifests(self, mock_http):
        mock_releases_page1 = [
            {
                "tag_name": "v1.0.0",
                "draft": False,
                "prerelease": False,
                "assets": [
                    {"name": "manifest.json", "browser_download_url": "https://example.com/manifest.json"}
                ]
            },
            {
                "tag_name": "v1.0.0-latest",
                "draft": False,
                "prerelease": True,  # should be skipped
                "assets": [
                    {"name": "manifest.json", "browser_download_url": "https://example.com/latest.json"}
                ]
            }
        ]
        mock_manifest_data = {
            "app_id": "childsafe",
            "version_name": "1.0.0",
            "version_code": 1
        }

        # Page 1 returns releases, Page 2 returns empty list
        mock_http.side_effect = [mock_releases_page1, mock_manifest_data, []]

        manifests = fetch_manifests("owner/repo", token=None)
        self.assertEqual(len(manifests), 1)
        self.assertEqual(manifests[0]["app_id"], "childsafe")

    @patch("tools.builder.github_api.http_json")
    def test_fetch_manifests_resilience_on_bad_asset(self, mock_http):
        mock_releases = [
            {
                "tag_name": "v1.0.0",
                "draft": False,
                "prerelease": False,
                "assets": [{"name": "manifest.json", "browser_download_url": "https://example.com/bad.json"}]
            }
        ]
        # First call returns releases, second call raises Exception
        mock_http.side_effect = [mock_releases, Exception("404 Not Found"), []]

        manifests = fetch_manifests("owner/repo", token=None)
        self.assertEqual(manifests, [])  # skips bad release without crashing


class TestSiteRendering(unittest.TestCase):
    """Integration test for site output generation."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.cfg = {
            "name": "Vivek Umrao",
            "tagline": "Android apps, libraries and tools",
            "base_path": "",
            "links": {}
        }
        self.site = Site(self.temp_dir, self.cfg)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_site_write_and_page(self):
        page_html = self.site.page("Test Page", "<h1>Content</h1>", show_home_brand=True)
        self.site.write("test.html", page_html)
        target_file = self.temp_dir / "test.html"
        self.assertTrue(target_file.exists())
        text = target_file.read_text(encoding="utf-8")
        self.assertIn("Test Page", text)
        self.assertIn("<h1>Content</h1>", text)

    def test_enrollment_payload(self):
        p = {"device_owner": {"admin_component": "com.test/com.test.Admin"}}
        m = {"url_latest": "https://example.com/app.apk", "cert_sha256_b64url": "sha256b64"}
        payload = enrollment_payload(p, m)
        self.assertEqual(payload["android.app.extra.PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME"], "com.test/com.test.Admin")
        self.assertEqual(payload["android.app.extra.PROVISIONING_DEVICE_ADMIN_PACKAGE_DOWNLOAD_LOCATION"], "https://example.com/app.apk")
        self.assertEqual(payload["android.app.extra.PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM"], "sha256b64")

    def test_get_project_category_badge(self):
        self.assertEqual(get_project_category_badge({"type": "app"}), "📱 Android App")
        self.assertEqual(get_project_category_badge({"type": "library"}), "📦 Android Library")
        self.assertEqual(get_project_category_badge({"id": "agenticinventory", "category_badge": "⚡ Microservices & AI"}), "⚡ Microservices & AI")
        self.assertEqual(get_project_category_badge({"category_badge": "Custom Badge"}), "Custom Badge")

    def test_http_json_bearer_security(self):
        with self.assertRaises(ValueError):
            http_json("https://malicious-site.com/data", token="secret_token")

    def test_full_build_site_e2e(self):
        fixture_path = ROOT / "tools" / "fixtures" / "manifests.sample.json"
        out_dir = Path(self.temp_dir) / "dist"
        with patch("sys.argv", ["build_site.py", "--out", str(out_dir), "--fixture", str(fixture_path)]):
            exit_code = build_site_main()
            self.assertEqual(exit_code, 0)
            self.assertTrue((out_dir / "index.html").exists())
            self.assertTrue((out_dir / "style.css").exists())
            self.assertTrue((out_dir / "api" / "catalog.json").exists())
            index_content = (out_dir / "index.html").read_text(encoding="utf-8")
            self.assertIn("Vivek Umrao", index_content)
            self.assertIn("Child Safe", index_content)


if __name__ == "__main__":
    unittest.main()

