# Agent instructions (hub repo)

This single public repo is (1) the personal website (GitHub Pages), (2) the central APK/Releases store for every app,
and (3) the home of the reusable release workflow. It must stay free to run: GitHub Free only, no paid services.

Skills: read before editing.
- `.claude/skills/hub-site-catalog/SKILL.md`: edit the catalog, build the site, release/URL conventions.
- `.claude/skills/onboard-project/SKILL.md`: end-to-end checklist to add a new app or library (spans hub + source repo).

Hard rules
- Never commit APKs, keystores, tokens. Binaries live only in GitHub Releases.
- Never rename `app-id`s, release tags or `<id>-latest` releases once published (URLs and QR codes depend on them).
- Never put private source repo names, commits or internal details in public catalog files or manifests.
- Keep `android-release.yml` backward compatible: new inputs need defaults.
