---
name: onboard-project
description: Step-by-step checklist to add a new Android app or library (public or private) to the free central hub so it gets signed APK releases, a download page, privacy policy page and optional device-owner QR. Use when the user says add/onboard/publish/migrate a project or repo, retire a dummy release repo, or asks "how do I release this app/library".
---

# Onboard a project (app or library)

Collect: project name, slug (`app-id`, lowercase, permanent), type, source repo visibility, package name,
Device Owner? (admin receiver class), Play Store URL, one-paragraph description.

## A. Source repo (private or public Android app)
1. Add `.github/workflows/release.yml` from `app-repo-template/` of the kit; set `app-id`, `display-name`, `module`, `device-owner`.
2. Ensure Gradle requirements (see that repo's `android-release-pipeline` skill): executable `gradlew`, release build does not need a keystore.
3. Set 5 secrets: `gh secret set KEYSTORE_B64 --repo OWNER/REPO < keystore.b64`, then `KEYSTORE_PASSWORD`, `KEY_ALIAS`, `KEY_PASSWORD`, `HUB_TOKEN`.
4. Copy `AGENTS.md`, `CLAUDE.md` and the two skills from the template into the repo.

## B. Hub repo
5. Create `catalog/projects/<id>/project.json` (copy `childsafe`), add `privacy.md` and `assets/` screenshots.
6. Commit to `main`; confirm the Pages deploy succeeds (Actions tab).

## C. First release
7. In the source repo: set versionName/versionCode, `git tag v1.0.0 && git push origin v1.0.0`.
8. Verify in hub Releases: `<id>-v1.0.0` and `<id>-latest` exist with `.apk`, `SHA256SUMS`, `manifest.json`.
9. Open `/apps/<id>/`; check download, checksum, QR (Device Owner). Test enrollment on a factory-reset device.

## D. Library variant
Skip A and C; add `jitpack.yml` and the publishing block from `library-publishing-jitpack`, tag the library, set `library.*` in project.json.

## E. Retire an old dummy release repo
Update README to point to the new page, put old APKs' replacement in the hub, keep the old releases available (archive the repo,
do not delete) so already-printed QR codes still work. Check the app does not hardcode the old repo for self-update URLs.
