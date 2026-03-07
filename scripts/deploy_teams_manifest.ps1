#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build the Teams app manifest.zip for the Advisor agent and (optionally) publish
    it to the organisation app catalog via Microsoft Graph.

.DESCRIPTION
    1. Reads the real Bot App ID from Terraform outputs (bot_microsoft_app_id).
    2. Patches teams-app/manifest.json with the live value.
    3. Zips the patched manifest together with the icon files.
    4. Optionally uploads the zip to the Teams org catalog so the bot is
       available in Microsoft Teams and as a Microsoft 365 Copilot custom engine
       agent (requires AppCatalog.ReadWrite.All or AppCatalog.Submit permission).

.PARAMETER TerraformDir
    Path to the Terraform directory that contains the workspace state.
    Defaults to <repo-root>/infra.

.PARAMETER Publish
    When set, uploads manifest.zip to the org catalog via Microsoft Graph.
    Requires an active 'az login' session with the appropriate permissions.

.PARAMETER SkipTerraform
    Skip reading Terraform outputs and use the values already baked into
    manifest.json as-is. Useful for a quick re-zip / re-publish without
    needing the infra state.

.EXAMPLE
    # Build zip only (reads bot ID from Terraform)
    .\scripts\deploy_teams_manifest.ps1

.EXAMPLE
    # Build zip and publish to org catalog
    .\scripts\deploy_teams_manifest.ps1 -Publish

.EXAMPLE
    # Re-zip existing manifest and publish without touching Terraform
    .\scripts\deploy_teams_manifest.ps1 -SkipTerraform -Publish
#>

