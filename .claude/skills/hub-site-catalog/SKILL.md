---
name: hub-site-catalog
description: Edit the personal website and project catalog in this hub repo, change pages/styling, add privacy policies or screenshots, fix the site build, or explain download URLs and release tags. Use whenever the user mentions the portfolio, website, GitHub Pages, project page, privacy policy page, screenshots, catalog, site build failing, manifest.json, or download links for any app or library.
---

# Hub site and catalog

## Layout
```
catalog/site.json                      site name, bio, links, base_path ("" for root domain)
catalog/projects/<id>/project.json     one folder per app or library (public metadata only)
catalog/projects/<id>/privacy.md       optional; published at /apps/<id>/privacy/ (use as Play Console URL)
catalog/projects/<id>/assets/*         screenshots, icons (listed in project.json "screenshots")
static/                                copied to site root (CNAME, robots.txt, .well-known/assetlinks.json)
tools/build_site.py                    generator (stdlib + markdown + segno)
.github/workflows/site.yml             builds and deploys Pages
.github/workflows/android-release.yml  reusable release workflow used by all app repos
```

## project.json fields
`id` (slug = folder name = app-id), `name`, `type` (`app`|`library`), `order`, `published`, `tagline`, `description`
(paragraphs separated by blank line), `tags[]`, `visibility` (`public`|`private`: source link shown only if public),
`repo` (public only), `package`, `play_store_url`, `device_owner {enabled, admin_component}`, `screenshots[]`,
`library {jitpack, latest_version, docs_url}`.

## Release data (do not edit by hand)
Per app the pipeline publishes in this repo's Releases:
`<id>-vX.Y.Z` (immutable; `<id>-X.Y.Z.apk`, `SHA256SUMS`, `manifest.json`) and `<id>-latest` (rolling, prerelease flag;
`<id>.apk`). The site reads the `manifest.json` of non-prerelease releases. Stable URL:
`https://github.com/<owner>/<this-repo>/releases/download/<id>-latest/<id>.apk`.

## Local preview
`pip install -r requirements.txt && python tools/build_site.py --out dist --fixture tools/fixtures/manifests.sample.json`
then `python -m http.server -d dist`. Without `--fixture`, set `HUB_REPO=<owner>/<repo>` (and `GITHUB_TOKEN` to avoid rate limits).

## Rules
- Public data only. Never add private repo names, commit hashes, secrets or internal URLs to the catalog.
- Changing page design: edit `CSS` and render functions in `tools/build_site.py`; keep it dependency-light.
- A project must have a catalog folder before its first release appears on the site, but releases work without one.
- Pages source must be "GitHub Actions" (Settings > Pages). If deploy fails with environment protection, deploy from `main` only.
