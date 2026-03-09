terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~> 2.0"
    }
  }
}

variable "base_name" {
  description = "Base name for resources"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "key_vault_id" {
  description = "Key Vault ID (retained for interface compatibility, not used by azapi resources)"
  type        = string
  default     = null
}

# --- Resolve the resource group ID for azapi parent_id ---

data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

########## Create AI Foundry resource
##########

## Create the AI Foundry resource
##
resource "azapi_resource" "ai_foundry" {
  type                      = "Microsoft.CognitiveServices/accounts@2025-06-01"
  name                      = "${var.base_name}-ai-foundry"
  parent_id                 = data.azurerm_resource_group.main.id
  location                  = var.location
  schema_validation_enabled = false
  tags                      = var.tags

  body = {
    kind = "AIServices"
    sku = {
      name = "S0"
    }
    identity = {
      type = "SystemAssigned"
    }
    properties = {
      # Support both Entra ID and API Key authentication
      disableLocalAuth = false

      # Specifies that this is an AI Foundry resource
      allowProjectManagement = true
      enablePublicHostingEnvironment = true

      # Required by the API
      publicNetworkAccess = "Enabled"

      # Set custom subdomain name for DNS names created for this Foundry resource
      customSubDomainName = "${var.base_name}-ai-foundry"
    }
  }

  response_export_values = ["properties.endpoint"]
}

## Create a deployment for OpenAI's GPT-4o in the AI Foundry resource
##
resource "azapi_resource" "aifoundry_deployment_gpt4o" {
  type      = "Microsoft.CognitiveServices/accounts/deployments@2023-05-01"
  name      = "gpt-5.2-chat"
  parent_id = azapi_resource.ai_foundry.id

  depends_on = [azapi_resource.ai_foundry]

  body = {
    sku = {
      name     = "GlobalStandard"
      capacity = 1
    }
    properties = {
      model = {
        format  = "OpenAI"
        name    = "gpt-5.2-chat"
        version = "2026-02-10"
      }
    }
  }
}

## Create a deployment for OpenAI's GPT-4o-mini in the AI Foundry resource
##
resource "azapi_resource" "aifoundry_deployment_gpt4o_mini" {
  type      = "Microsoft.CognitiveServices/accounts/deployments@2023-05-01"
  name      = "gpt-5-mini"
  parent_id = azapi_resource.ai_foundry.id

  depends_on = [azapi_resource.aifoundry_deployment_gpt4o]

  body = {
    sku = {
      name     = "GlobalStandard"
      capacity = 1
    }
    properties = {
      model = {
        format  = "OpenAI"
        name    = "gpt-5-mini"
        version = "2025-08-07"
      }
    }
  }
}

## Create AI Foundry project
##
resource "azapi_resource" "ai_foundry_project" {
  type                      = "Microsoft.CognitiveServices/accounts/projects@2025-06-01"
  name                      = "${var.base_name}-ai-project"
  parent_id                 = azapi_resource.ai_foundry.id
  location                  = var.location
  schema_validation_enabled = false
  tags                      = var.tags

  body = {
    sku = {
      name = "S0"
    }
    identity = {
      type = "SystemAssigned"
    }
    properties = {
      displayName = "${var.base_name}-ai-project"
      description = "AI Foundry project"
    }
  }
}

output "hub_name" {
  value = azapi_resource.ai_foundry.name
}

output "hub_id" {
  value = azapi_resource.ai_foundry.id
}

output "ai_services_id" {
  value = azapi_resource.ai_foundry.id
}

output "project_name" {
  value = azapi_resource.ai_foundry_project.name
}

output "project_endpoint" {
  # Project-scoped endpoint required by AzureOpenAIResponsesClient.
  # Format: https://<account>.cognitiveservices.azure.com/projects/<project-name>
  value = "${trimsuffix(azapi_resource.ai_foundry.output.properties.endpoint, "/")}/api/projects/${azapi_resource.ai_foundry_project.name}"
}

output "openai_endpoint" {
  # Azure OpenAI endpoint derived from the AI Services resource name.
  # Format: https://<name>.openai.azure.com/
  value = "https://${azapi_resource.ai_foundry.name}.openai.azure.com/"
}
