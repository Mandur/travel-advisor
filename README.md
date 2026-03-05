# Hack Trial — Foundry Hosted Agents

Multi-agent monorepo built with [uv](https://docs.astral.sh/uv/) and [Microsoft Agent Framework](https://github.com/microsoft/agent-framework), deployable as:
- Private hosted agents on [Microsoft Foundry Agent Service](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/hosted-agents)
- Container apps on [Azure App Service](https://learn.microsoft.com/en-us/azure/app-service/)

## Agents

| Agent | Description | Port |
|-------|-------------|------|
| **Routing Agent** | Classifies user intent and routes to the correct downstream agent | 8088 |
| **Travel Advisor Agent** | Surfaces hotel pricing information and price forecasting | 8088 |
| **Meeting Broker Agent** | Handles meeting scheduling, room booking, and amenities | 8088 |

## Project Structure

```
hack-trial/
├── pyproject.toml              # Workspace root
├── shared/                     # Shared library (models, config, utils)
├── agents/
│   ├── advisor_agent/          # Intent classification agent
│   ├── travel_advisor_agent/   # Hotel pricing & forecasting agent
│   └── meeting_broker_agent/   # Meeting scheduling agent
├── infra/                      # Azure Bicep templates
├── scripts/                    # Build & deployment scripts
└── azure.yaml                  # Azure Developer CLI config
```

## Prerequisites

- [Python 3.12+](https://python.org)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) with `az login`
- [Azure Developer CLI (azd)](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/)

## Local Development

```bash
# Install all dependencies
uv sync

# Run a specific agent locally (serves on http://localhost:8088)
uv run --package routing-agent python -m advisor_agent.main
uv run --package travel-advisor-agent python -m travel_advisor_agent.main
uv run --package meeting-broker-agent python -m meeting_broker_agent.main
```

## Docker Build

```bash
# Build individual agent images
docker build -t routing-agent -f agents/advisor_agent/Dockerfile .
docker build -t travel-advisor-agent -f agents/travel_advisor_agent/Dockerfile .
docker build -t meeting-broker-agent -f agents/meeting_broker_agent/Dockerfile .

# Run locally
docker run -p 8088:8088 routing-agent
```

## Azure Deployment

### 1. Provision Infrastructure

```bash
# Using Azure Developer CLI
azd up

# Or using Bicep directly
az deployment group create \
  --resource-group <rg-name> \
  --template-file infra/main.bicep \
  --parameters infra/main.bicepparam
```

### 2. Build & Push Docker Images

```powershell
.\scripts\build_and_push.ps1 -AcrName <your-acr-name>
```

### 3. Register Agents in Foundry

```powershell
.\scripts\deploy_agents.ps1 -AcrName <your-acr-name> -FoundryProject <project-name> -ResourceGroup <rg-name>
```

## Azure App Service Deployment

### 1. Provision Infrastructure with Terraform

The infrastructure includes an App Service Plan and three Linux Web Apps (one per agent).

```bash
cd infra

# Initialize Terraform
terraform init

# Create/update terraform.tfvars with your settings
# Example:
# base_name           = "hack-trial"
# resource_group_name = "hack-trial-rg"
# location            = "swedencentral"

# Plan and apply
terraform plan -out=tfplan
terraform apply tfplan
```

### 2. Build & Push Docker Images

```powershell
.\scripts\build_and_push.ps1 -AcrName hacktrial
```

### 3. Deploy to App Service

```powershell
# Using the PowerShell deployment script
.\scripts\deploy_agents_appservice.ps1 `
  -ResourceGroup hack-trial-rg `
  -BaseName hack-trial `
  -Tag 0.0.1

# Or using Azure CLI directly to restart apps
az webapp restart --resource-group hack-trial-rg --name hack-trial-routing-agent
az webapp restart --resource-group hack-trial-rg --name hack-trial-travel-advisor-agent
az webapp restart --resource-group hack-trial-rg --name hack-trial-meeting-broker-agent
```

### Terraform Outputs

After successful deployment, Terraform outputs the following:

```bash
terraform output web_app_urls
```

Example output:
```
{
  "meeting-broker-agent" = "https://hack-trial-meeting-broker-agent.azurewebsites.net"
  "routing-agent" = "https://hack-trial-routing-agent.azurewebsites.net"
  "travel-advisor-agent" = "https://hack-trial-travel-advisor-agent.azurewebsites.net"
}
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name |
| `AZURE_OPENAI_API_VERSION` | API version (default: `2024-12-01-preview`) |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Application Insights connection string |

## Architecture

```
User → Routing Agent → Travel Advisor Agent
                     → Meeting Broker Agent
```

The **Routing Agent** classifies user intent into `travel`, `meeting`, or `general` categories and routes to the appropriate specialist agent. Each agent runs as an independent container on Foundry Agent Service, communicating via the Foundry orchestration layer.
