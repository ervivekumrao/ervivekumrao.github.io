# Free Central App Hub: Detailed Step-by-Step Guide

**Goal:** one public repo that is (1) your website, (2) the central APK download store for every app, whether its source is private or public, and (3) the home of one reusable build/sign/release workflow. Everything runs on GitHub Free at **$0**.

**How to use this guide:** do the parts in order. Every step ends with a **✔ Check** so you know it worked before moving on. Replace `ervivekumrao` with your username if different. Estimated time for the first app: 2 to 3 hours; each additional app: 15 to 20 minutes.

---

## Contents
1. [How it works](#1-how-it-works)
2. [What stays free and what to watch](#2-what-stays-free-and-what-to-watch)
3. [Prerequisites](#3-prerequisites)
4. [Decisions to make first](#4-decisions-to-make-first)
5. [Part A: Set up the hub repo](#5-part-a-set-up-the-hub-repo)
6. [Part B: Signing key](#6-part-b-signing-key)
7. [Part C: Hub token](#7-part-c-hub-token)
8. [Part D: Prepare one app repo](#8-part-d-prepare-one-app-repo)
9. [Part E: First release (smoke test, then real)](#9-part-e-first-release)
10. [Part F: Project page on the website](#10-part-f-project-page-on-the-website)
11. [Part G: Device Owner QR enrollment](#11-part-g-device-owner-qr-enrollment)
12. [Part H: Migrate your existing repos](#12-part-h-migrate-your-existing-repos)
13. [Part I: Libraries (JitPack)](#13-part-i-libraries-jitpack)
14. [Part J: AI agent skills](#14-part-j-ai-agent-skills)
15. [Operations](#15-operations)
16. [Security](#16-security)
17. [Troubleshooting](#17-troubleshooting)
18. [Reference](#18-reference)
19. [Master checklist](#19-master-checklist)

---

## 1. How it works

```
 App repos (private or public)                 HUB: ervivekumrao/ervivekumrao.github.io  (public)
 ┌──────────────────────────┐  push tag v1.2.0 ┌───────────────────────────────────────────────┐
 │ Child-Safe (private)     │ ───────────────► │ .github/workflows/android-release.yml          │
 │  .github/workflows/      │  calls reusable  │   1 build unsigned APK (runs in the APP repo)  │
 │  release.yml (20 lines)  │  workflow        │   2 zipalign + apksigner sign + verify         │
 └──────────────────────────┘                  │   3 read package/version/cert fingerprint      │
 ┌──────────────────────────┐                  │   4 gh release create ──► hub Releases         │
 │ Study-Companion ...      │ ───────────────► │   5 trigger site rebuild                       │
 └──────────────────────────┘                  │                                                │
                                               │ Releases (binaries only)                       │
 ┌──────────────────────────┐   git tag        │   childsafe-v1.2.0   fixed, never changes      │
 │ TimeSpanSelectorView     │ ──► JitPack      │   childsafe-latest   rolling, QR codes use it  │
 └──────────────────────────┘                  │                                                │
                                               │ catalog/ + tools/build_site.py ──► GitHub Pages │
                                               └───────────────────────────────────────────────┘
```

Important: the build runs inside **your app repo's** Actions (so source never leaves it), but the workflow *definition* is shared from the hub. Only the finished, signed APK goes to the public hub.

| Problem you described | Solution |
|---|---|
| Private repos cannot give public APK links for QR enrollment | APKs are published to the public hub's Releases; source stays private |
| Each project must be distinguishable, without a repo per project | Tag namespace inside one repo: `<app-id>-vX.Y.Z` and `<app-id>-latest` |
| One website, not one repo per page | One folder per project in `catalog/`; a script builds all pages |
| No repeated CI setup | One reusable workflow, each app has a ~20-line caller |
| Libraries | JitPack builds from git tags, free |
| Per-repo AI agents must be able to change this | `AGENTS.md` and `.claude/skills/*` in each repo |

**URLs you will get**

| Purpose | URL |
|---|---|
| Stable latest APK (QR codes, links) | `https://github.com/ervivekumrao/ervivekumrao.github.io/releases/download/<app-id>-latest/<app-id>.apk` |
| Pinned version (audits, rollback) | `https://github.com/ervivekumrao/ervivekumrao.github.io/releases/download/<app-id>-v1.2.0/<app-id>-1.2.0.apk` |
| App page | `https://ervivekumrao.github.io/apps/<app-id>/` |
| Privacy policy (Play Console) | `https://ervivekumrao.github.io/apps/<app-id>/privacy/` |
| Library page | `https://ervivekumrao.github.io/libs/<lib-id>/` |
| Machine-readable catalog | `https://ervivekumrao.github.io/api/catalog.json` |

## 2. What stays free and what to watch

Limits below are what GitHub published at the time of writing. **Confirm on GitHub's pricing and docs pages**, since plans change.

| Resource | Free allowance | Your usage |
|---|---|---|
| Actions minutes, public repos | Unlimited (standard runners) | Hub workflows: seconds per run |
| Actions minutes, private repos | 2,000 Linux min/month | A release build ≈ 5 to 10 min, so 200+ releases/month |
| Pages | Public repos; soft limits ~1 GB site, ~100 GB/month traffic | Site is a few hundred KB; APKs are not on Pages |
| Release assets | 2 GiB per file; no total cap | APKs are tens of MB |
| Secrets, fine-grained tokens, reusable workflows | Free | |
| JitPack | Free for public repos | |

**Make sure you can never be charged:**
1. GitHub > profile photo > **Settings > Billing and plans** (menu names shift; look for *Budgets and alerts* / *Spending limit*). Keep the Actions spending limit/budget at **$0** and do not add a payment method.
2. Check usage monthly: *Billing and plans > Usage*. If private-repo minutes run low, the builds stop (they do not bill you at $0 budget); wait for the monthly reset or make builds faster.
3. Save minutes: the workflow already caches Gradle; avoid pushing many tags; use `workflow_dispatch` only when needed.

What you give up compared with paid hosting: no custom download domain, no download analytics beyond the per-asset download counts shown on the Releases page, and GitHub is a single dependency.

## 3. Prerequisites

Install on your computer (all free):

| Tool | Why | Check |
|---|---|---|
| Git | commit and tag | `git --version` |
| GitHub CLI `gh` (https://cli.github.com) | set secrets, view releases | `gh --version`, then `gh auth login` and pick GitHub.com, HTTPS, browser login |
| JDK 17 (includes `keytool`) | keystore management | `keytool -help` |
| Android Studio (or just SDK build-tools) | local `apksigner` for verification | find `apksigner` under `<Android SDK>/build-tools/<version>/` |
| Python 3.10+ (optional) | preview the site locally | `python --version` |

Windows: use Git Bash or PowerShell; macOS/Linux: any terminal. Commands are given for each.

## 4. Decisions to make first

Fill this worksheet for each app before you start (the example is ChildSafe):

| Field | Example | Rules |
|---|---|---|
| Source repo | `ervivekumrao/Child-Safe` (private) | existing |
| `app-id` (slug) | `childsafe` | lowercase letters/digits/hyphens, **permanent**, becomes folder name, tag prefix and URL |
| Display name | ChildSafe | shown on site |
| Package name | `com.vivek.childsafe` | from your Gradle `applicationId` |
| Gradle module | `app` | the module that builds the APK |
| Device Owner? | yes | needs QR enrollment |
| Admin component | `com.vivek.childsafe/.admin.AdminReceiver` | from `AndroidManifest.xml` |
| Also on Play? | yes/no | affects signing (see Part B) |
| Source visibility on site | private | public repos can show a "Source code" button |

Pick one signing strategy now (Part B): **one shared keystore for all apps** (simplest, one backup) or **one per app** (smaller blast radius, more secrets to track). If apps are already distributed, you have no choice: keep each app's existing key.

---

## 5. Part A: Set up the hub repo

### A1. Rename `me` to `ervivekumrao.github.io`
1. Open https://github.com/ervivekumrao/me > **Settings** > General > *Repository name*, type `ervivekumrao.github.io`, **Rename**.
2. The name must be exactly `<username>.github.io` for the site to serve at the root. Your old address `.../me/` will stop working; GitHub redirects the repository URL but not the Pages URL, so update links you shared.
3. Make sure the repo is **Public**.

✔ Check: `https://github.com/ervivekumrao/ervivekumrao.github.io` opens.

### A2. Back up the old portfolio
```bash
git clone https://github.com/ervivekumrao/ervivekumrao.github.io hub && cd hub
git checkout -b old-portfolio && git push -u origin old-portfolio
git checkout main
```
This keeps your current HTML in a branch you can copy text and images from.

### A3. Add the kit files
1. Unzip the kit. Copy **everything inside `hub-repo/`** into the cloned repo (including hidden folders `.github` and `.claude`). Also copy the kit's `scripts/` folder and `docs/GUIDE.md` into it (handy, harmless).
2. Remove your old HTML from `main`: `git rm -r --ignore-unmatch *.html css js images` (adjust names), keeping `.git`, `.github`, `catalog`, `tools`, `static`, `requirements.txt`, `AGENTS.md`, `CLAUDE.md`, `.claude`, `scripts`, `docs`.
3. If your username or repo name differs, search the hub files for `ervivekumrao` and replace: `.github/workflows/android-release.yml` (the `hub-repo` default input) and later the caller template.

### A4. Edit the site identity
Open `catalog/site.json`:
```json
{
  "name": "Vivek Kumar Rao",
  "tagline": "Android apps, libraries and tools",
  "bio": "Free Android apps and open-source libraries. Every download is signed and checksummed.",
  "base_path": "",
  "footer": "© Vivek Kumar Rao. All apps are free.",
  "links": { "GitHub": "https://github.com/ervivekumrao" }
}
```
Keep `"base_path": ""` because the site is at the domain root.

### A5. Preview locally (optional but recommended)
```bash
pip install -r requirements.txt
python tools/build_site.py --out dist --fixture tools/fixtures/manifests.sample.json
python -m http.server -d dist 8000      # open http://localhost:8000
```
✔ Check: home page lists "ChildSafe" and "TimeSpanSelectorView"; ChildSafe's page shows a Download section and a QR (QR needs `segno`, installed by `requirements.txt`).

### A6. Turn on GitHub Pages via Actions
1. Repo **Settings > Pages > Build and deployment > Source: GitHub Actions**.
2. Commit and push:
```bash
git add -A && git commit -m "Hub: site generator, release workflow, catalog" && git push origin main
```
3. Open the **Actions** tab, workflow *Build and deploy site*.

✔ Check: the run is green and `https://ervivekumrao.github.io/` shows your new site. If the build step fails because there are no releases yet, that is fine: the generator handles zero releases (it shows "No release has been published yet").

---

## 6. Part B: Signing key

### B1. Case 1: the app is already distributed
You must reuse the **same key** that signed the APKs already in users' hands (and in enrolled devices' QR checksums).
1. Find the keystore (`.jks` / `.keystore`) from your Android Studio *Generate Signed Bundle/APK* history or Gradle `signingConfigs`.
2. Confirm it is the right one by comparing fingerprints:
```bash
keytool -list -v -keystore release.jks -alias <alias>      # note "SHA256:" line
apksigner verify --print-certs old-release.apk             # "certificate SHA-256 digest:"
```
The two SHA-256 values must be identical (colons aside).

### B2. Case 2: new app
```bash
keytool -genkeypair -v -keystore release.jks -alias release \
  -keyalg RSA -keysize 4096 -validity 10000
```
Answer the prompts, choose a strong password, and use the same password for the key if asked (or note both).

### B3. Play App Signing: read this if the app is on Play
With Play App Signing, Google holds the real app-signing key and re-signs what you upload. APKs you sideload or enroll via QR are signed with **your** key, so their certificate differs from the Play-installed one. Consequences:
- A device that has the Play-signed build cannot be updated in place by your self-signed APK (and vice versa); you must uninstall first.
- For QR enrollment, the checksum must match the build served at the QR download URL (your key). That is what the pipeline computes automatically.
- Decide per app: Device Owner apps usually ship via QR only; keep Play for the consumer variant, or use a different `applicationId` for the managed build.

### B4. Back it up (do this now)
Keep `release.jks` and the passwords in **two offline places** (for example an encrypted USB drive and a password manager's secure notes). Never commit it. If it is lost you can never update installed copies.

### B5. Encode it for GitHub
- macOS/Linux/Git Bash: `base64 < release.jks | tr -d '\n' > keystore.b64`
- PowerShell: `[Convert]::ToBase64String([IO.File]::ReadAllBytes("release.jks")) | Set-Content keystore.b64 -NoNewline`

Do not leave `keystore.b64` lying around after step D2; delete it.

---

## 7. Part C: Hub token

The app repos need permission to publish into the hub repo. Use a **fine-grained personal access token** restricted to the hub repo.

1. GitHub > profile photo > **Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token**.
2. Name: `hub-publisher`. Expiration: 1 year (the maximum is a year unless you choose "no expiration", which is not recommended).
3. Resource owner: your account. **Repository access: Only select repositories** > `ervivekumrao.github.io`.
4. **Repository permissions:** Contents = *Read and write*; Actions = *Read and write*; Metadata = *Read-only* (automatic).
5. Generate and copy the token immediately (shown once).

✔ Check (optional): `GH_TOKEN=<token> gh release list --repo ervivekumrao/ervivekumrao.github.io` runs without a permission error.

Put a calendar reminder 2 weeks before expiry. When it expires releases fail with HTTP 403 until you replace `HUB_TOKEN` in each app repo.

---

## 8. Part D: Prepare one app repo

Start with **ChildSafe** (`Child-Safe`). Repeat later for others.

### D1. Make Gradle CI-friendly
Open `app/build.gradle(.kts)`.

1. **Versions** must be in Gradle and increase every release:
```kotlin
android { defaultConfig {
    applicationId = "com.vivek.childsafe"
    versionCode = 12           // integer, must increase every release (Play requires this too)
    versionName = "1.2.0"      // matches the git tag v1.2.0
} }
```
Groovy: `versionCode 12` / `versionName "1.2.0"`.
2. **Release must not require your keystore.** If you have a release signing config that reads a local file, guard it so CI can build an unsigned APK:
```kotlin
val ksFile = rootProject.file("keystore.jks")
android {
    if (ksFile.exists()) {
        signingConfigs { create("release") { storeFile = ksFile /* passwords from local.properties */ } }
        buildTypes.getByName("release").signingConfig = signingConfigs.getByName("release")
    }
}
```
CI signs afterwards with `apksigner`, so the unsigned output is expected.
3. **gradlew** must be executable in git: `git update-index --chmod=+x gradlew && git commit -m "gradlew exec"`.
4. Confirm a local build works: `./gradlew :app:assembleRelease` and that an APK appears in `app/build/outputs/apk/release/`.

### D2. Add the five secrets
Each app repo needs: `KEYSTORE_B64`, `KEYSTORE_PASSWORD`, `KEY_ALIAS`, `KEY_PASSWORD`, `HUB_TOKEN`.

**Option 1: script (recommended)**
- macOS/Linux/Git Bash: `./scripts/set-app-secrets.sh ervivekumrao/Child-Safe /path/release.jks`
- PowerShell: `.\scripts\set-app-secrets.ps1 -Repo ervivekumrao/Child-Safe -Keystore C:\path\release.jks`

**Option 2: web UI.** Repo > Settings > Secrets and variables > Actions > *New repository secret*, five times (for `KEYSTORE_B64` paste the whole content of `keystore.b64`).

✔ Check: `gh secret list --repo ervivekumrao/Child-Safe` shows all five names (values are never shown). Then delete `keystore.b64`.

### D3. Add the caller workflow
Copy `app-repo-template/.github/workflows/release.yml` to the app repo and edit the 4 marked lines:
```yaml
jobs:
  release:
    uses: ervivekumrao/ervivekumrao.github.io/.github/workflows/android-release.yml@main
    with:
      app-id: childsafe          # permanent slug
      display-name: ChildSafe
      module: app
      device-owner: true         # false for normal apps
    secrets:
      KEYSTORE_B64: ${{ secrets.KEYSTORE_B64 }}
      KEYSTORE_PASSWORD: ${{ secrets.KEYSTORE_PASSWORD }}
      KEY_ALIAS: ${{ secrets.KEY_ALIAS }}
      KEY_PASSWORD: ${{ secrets.KEY_PASSWORD }}
      HUB_TOKEN: ${{ secrets.HUB_TOKEN }}
```
Notes:
- Private repo calling a workflow from the hub works only because the hub is public.
- Flavors? Use `gradle-task: assembleProdRelease` and see the troubleshooting row for the output path.
- Pin later for stability: `@main` becomes `@v1` after you tag the hub.

### D4. Add the agent files
Copy `AGENTS.md`, `CLAUDE.md` and `.claude/skills/` from `app-repo-template/` (see Part J). Commit everything on the default branch:
```bash
git add -A && git commit -m "CI: hub release workflow + agent skills" && git push
```

---

## 9. Part E: First release

### E1. Smoke test with a throwaway id (recommended)
To avoid polluting real tags, first run with a test id.
1. In `release.yml` temporarily set `app-id: zz-smoketest`.
2. Push a tag: `git tag v0.0.1-test && git push origin v0.0.1-test`. (The released version number comes from Gradle `versionName`, not from the tag, so make sure Gradle has a sensible value.)
3. Repo > **Actions** > watch *Release*. Typical steps: Build, Locate APK, Align and sign, Build manifest, Publish.
4. Check the hub's Releases: `zz-smoketest-vX` and `zz-smoketest-latest`.
5. **Clean up:** delete both releases and their tags on the hub:
```bash
gh release delete zz-smoketest-latest --repo ervivekumrao/ervivekumrao.github.io --cleanup-tag -y
gh release delete zz-smoketest-v<version> --repo ervivekumrao/ervivekumrao.github.io --cleanup-tag -y
```
6. Set `app-id: childsafe` back and delete the test tag: `git push origin :refs/tags/v0.0.1-test && git tag -d v0.0.1-test`.

### E2. Real release
1. Bump `versionCode`/`versionName` in Gradle, commit and push.
2. `git tag v1.2.0 && git push origin v1.2.0`.

✔ Check (all of these):
- Hub Releases has `childsafe-v1.2.0` with `childsafe-1.2.0.apk`, `SHA256SUMS`, `manifest.json`, and `childsafe-latest` (flagged *Pre-release*, which is intentional) with `childsafe.apk` and `manifest.json`.
- The URL downloads: `curl -IL https://github.com/ervivekumrao/ervivekumrao.github.io/releases/download/childsafe-latest/childsafe.apk` ends in `200`.
- Checksum matches: `sha256sum childsafe.apk` equals the line in `SHA256SUMS`.
- Signature is yours: `apksigner verify --print-certs childsafe.apk` shows the SHA-256 you recorded in Part B.
- Installing the APK on a phone works.

### E3. What the pipeline does (so you can reason about failures)
1. Checks out the app repo with full history, sets up Java and Gradle cache.
2. Runs `./gradlew :<module>:assembleRelease`.
3. Finds the APK in `<module>/build/outputs/apk/release/`.
4. Decodes the keystore into a temp file, `zipalign -p -f 4`, `apksigner sign`, `apksigner verify`.
5. Reads package, versionName, versionCode, minSdk from the APK (`aapt2`) and the certificate SHA-256 (`apksigner`), writes `manifest.json` and `SHA256SUMS`.
6. Creates/updates `<id>-latest` (overwrites assets) and creates `<id>-vX.Y.Z` (or re-uploads if it exists, so re-running is safe).
7. Triggers the hub's site workflow, which rebuilds pages from all `manifest.json` files.
8. Deletes the temp keystore.

Order matters: `-latest` is updated before the versioned release, so a download page never points to a version that does not exist.

---

## 10. Part F: Project page on the website

### F1. Create the catalog folder in the hub
```
catalog/projects/childsafe/
    project.json
    privacy.md
    assets/            screenshots (png/jpg/webp)
```

### F2. `project.json` field by field
```json
{
  "id": "childsafe",                 // = app-id, = folder name
  "name": "ChildSafe",
  "type": "app",                     // app | library | other
  "order": 10,                       // lower = earlier on home page
  "published": true,                 // false hides the page
  "tagline": "Parental control and device-owner child safety.",
  "description": "First paragraph.\n\nSecond paragraph.",
  "tags": ["Android", "Java", "Device Owner"],
  "visibility": "private",           // private: no source button; public: shows repo link
  "repo": "",                        // owner/name, only used when visibility is public
  "package": "com.vivek.childsafe",
  "play_store_url": "",              // optional button
  "device_owner": { "enabled": true, "admin_component": "com.vivek.childsafe/.admin.AdminReceiver" },
  "screenshots": ["home.png", "settings.png"]
}
```
(JSON does not allow comments: remove the `//` notes in the real file.)

### F3. Privacy policy
Write `privacy.md` in Markdown: what data is collected, why, where it is stored, retention, how to delete it, contact email. Use the published URL in the Play Console and inside the app.

### F4. Publish
```bash
git add catalog && git commit -m "Add ChildSafe page" && git push
```
✔ Check: `https://ervivekumrao.github.io/apps/childsafe/` shows description, screenshots, latest version, size, SHA-256, certificate fingerprint, Download buttons, version table and (Device Owner) a QR code. Private source repo names and commit hashes appear nowhere.

### F5. Customizing the design
Edit the `CSS` string and the `render_*` functions in `tools/build_site.py`. Add `static/CNAME` or `static/.well-known/assetlinks.json` if you ever need them (files in `static/` are copied to the site root).

---

## 11. Part G: Device Owner QR enrollment

### G1. App-side requirements (Android)
1. `DeviceAdminReceiver` subclass and manifest entry:
```xml
<receiver android:name=".admin.AdminReceiver"
    android:permission="android.permission.BIND_DEVICE_ADMIN" android:exported="true">
    <meta-data android:name="android.app.device_admin" android:resource="@xml/device_admin"/>
    <intent-filter><action android:name="android.app.action.DEVICE_ADMIN_ENABLED"/></intent-filter>
</receiver>
```
2. `res/xml/device_admin.xml` listing needed `<uses-policies>`.
3. For Android 12+ provisioning, also handle `android.app.action.GET_PROVISIONING_MODE` and `android.app.action.ADMIN_POLICY_COMPLIANCE` activities as described in the Android Enterprise documentation.
4. The component name in the QR is `<package>/<receiver class>`; use `.admin.AdminReceiver` relative form or the fully qualified class. Put it in the catalog's `device_owner.admin_component`.

### G2. What the generated QR contains
```json
{
 "android.app.extra.PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME": "com.vivek.childsafe/.admin.AdminReceiver",
 "android.app.extra.PROVISIONING_DEVICE_ADMIN_PACKAGE_DOWNLOAD_LOCATION": "https://github.com/ervivekumrao/ervivekumrao.github.io/releases/download/childsafe-latest/childsafe.apk",
 "android.app.extra.PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM": "<base64url SHA-256 of signing certificate>"
}
```
Why the certificate checksum: it stays the same for every future version signed with the same key, so one printed QR works forever and always fetches `-latest`.

### G3. Test on a real device (mandatory before you rely on it)
1. Use a **factory-reset** device (or an emulator image with Google APIs that supports it).
2. On the first welcome screen tap the same spot **6 times**; a QR scanner opens (older/OEM devices may differ; some need Wi-Fi first).
3. Connect to Wi-Fi when asked, scan the QR from the app page.
4. Watch the download and setup. If it fails: `adb logcat | grep -iE "provision|DevicePolicy"`.

Typical failures: wrong component name, certificate mismatch (Play vs self-signed), missing provisioning activities on Android 12+, Wi-Fi/HTTPS inspection blocking the download.

### G4. If the GitHub redirect is a problem on some devices
GitHub release downloads redirect to a CDN. Most provisioning downloaders follow redirects. If a device model does not, host the APK on another free host that serves the file directly over HTTPS (for example Cloudflare Pages free tier or GitLab Pages), and set `url_latest` there by publishing the file in an extra step. Test first; do not build this unless needed.

### G5. Security of the public QR
The QR only holds a public URL and a public certificate fingerprint, so publishing it is safe. Do not add Wi-Fi passwords or server tokens to a public QR; use a private QR for that.

---

## 12. Part H: Migrate your existing repos

From your repo list (confirm each against reality):

| Repo today | Visibility | Probable role | Action |
|---|---|---|---|
| `ChildSafe` (HTML) | public | dummy release repo for `Child-Safe` | after first hub release: update README to point to new page, **archive** |
| `Child-Safe` (Java) | private | real source | add caller workflow + secrets |
| `StudyCompanion` (HTML) | public | dummy for `Study-Companion` | same |
| `Study-Companion` (Kotlin) | private | real source | onboard |
| `Career-Crox-Calling-Assistant` (HTML) | public | dummy | archive after migration |
| `Career-Crox-CallingAssistant` (Java), `Career-Crox` | private | real sources, possible duplicates | decide which is current, merge or delete the other |
| `Mockup-Master`, `Med-Reminder`, `App-Manager`, `OfficeTimeCounter`, `Android` | private | apps | onboard only if you distribute APKs |
| `TimeSpanSelectorView`, `RuntimeCompile` | public | libraries | Part I |
| `Tomcat-Vault`, `DatabaseCreator`, `Agentic-Inventory`, `MyAdminApp` | public | projects | catalog entries (`type` `other`/`app`) |
| `Ashutosh` | private | personal | leave |
| `me` | public | portfolio | renamed to hub (Part A) |

### H1. Per-app migration routine
1. Complete Part D and E for the private source repo.
2. Create its catalog entry (Part F).
3. Verify download, checksum and (if Device Owner) QR on a device.
4. In the old dummy repo: edit README to say "Moved to https://ervivekumrao.github.io/apps/<id>/", keep its existing Releases in place.
5. Dummy repo > Settings > General > scroll to *Danger zone* > **Archive this repository**. Archive, do not delete: archived repos keep their Releases downloadable, so old QR codes and old installed apps keep working.
6. Search your app's code for the old repo URL (for example an update checker or hardcoded download link). Change it to the `-latest` URL in the next release.

### H2. Already-enrolled Device Owner devices
They are unaffected as long as the signing key is the same. To move them to the new update path, ship an app version whose update URL points to `.../<id>-latest/<id>.apk` (or to `manifest.json` for version checks: `.../<id>-latest/manifest.json` has `version_code` and `sha256`).

---

## 13. Part I: Libraries (JitPack)

For `TimeSpanSelectorView` and `RuntimeCompile`:
1. Repo must be public. Copy `library-repo-template/jitpack.yml`.
2. Add `maven-publish` configuration (full snippet in the library skill).
3. Tag: `git tag 1.0.0 && git push origin 1.0.0`.
4. Open `https://jitpack.io/#ervivekumrao/TimeSpanSelectorView`, click **Get it** next to the tag, and confirm the build log is green.
5. Consumers use:
```kotlin
repositories { maven { url = uri("https://jitpack.io") } }
dependencies { implementation("com.github.ervivekumrao:TimeSpanSelectorView:1.0.0") }
```
6. Hub catalog entry with `"type": "library"` and the `library` block (`jitpack`, `latest_version`, optional `docs_url`). Update `latest_version` on each release.

Your existing GitHub Packages publication of TimeSpanSelectorView can stay for compatibility, but GitHub Packages requires authentication for consumers even on public Maven packages, which is why JitPack is the recommended public route.

Java-only tools (`Tomcat-Vault`, `DatabaseCreator`, `RuntimeCompile`): attach the JAR to a GitHub Release of that same repo (public repos can do this freely); link to it from the catalog entry. No hub involvement needed.

---

## 14. Part J: AI agent skills

Skills are folders with a `SKILL.md` (name + description + instructions). An agent loads one when your request matches its description.

| Repo type | Copy these into the repo |
|---|---|
| Hub | `AGENTS.md`, `CLAUDE.md`, `.claude/skills/hub-site-catalog/`, `.claude/skills/onboard-project/` |
| App | `AGENTS.md`, `CLAUDE.md`, `.claude/skills/android-release-pipeline/`, `.claude/skills/device-owner-qr-enrollment/` |
| Library | `AGENTS.md`, `CLAUDE.md`, `.claude/skills/library-publishing-jitpack/` |

- Claude Code reads `CLAUDE.md` and discovers `.claude/skills` automatically.
- Other agents (Codex, Cursor, Copilot, etc.) read `AGENTS.md`, which names each skill path; tell them to read those files.
- Commit these files; do not put secrets in them.

**Example prompts**
- "Onboard `Med-Reminder` (package com.vivek.med, not device owner) to the hub." (use in hub repo; the agent follows `onboard-project`)
- "The release workflow failed at Align and sign; diagnose." (app repo)
- "Add a privacy page and three screenshots for StudyCompanion." (hub repo)
- "Switch ChildSafe's admin component to `.DeviceAdmin` and fix the QR." (both)
- "Release the library as 1.1.0 and update the site entry."

**Keeping skills accurate:** when you change the pipeline (new input, new file), update the matching `SKILL.md` in the same commit; the skills are the agents' source of truth.

---

## 15. Operations

| Task | How |
|---|---|
| Release an app | Bump Gradle version, `git tag vX.Y.Z && git push origin vX.Y.Z` |
| Re-run a failed release | Actions > re-run; uploads are idempotent (`--clobber`) |
| Change page text or screenshots | Edit `catalog/projects/<id>/`, push hub `main` |
| Hide a project | `"published": false` |
| Roll back users | Point them to `<id>-vOLD`; to restore `-latest`, re-run the old tag's workflow run |
| Renew `HUB_TOKEN` | Create new token (Part C), run `gh secret set HUB_TOKEN` per repo |
| Change the build for all apps | Edit `android-release.yml` once in the hub; keep new inputs optional with defaults |
| Pin the pipeline version | Tag the hub `v1` and change callers to `@v1` |
| Add a project | `onboard-project` skill or Part D to F |
| Backup | `git clone --mirror` the hub monthly; keep the keystore offline; keep copies of important APKs |

Cadence: monthly check *Billing > Usage*; yearly token rotation; after each GitHub Actions deprecation notice, bump action versions (`actions/checkout@v4` etc.).

## 16. Security

- **Secrets:** only in repo secrets. The workflow writes the keystore to a temp path and deletes it. Never `echo` secrets.
- **Triggers:** the release workflow runs on tag pushes and manual dispatch, not on pull requests, so fork PRs cannot read secrets. Do not add `pull_request_target` triggers that check out untrusted code.
- **Token scope:** `HUB_TOKEN` can only touch the hub repo. If leaked, revoke it in Developer settings and create a new one.
- **Integrity:** every release publishes `SHA256SUMS` and the signing-certificate fingerprint, shown on the site.
- **Privacy:** the hub is public. `manifest.json` deliberately omits the source repo name and commit. Never put internal URLs or credentials in `catalog/`.
- **Immutable versions:** never edit or reuse a `<id>-vX.Y.Z` release; fix forward with a new version.
- **Action pinning:** for extra safety replace `@v4` tags with commit SHAs (optional).

## 17. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| "workflow was not found" in the caller | Hub private, wrong path, or branch | Hub must be public; check `uses:` path and `@main` |
| `Permission denied: ./gradlew` | File mode | `git update-index --chmod=+x gradlew` |
| `No release APK found` | Flavors or other module | Set `module`/`gradle-task`; edit the hub *Locate APK* path for flavors |
| Gradle fails on signing config | Release config requires missing keystore | Guard it (D1.2) |
| `Keystore was tampered with, or password was incorrect` | Wrong password, or Base64 with newlines | Re-run secret script; use no-newline Base64 |
| `Failed to read key ... from keystore` | Wrong `KEY_ALIAS`/`KEY_PASSWORD` | `keytool -list -keystore release.jks` to see the alias |
| `aapt2: command not found` | Unusual runner image | Use `ubuntu-latest`; check `$ANDROID_HOME/build-tools` |
| 403 / `Resource not accessible by personal access token` at publish | Token expired or missing Contents/Actions write or wrong repo | Recreate token (Part C), update secret |
| Release exists but site not updated | Site workflow trigger failed | Run *Build and deploy site* manually; check Actions permission on token |
| Pages deploy blocked | Source not Actions, or deploying from tag | Settings > Pages > Source: GitHub Actions; run from `main` |
| App page missing the new version | Release is marked pre-release/draft | Versioned release must be a normal published release |
| Old APK still downloads after release | CDN cache | Wait a few minutes; use versioned URL to verify |
| Installed app refuses update | Different signing key or versionCode not higher | Use the original key; increment versionCode |
| QR scan says "can't set up device" | Component/checksum/URL wrong, or Android 12 activities missing | Part G3 and the device-owner skill |
| Out of Actions minutes (private repo) | Monthly cap | Wait for reset; reduce releases; keep Gradle cache |

## 18. Reference

### Files in the kit
```
README.md
docs/GUIDE.md                         this guide
scripts/set-app-secrets.sh|.ps1       set the five secrets on an app repo
hub-repo/                             copy into ervivekumrao.github.io
  .github/workflows/site.yml            build + deploy Pages
  .github/workflows/android-release.yml reusable build/sign/publish workflow
  tools/build_site.py                   site generator
  tools/fixtures/manifests.sample.json  offline test data
  catalog/site.json, catalog/projects/  site + project data
  static/                               copied to site root
  requirements.txt, AGENTS.md, CLAUDE.md, .claude/skills/{hub-site-catalog,onboard-project}
app-repo-template/                    copy into each Android app repo
  .github/workflows/release.yml         20-line caller
  AGENTS.md, CLAUDE.md, .claude/skills/{android-release-pipeline,device-owner-qr-enrollment}
library-repo-template/                jitpack.yml, AGENTS.md, CLAUDE.md, library skill
```

### Workflow inputs (`android-release.yml`)
| Input | Default | Meaning |
|---|---|---|
| `app-id` | required | slug for tags/files/URLs |
| `display-name` | required | human name |
| `module` | `app` | Gradle module |
| `gradle-task` | `assembleRelease` | task to build |
| `java-version` | `17` | JDK |
| `device-owner` | `false` | adds QR to the site page |
| `hub-repo` | `ervivekumrao/ervivekumrao.github.io` | where to publish |
Secrets: `KEYSTORE_B64`, `KEYSTORE_PASSWORD`, `KEY_ALIAS`, `KEY_PASSWORD`, `HUB_TOKEN`.

### `manifest.json` schema (published with every release)
`schema`, `app_id`, `name`, `package`, `version_name`, `version_code`, `min_sdk`, `sha256`, `size_bytes`, `cert_sha256_hex`, `cert_sha256_b64url`, `device_owner`, `url_versioned`, `url_latest`, `released_at`.

### Glossary
- **Hub repo:** the single public repo holding site, releases and shared workflow.
- **Reusable workflow:** a workflow file other repos call with `uses:`.
- **Device Owner:** the managed-device mode an app gets via QR/zero-touch provisioning.
- **Fine-grained PAT:** a GitHub token limited to chosen repos and permissions.
- **Rolling latest:** the `<id>-latest` release whose files are overwritten each release.
- **JitPack:** free service building public GitHub repos into Maven artifacts.

## 19. Master checklist

**Once**
- [ ] Tools installed; `gh auth login` done
- [ ] `me` renamed to `ervivekumrao.github.io`, public; old portfolio backed up
- [ ] Hub files committed; Pages source = GitHub Actions; site loads
- [ ] Billing budget $0, no payment method
- [ ] Keystore located/created, fingerprints verified, two offline backups
- [ ] Fine-grained token created (hub only, Contents + Actions write), expiry reminder set
- [ ] Agent files copied into hub

**Per app**
- [ ] Worksheet filled (app-id, package, module, device owner)
- [ ] Gradle: versions set, release build needs no keystore, `gradlew` executable
- [ ] Five secrets set; `keystore.b64` deleted
- [ ] `release.yml` caller added; agent files copied
- [ ] Smoke test passed and cleaned up
- [ ] Real tag pushed; assets, checksum, signature verified; installs on phone
- [ ] Catalog folder: project.json, privacy.md, screenshots
- [ ] Page verified; (Device Owner) QR tested on factory-reset device
- [ ] Old dummy repo README updated and archived; hardcoded update URLs fixed

**Per library**
- [ ] `jitpack.yml` + publishing block; tag pushed; JitPack build green
- [ ] Catalog entry with `library` block
