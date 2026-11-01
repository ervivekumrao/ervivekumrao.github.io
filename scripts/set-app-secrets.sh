#!/usr/bin/env bash
# Sets the 5 release secrets on one app repo.  Usage: ./set-app-secrets.sh OWNER/REPO path/to/release.jks
# Needs: GitHub CLI (gh) logged in with `gh auth login`.
set -euo pipefail
REPO="${1:?usage: $0 OWNER/REPO path/to/release.jks}"; KS="${2:?keystore path}"
read -rsp "Keystore password: " KSP; echo
read -rp  "Key alias: " ALIAS
read -rsp "Key password (Enter = same as keystore): " KP; echo; KP="${KP:-$KSP}"
read -rsp "Hub token (fine-grained PAT): " TOKEN; echo
base64 < "$KS" | tr -d '\n' | gh secret set KEYSTORE_B64 --repo "$REPO"
printf %s "$KSP"   | gh secret set KEYSTORE_PASSWORD --repo "$REPO"
printf %s "$ALIAS" | gh secret set KEY_ALIAS --repo "$REPO"
printf %s "$KP"    | gh secret set KEY_PASSWORD --repo "$REPO"
printf %s "$TOKEN" | gh secret set HUB_TOKEN --repo "$REPO"
echo "Done. Secrets now on $REPO:"; gh secret list --repo "$REPO"