param(
    [string]$TerraformDir = (Join-Path $PSScriptRoot ".." "infra"),

    [switch]$Publish,

    [switch]$SkipTerraform
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot    = Join-Path $PSScriptRoot ".."
$TeamsAppDir = Join-Path $RepoRoot "advisor" "agents" "advisor_agent" "teams-app"
$StagingDir  = Join-Path $PSScriptRoot ".." ".tmp" "teams-app-staging"
$ZipPath     = Join-Path $PSScriptRoot ".." "manifest.zip"

# ---------------------------------------------------------------------------
# 1. Resolve Terraform outputs
# ---------------------------------------------------------------------------
$BotAppId = $null

if ($SkipTerraform) {
    Write-Host "Skipping Terraform — using manifest.json values as-is." -ForegroundColor Yellow
} else {
    $TerraformDir = Resolve-Path $TerraformDir
    Write-Host "Reading Terraform outputs from: $TerraformDir" -ForegroundColor Cyan

    Push-Location $TerraformDir
    try {
        $BotAppId = terraform output -raw bot_microsoft_app_id 2>$null
    } finally {
        Pop-Location
    }

    if (-not $BotAppId) {
        Write-Warning "Terraform output 'bot_microsoft_app_id' is empty or unavailable."
        Write-Warning "The botId in manifest.json will NOT be updated."
        $BotAppId = $null
    } else {
        Write-Host "  BOT_APP_ID : $BotAppId" -ForegroundColor Gray
    }
}

# ---------------------------------------------------------------------------
# 2. Stage a working copy of the teams-app folder
# ---------------------------------------------------------------------------
Write-Host "`nStaging teams-app files..." -ForegroundColor Cyan

if (Test-Path $StagingDir) { Remove-Item $StagingDir -Recurse -Force }
New-Item -ItemType Directory -Path $StagingDir -Force | Out-Null

Copy-Item -Path "$TeamsAppDir\*" -Destination $StagingDir -Recurse

# ---------------------------------------------------------------------------
# 3. Patch manifest.json
# ---------------------------------------------------------------------------
$ManifestPath = Join-Path $StagingDir "manifest.json"

if (-not (Test-Path $ManifestPath)) {
    throw "manifest.json not found at: $ManifestPath"
}

$content = Get-Content $ManifestPath -Raw

if ($BotAppId) {
    Write-Host "Patching manifest.json with live Bot App ID..." -ForegroundColor Cyan

    # Replace every occurrence of the placeholder/existing botId inside the JSON.
    # The manifest uses the same GUID for both bots[].botId and
    # copilotAgents.customEngineAgents[].id — update both.
    $manifest  = $content | ConvertFrom-Json
    $oldBotId  = $manifest.bots[0].botId

    if ($oldBotId -ne $BotAppId) {
        Write-Host "  Replacing botId: $oldBotId  ->  $BotAppId"
        $content = $content -replace [regex]::Escape($oldBotId), $BotAppId
        Set-Content -Path $ManifestPath -Value $content -NoNewline
        Write-Host "  Patched." -ForegroundColor Green
    } else {
        Write-Host "  botId already matches — no change needed." -ForegroundColor Green
    }
} else {
    Write-Host "  No Bot App ID to patch; manifest.json left as-is." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 4. Create manifest.zip
# ---------------------------------------------------------------------------
Write-Host "`nCreating manifest.zip..." -ForegroundColor Cyan

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

Compress-Archive -Path "$StagingDir\*" -DestinationPath $ZipPath
Write-Host "  Created: $ZipPath" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 5. Publish to the org app catalog (optional)
# ---------------------------------------------------------------------------
if ($Publish) {
    Write-Host "`nPublishing to the Microsoft Teams org app catalog..." -ForegroundColor Cyan

    Write-Host "  Acquiring Graph access token via 'az account get-access-token'..."
    $tokenJson = az account get-access-token --resource https://graph.microsoft.com | ConvertFrom-Json
    if (-not $tokenJson.accessToken) {
        throw "Failed to obtain a Graph access token. Run 'az login' first."
    }
    $token = $tokenJson.accessToken

    $authHeaders = @{
        Authorization  = "Bearer $token"
        "Content-Type" = "application/zip"
    }

    $zipBytes = [System.IO.File]::ReadAllBytes($ZipPath)

    # Determine the Teams app's external ID from the (patched) manifest.
    $manifestObj = Get-Content $ManifestPath | ConvertFrom-Json
    $externalId  = $manifestObj.id   # stable Teams app GUID
    $searchUri   = "https://graph.microsoft.com/v1.0/appCatalogs/teamsApps?`$filter=externalId eq '$externalId'"
    $existing    = Invoke-RestMethod -Uri $searchUri -Headers @{ Authorization = "Bearer $token" }

    if ($existing.value.Count -gt 0) {
        $teamsAppId = $existing.value[0].id
        Write-Host "  App already exists in catalog (teamsAppId: $teamsAppId). Updating..."
        $updateUri = "https://graph.microsoft.com/v1.0/appCatalogs/teamsApps/$teamsAppId/appDefinitions"
        Invoke-RestMethod -Uri $updateUri -Method PUT -Headers $authHeaders -Body $zipBytes | Out-Null
        Write-Host "  Updated successfully." -ForegroundColor Green
    } else {
        Write-Host "  Uploading new app to org catalog..."
        $uploadUri = "https://graph.microsoft.com/v1.0/appCatalogs/teamsApps"
        $response  = Invoke-RestMethod -Uri $uploadUri -Method POST -Headers $authHeaders -Body $zipBytes
        Write-Host "  Published successfully (teamsAppId: $($response.id))." -ForegroundColor Green
    }

    Write-Host @"

The Advisor agent app is now available in:
  - Microsoft Teams    : Apps -> Built for your org
  - Microsoft 365 Copilot : as a custom engine agent

Note: If your account has AppCatalog.Submit (not AppCatalog.ReadWrite.All) the
      app will need admin approval in the Teams Admin Center before it appears.
"@ -ForegroundColor Green

} else {
    Write-Host @"

Zip ready. To publish manually:
  1. Go to https://admin.microsoft.com
  2. Navigate to Settings -> Integrated apps -> Upload custom app
  3. Upload: $ZipPath

Or re-run with -Publish to automate this step:
  .\scripts\deploy_teams_manifest.ps1 -Publish
"@ -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# 6. Clean up staging dir
# ---------------------------------------------------------------------------
Remove-Item $StagingDir -Recurse -Force
