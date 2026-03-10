---
title: Infrastructure
description: Terraform configuration for the Advisor hack-trial Azure infrastructure.
---

## Overview

Terraform (AzureRM ~4.0 + AzAPI ~2.0) provisions all Azure resources for the multi-agent system. State is stored remotely in Azure Blob Storage authenticated via Azure AD (no storage key required).

## Prerequisites

| Requirement | Version |
|---|---|
| [Terraform](https://developer.hashicorp.com/terraform/downloads) | >= 1.9 |
| [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) | >= 2.60 |
| Subscription role | **Contributor** + **User Access Administrator** (for RBAC assignments) |

You must be logged in with `az login` before running any Terraform commands.

## Remote State

State is stored in the `tfstate` blob container of the `tfstateadvisorhack` storage account (`rg-hosbi-advisor-teams-poc`). Your Azure AD identity needs the **Storage Blob Data Contributor** role on that account.

## Modules

| Module | Purpose |
|---|---|
| `acr` | Azure Container Registry |
| `foundry` | Azure AI Foundry (AI Services + project) |
| `monitoring` | Log Analytics + Application Insights |
| `redis` | Azure Managed Redis for LangGraph checkpoint storage |
| `keyvault` | Azure Key Vault |
| `appservice` | Container Apps environment + agent apps |
| `agents` | AI Foundry agent metadata |
| `bot` | Azure Bot Service + Teams channel |

A single user-assigned managed identity (`{base_name}-identity`) is shared across all agents. It is granted **AcrPull**, **Cognitive Services OpenAI User**, **Azure AI User**, and **Key Vault Secrets User** roles automatically.

The Redis module provisions Azure Managed Redis via `azapi` and enables the `RedisJSON` and `RediSearch` modules required by the LangGraph Redis checkpointer.

## Usage

```bash
cd infra

# First-time setup — initialises the remote backend
terraform init

# Preview changes
terraform plan -var-file=terraform.tfvars

# Apply
terraform apply -var-file=terraform.tfvars
```

## Key Variables

| Variable | Default | Description |
|---|---|---|
| `base_name` | — | Prefix for all resource names |
| `resource_group_name` | — | Target resource group |
| `location` | `swedencentral` | Azure region |
| `tags` | see `variables.tf` | Tags applied to all resources |

Copy `terraform.tfvars` and set `base_name` and `resource_group_name` before running.
