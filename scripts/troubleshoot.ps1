#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Troubleshoot the hack-trial agent deployment locally or on Azure.

.DESCRIPTION
    Runs a suite of checks against the three agents (routing, travel-advisor,
    meeting-broker). Detects local (docker-compose) or Azure (Container Apps)
    mode automatically, or you can force one with -Mode.

.PARAMETER Mode
    "local" | "azure". Defaults to auto-detect: uses "local" when Docker
    containers are running, otherwise falls back to "azure".

.PARAMETER ResourceGroup
    Azure resource group name. Defaults to "rg-hack-trial".

.PARAMETER BaseName
    Base name used for Azure resource naming. Defaults to "hack-trial".

.EXAMPLE
    .\scripts\troubleshoot.ps1
    .\scripts\troubleshoot.ps1 -Mode azure
    .\scripts\troubleshoot.ps1 -Mode local
#>
param(
    [ValidateSet("local", "azure", "auto")]
    [string]$Mode = "auto",

    [string]$ResourceGroup = "rg-hack-trial",
    [string]$BaseName = "hack-trial"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

$script:PassCount = 0
$script:FailCount = 0
$script:WarnCount = 0

function Write-Header([string]$Title) {
    Write-Host ""
    Write-Host "━━━ $Title " -ForegroundColor Cyan -NoNewline
    Write-Host ("━" * [Math]::Max(0, 60 - $Title.Length)) -ForegroundColor Cyan
}

function Pass([string]$Msg) {
    $script:PassCount++
    Write-Host "  ✔  $Msg" -ForegroundColor Green
}

function Fail([string]$Msg, [string]$Detail = "") {
    $script:FailCount++
    Write-Host "  ✘  $Msg" -ForegroundColor Red
    if ($Detail) { Write-Host "     $Detail" -ForegroundColor DarkRed }
}

function Warn([string]$Msg, [string]$Detail = "") {
    $script:WarnCount++
    Write-Host "  ⚠  $Msg" -ForegroundColor Yellow
    if ($Detail) { Write-Host "     $Detail" -ForegroundColor DarkYellow }
}

function Info([string]$Msg) {
    Write-Host "  ℹ  $Msg" -ForegroundColor DarkGray
}

function Test-HttpHealth([string]$Label, [string]$Url) {
    try {
        $response = Invoke-WebRequest -Uri $Url -Method GET -TimeoutSec 8 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Pass "$Label  →  $Url  (HTTP $($response.StatusCode))"
            return $true
        } else {
            Fail "$Label  →  $Url  (HTTP $($response.StatusCode))"
            return $false
        }
    } catch {
        Fail "$Label  →  $Url  unreachable" "$($_.Exception.Message)"
        return $false
    }
}

# ---------------------------------------------------------------------------
# Auto-detect mode
# ---------------------------------------------------------------------------

if ($Mode -eq "auto") {
    $dockerRunning = docker ps --format "{{.Names}}" 2>$null |
        Where-Object { $_ -match "advisor-agent|travel-advisor|meeting-broker" }
    $Mode = if ($dockerRunning) { "local" } else { "azure" }
    Info "Auto-detected mode: $Mode"
}

# ---------------------------------------------------------------------------
# ── LOCAL MODE ───────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

