<#
.SYNOPSIS
    Deploy hosted agents to Azure Container Apps.

.DESCRIPTION
    This script updates the container images for deployed Azure Container Apps
    and triggers new revisions to pull the latest version from Azure Container Registry.
    Replaces the deprecated deploy_agents_appservice.ps1 (which targeted App Service).

.PARAMETER ResourceGroup
    Azure resource group containing the Container Apps.

.PARAMETER BaseName
    Base name used for all resources (e.g., 'hack-trial').

.PARAMETER AcrName
    Azure Container Registry name (without .azurecr.io suffix). Defaults to 'hacktrial'.

.PARAMETER Tag
    Docker image tag to deploy. Defaults to '0.0.1'.

.EXAMPLE
    .\deploy_agents_containerapp.ps1 -ResourceGroup "rg-hack-trial" -BaseName "hack-trial"

.EXAMPLE
    .\deploy_agents_containerapp.ps1 -ResourceGroup "rg-hack-trial" -BaseName "hack-trial" -Tag "0.0.2"
#>

param(
    [string]$ResourceGroup = "rg-hack-trial",

    [string]$BaseName = "hack-trial",

    [string]$AcrName = "hacktrial",

    [string]$Tag = "0.0.3"
)

$ErrorActionPreference = "Continue"

$agents = @(
    "advisor-agent",
    "travel-advisor-agent",
    "meeting-broker-agent"
)

$acrLoginServer = "$AcrName.azurecr.io"
$failures = @()

Write-Host "Deploying agents to Azure Container Apps..." -ForegroundColor Cyan
Write-Host "  Resource Group: $ResourceGroup"
Write-Host "  Base Name:      $BaseName"
Write-Host "  ACR:            $acrLoginServer"
Write-Host "  Image Tag:      $Tag"
Write-Host ""

Write-Host "Building and pushing Docker images (TAG=$Tag)..." -ForegroundColor Cyan
$env:TAG = $Tag
docker-compose build --push
if ($LASTEXITCODE -ne 0) {
    Write-Error "docker-compose build --push failed. Aborting deployment."
    exit 1
}
Write-Host "Docker images built and pushed successfully." -ForegroundColor Green
Write-Host ""

foreach ($agentName in $agents) {
    $containerAppName = "$BaseName-$agentName"
    $image = "$acrLoginServer/${agentName}:$Tag"

    Write-Host "Updating '$containerAppName' to image '$image'..." -ForegroundColor Yellow

    az containerapp update `
        --name $containerAppName `
        --resource-group $ResourceGroup `
        --image $image `
        2>&1 | Out-Null

    if ($LASTEXITCODE -ne 0) {
        Write-Warning "  ERROR: Failed to update '$containerAppName'."
        $failures += $agentName
        continue
    }

    Write-Host "  '$containerAppName' updated successfully (new revision triggered)." -ForegroundColor Green
    Write-Host ""
}

Write-Host "All agents processed." -ForegroundColor Cyan

if ($failures.Count -gt 0) {
    Write-Warning "The following agents had failures: $($failures -join ', ')"
    exit 1
}

Write-Host ""
Write-Host "Deployment completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "To view agent traffic FQDNs:"
foreach ($agentName in $agents) {
    $containerAppName = "$BaseName-$agentName"
    Write-Host "  az containerapp show --name $containerAppName --resource-group $ResourceGroup --query properties.latestRevisionFqdn -o tsv"
}
