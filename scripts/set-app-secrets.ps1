# Sets the 5 release secrets on one app repo (Windows PowerShell).
# Usage: .\set-app-secrets.ps1 -Repo OWNER/REPO -Keystore C:\path\release.jks
param([Parameter(Mandatory)][string]$Repo, [Parameter(Mandatory)][string]$Keystore)
function Plain($s) { [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)) }
$ksp   = Plain (Read-Host "Keystore password" -AsSecureString)
$alias = Read-Host "Key alias"
$kp    = Plain (Read-Host "Key password (Enter = same as keystore)" -AsSecureString); if (-not $kp) { $kp = $ksp }
$token = Plain (Read-Host "Hub token (fine-grained PAT)" -AsSecureString)
$b64   = [Convert]::ToBase64String([IO.File]::ReadAllBytes($Keystore))
gh secret set KEYSTORE_B64      --repo $Repo --body $b64
gh secret set KEYSTORE_PASSWORD --repo $Repo --body $ksp
gh secret set KEY_ALIAS         --repo $Repo --body $alias
gh secret set KEY_PASSWORD      --repo $Repo --body $kp
gh secret set HUB_TOKEN         --repo $Repo --body $token
gh secret list --repo $Repo