if ($Mode -eq "local") {

    # --- .env file ---
    Write-Header "Environment (.env)"
    $envFile = Join-Path $PSScriptRoot ".." ".env"
    $envFile = [System.IO.Path]::GetFullPath($envFile)

    if (Test-Path $envFile) {
        Pass ".env file found"
        $envVars = Get-Content $envFile |
            Where-Object { $_ -match "^[^#].+=." } |
            ForEach-Object { ($_ -split "=", 2)[0].Trim() }

        foreach ($required in @("AZURE_AI_PROJECT_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_MINI_DEPLOYMENT")) {
            if ($required -in $envVars) {
                $val = (Get-Content $envFile | Where-Object { $_ -match "^$required=" }) -replace "^$required=", ""
                if ($val -and $val -notmatch "^<") {
                    Pass "$required is set"
                } else {
                    Fail "$required is empty or a placeholder" "Edit .env with a real value"
                }
            } else {
                Fail "$required missing from .env"
            }
        }
    } else {
        Fail ".env file not found" "Copy .env.example → .env and fill in values"
    }

    # --- Docker containers ---
    Write-Header "Docker Containers"

    $expectedContainers = @{
        "advisor-agent"       = 8088
        "travel-advisor-agent" = 8089
        "meeting-broker-agent" = 8090
    }

    $runningContainers = docker ps --format "{{.Names}}\t{{.Status}}" 2>$null
    if (-not $runningContainers) {
        Fail "No containers running" "Run: docker-compose up -d"
    } else {
        foreach ($name in $expectedContainers.Keys) {
            $match = $runningContainers | Where-Object { $_ -match $name }
            if ($match) {
                $status = ($match -split "\t")[1]
                if ($status -match "^Up") {
                    Pass "$name  ($status)"
                } else {
                    Fail "$name is not healthy  ($status)"
                }
            } else {
                Fail "$name container not found"
            }
        }
    }

    # --- Health endpoints ---
    Write-Header "Health Endpoints (local)"

    foreach ($name in $expectedContainers.Keys | Sort-Object) {
        $port = $expectedContainers[$name]
        $healthy = Test-HttpHealth $name "http://localhost:$port/health"

        if (-not $healthy) {
            Write-Host ""
            Write-Host "     Recent logs for ${name}:" -ForegroundColor DarkYellow
            docker logs --tail 30 ($runningContainers |
                Where-Object { $_ -match $name } |
                ForEach-Object { ($_ -split "\t")[0] }) 2>&1 |
                ForEach-Object { Write-Host "     | $_" -ForegroundColor DarkGray }
        }
    }

    # --- Azure AI Foundry reachability ---
    Write-Header "Azure AI Foundry Reachability"

    $endpoint = $env:AZURE_AI_PROJECT_ENDPOINT
    if (-not $endpoint -and (Test-Path $envFile)) {
        $endpoint = (Get-Content $envFile |
            Where-Object { $_ -match "^AZURE_AI_PROJECT_ENDPOINT=" }) -replace "^AZURE_AI_PROJECT_ENDPOINT=", ""
    }

    if ($endpoint -and $endpoint -notmatch "^<") {
        try {
            $null = Invoke-WebRequest -Uri $endpoint -Method HEAD -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
            Pass "Foundry endpoint reachable  ($endpoint)"
        } catch [System.Net.WebException] {
            # A 401/403 means the service is up, auth is separate
            if ($_.Exception.Response) {
                Pass "Foundry endpoint reachable (HTTP $([int]$_.Exception.Response.StatusCode))  ($endpoint)"
            } else {
                Fail "Foundry endpoint unreachable" "$($_.Exception.Message)"
            }
        } catch {
            Fail "Foundry endpoint unreachable" "$($_.Exception.Message)"
        }
    } else {
        Warn "AZURE_AI_PROJECT_ENDPOINT not set — skipping reachability check"
    }
}

# ---------------------------------------------------------------------------
# ── AZURE MODE ───────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

