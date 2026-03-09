variable "base_name" {
  description = "Base name for resources"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "acr_login_server" {
  description = "Azure Container Registry login server"
  type        = string
}

variable "managed_identity_id" {
  description = "Managed identity resource ID for the agents"
  type        = string
}

variable "managed_identity_client_id" {
  description = "Managed identity client ID for the agents"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "0.0.1"
}

variable "project_endpoint" {
  description = "Azure AI Foundry project endpoint"
  type        = string
  default     = ""
}

variable "postgres_connection_string" {
  description = "PostgreSQL connection string for the LangGraph checkpointer"
  type        = string
  default     = ""
  sensitive   = true
}

variable "keyvault_uri" {
  description = "Key Vault URI"
  type        = string
  default     = ""
}

variable "appinsights_connection_string" {
  description = "Application Insights connection string"
  type        = string
  default     = ""
  sensitive   = true
}

variable "bot_app_id" {
  description = "Microsoft App ID (managed identity client_id) injected into the advisor-agent for Bot Framework auth"
  type        = string
  default     = ""
}

variable "bot_app_tenant_id" {
  description = "Azure AD tenant ID injected into the advisor-agent for Bot Framework auth"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
}

# Container Apps Environment
resource "azurerm_container_app_environment" "agents" {
  name                = "${var.base_name}-env"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

locals {
  agents = [
    {
      name        = "advisor-agent"
      description = "Routes user intent to the correct downstream agent"
    },
    {
      name        = "travel-advisor-agent"
      description = "Surfaces hotel pricing and forecasting information"
    },
    {
      name        = "meeting-broker-agent"
      description = "Handles meeting scheduling and amenities requests"
    }
  ]

  env_vars = [
    {
      name  = "AZURE_CLIENT_ID"
      value = var.managed_identity_client_id
    },
    {
      name  = "AZURE_AI_PROJECT_ENDPOINT"
      value = var.project_endpoint
    },
    {
      name  = "POSTGRES_CONNECTION_STRING"
      value = var.postgres_connection_string
    },
    {
      name  = "KEYVAULT_URI"
      value = var.keyvault_uri
    },
    {
      name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
      value = var.appinsights_connection_string
    }
  ]

  # Extra env vars injected only into the advisor-agent for Bot Framework / Teams
  # auth. The CloudAdapter reads these at startup to validate incoming JWT tokens
  # from Azure Bot Service.
  bot_env_vars = {
    "advisor-agent" = [
      {
        name  = "MICROSOFT_APP_ID"
        value = var.bot_app_id
      },
      {
        name  = "MICROSOFT_APP_TYPE"
        value = "UserAssignedMSI"
      },
      {
        name  = "MICROSOFT_APP_TENANT_ID"
        value = var.bot_app_tenant_id
      },
      {
        name  = "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__auth_type"
        value = "UserManagedIdentity"
      },
      {
        name  = "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__client_id"
        value = var.bot_app_id
      },
      {
        name  = "CONNECTIONS__SERVICE_CONNECTION__SETTINGS__tenant_id"
        value = var.bot_app_tenant_id
      },
    ]
  }
}

# Container Apps for each agent
resource "azurerm_container_app" "agents" {
  for_each = { for agent in local.agents : agent.name => agent }

  name                = "${var.base_name}-${each.value.name}"
  container_app_environment_id = azurerm_container_app_environment.agents.id
  resource_group_name = var.resource_group_name
  revision_mode       = "Single"
  tags                = merge(var.tags, { agent = each.value.name })

  identity {
    type         = "UserAssigned"
    identity_ids = [var.managed_identity_id]
  }

  registry {
    server            = var.acr_login_server
    identity          = var.managed_identity_id
  }

  template {
    container {
      name   = each.value.name
      image  = "${var.acr_login_server}/${each.value.name}:${var.image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      dynamic "env" {
        for_each = concat(local.env_vars, lookup(local.bot_env_vars, each.key, []))
        content {
          name  = env.value.name
          value = env.value.value
        }
      }

      liveness_probe {
        port                    = 8088
        transport               = "HTTP"
        path                    = "/health"
        initial_delay           = 5
        interval_seconds        = 30
        failure_count_threshold = 3
      }

      readiness_probe {
        port                    = 8088
        transport               = "HTTP"
        path                    = "/health"
        initial_delay           = 3
        interval_seconds        = 10
        failure_count_threshold = 2
      }
    }

    max_replicas = 10
    min_replicas = 1
  }

  ingress {
    external_enabled = true
    target_port      = 8088
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

output "container_app_environment_id" {
  value = azurerm_container_app_environment.agents.id
}

output "container_app_urls" {
  value = {
    for name, app in azurerm_container_app.agents :
    name => app.ingress[0].fqdn
  }
}

output "container_app_ids" {
  value = {
    for name, app in azurerm_container_app.agents :
    name => app.id
  }
}