if ($Mode -eq "azure") {

    # --- az CLI ---
    Write-Header "Azure CLI"

    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        Fail "az CLI not installed" "Install from https://aka.ms/installazurecliwindows"
        exit 1
    }
    Pass "az CLI found  ($(az version --query '\"azure-cli\"' -o tsv 2>$null))"

    $account = az account show 2>$null | ConvertFrom-Json
    if (-not $account) {
        Fail "Not logged in to Azure" "Run: az login"
        exit 1
    }
    Pass "Logged in as $($account.user.name)  (subscription: $($account.name))"

    # --- Resource group ---
    Write-Header "Resource Group"

    $rg = az group show --name $ResourceGroup 2>$null | ConvertFrom-Json
    if ($rg) {
        Pass "Resource group '$ResourceGroup' exists  ($($rg.location))"
    } else {
        Fail "Resource group '$ResourceGroup' not found"
        exit 1
    }

    # --- Azure Container Registry ---
    Write-Header "Azure Container Registry"

    $acrName = "$BaseName" -replace "-", ""   # ACR names can't have hyphens
    $acr = az acr show --name $acrName --resource-group $ResourceGroup 2>$null | ConvertFrom-Json
    if ($acr) {
        Pass "ACR '$($acr.name)' found  (loginServer: $($acr.loginServer))"
        $repos = az acr repository list --name $acrName -o tsv 2>$null
        $expectedImages = @("advisor-agent", "travel-advisor-agent", "meeting-broker-agent")
        foreach ($img in $expectedImages) {
            if ($repos -match $img) {
                $tag = az acr repository show-tags --name $acrName --repository $img --orderby time_desc 2>$null |
                    ConvertFrom-Json | Select-Object -First 1
                Pass "Image $img  (latest tag: $tag)"
            } else {
                Fail "Image $img not found in ACR" "Run: .\scripts\build_and_push.ps1"
            }
        }
    } else {
        Warn "ACR '$acrName' not found — image checks skipped"
    }

    # --- Azure AI Foundry ---
    Write-Header "Azure AI Foundry"

    $foundryName = "$BaseName-ai-foundry"
    $foundry = az cognitiveservices account show --name $foundryName --resource-group $ResourceGroup 2>$null | ConvertFrom-Json
    if ($foundry) {
        Pass "AI Foundry '$foundryName' found  (endpoint: $($foundry.properties.endpoint))"

        # Check GPT model deployments
        $deployments = az cognitiveservices account deployment list `
            --name $foundryName --resource-group $ResourceGroup 2>$null | ConvertFrom-Json
        foreach ($model in @("gpt-5.2-chat", "gpt-5-mini")) {
            $dep = $deployments | Where-Object { $_.name -eq $model }
            if ($dep) {
                Pass "Model deployment '$model'  (state: $($dep.properties.provisioningState))"
            } else {
                Fail "Model deployment '$model' not found"
            }
        }
    } else {
        Warn "AI Foundry resource '$foundryName' not found — skipping model checks"
    }

    # --- Managed Identity / RBAC ---
    Write-Header "Managed Identity"

    $identity = az identity show `
        --name "$BaseName-agent-identity" --resource-group $ResourceGroup 2>$null | ConvertFrom-Json
    if ($identity) {
        Pass "Managed identity '$($identity.name)' found  (clientId: $($identity.clientId))"
    } else {
        Warn "Managed identity '$BaseName-agent-identity' not found"
    }

    # --- Container Apps ---
    Write-Header "Container Apps"

    $apps = az containerapp list --resource-group $ResourceGroup 2>$null | ConvertFrom-Json
    if (-not $apps) {
        Fail "No Container Apps found in resource group '$ResourceGroup'"
    } else {
        $expectedApps = @("advisor-agent", "travel-advisor-agent", "meeting-broker-agent")
        foreach ($appName in $expectedApps) {
            $fullName = "$BaseName-$appName"
            $app = $apps | Where-Object { $_.name -eq $fullName }
            if ($app) {
                $runState  = $app.properties.runningStatus
                $revState  = $app.properties.latestRevisionName
                if ($runState -eq "Running") {
                    Pass "$fullName  (running, revision: $revState)"
                } else {
                    Fail "$fullName  (state: $runState)"
                }
            } else {
                Fail "Container App '$fullName' not found"
            }
        }
    }

    # --- Health Endpoints (Azure) ---
    Write-Header "Health Endpoints (Azure)"

    foreach ($appName in @("advisor-agent", "travel-advisor-agent", "meeting-broker-agent")) {
        $fullName = "$BaseName-$appName"
        $app = $apps | Where-Object { $_.name -eq $fullName }
        if (-not $app) { continue }

        $fqdn = $app.properties.latestRevisionFqdn
        if (-not $fqdn) { $fqdn = $app.properties.configuration.ingress.fqdn }

        if ($fqdn) {
            $healthy = Test-HttpHealth $fullName "https://$fqdn/health"

            if (-not $healthy) {
                Write-Host ""
                Write-Host "     Recent logs for ${fullName}:" -ForegroundColor DarkYellow
                az containerapp logs show `
                    --name $fullName --resource-group $ResourceGroup `
                    --tail 30 --follow $false 2>$null |
                    ForEach-Object { Write-Host "     | $_" -ForegroundColor DarkGray }
            }
        } else {
            Warn "$fullName  — could not determine FQDN (ingress may be disabled)"
        }
    }

    # --- Key Vault ---
    Write-Header "Key Vault"

    $kvName = "$BaseName-kv"
    $kv = az keyvault show --name $kvName --resource-group $ResourceGroup 2>$null | ConvertFrom-Json
    if ($kv) {
        Pass "Key Vault '$kvName' found  ($($kv.properties.vaultUri))"
    } else {
        Warn "Key Vault '$kvName' not found"
    }

    # --- Application Insights ---
    Write-Header "Application Insights"

    $ai = az monitor app-insights component show `
        --app "$BaseName-appinsights" --resource-group $ResourceGroup 2>$null | ConvertFrom-Json
    if ($ai) {
        Pass "Application Insights '$($ai.name)' found"
    } else {
        Warn "Application Insights '$BaseName-appinsights' not found — telemetry may be unavailable"
    }
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Header "Summary"
Write-Host "  " -NoNewline
Write-Host " $script:PassCount passed " -ForegroundColor Black -BackgroundColor Green -NoNewline
Write-Host "  " -NoNewline
if ($script:WarnCount -gt 0) {
    Write-Host " $script:WarnCount warnings " -ForegroundColor Black -BackgroundColor Yellow -NoNewline
    Write-Host "  " -NoNewline
}
if ($script:FailCount -gt 0) {
    Write-Host " $script:FailCount failed " -ForegroundColor White -BackgroundColor Red
} else {
    Write-Host " 0 failed " -ForegroundColor Black -BackgroundColor Green
}
Write-Host ""

exit $(if ($script:FailCount -gt 0) { 1 } else { 0 })
