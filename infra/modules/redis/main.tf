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

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
}

data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

resource "azapi_resource" "redis" {
  type                      = "Microsoft.Cache/redisEnterprise@2025-04-01"
  name                      = "${var.base_name}-redis"
  parent_id                 = data.azurerm_resource_group.main.id
  location                  = var.location
  schema_validation_enabled = false
  tags                      = var.tags

  body = {
    properties = {
      encryption = {}
      highAvailability = "Enabled"
      minimumTlsVersion = "1.2"
      publicNetworkAccess = "Enabled"
    }
    sku = {
      name = "Balanced_B0"
    }
  }

  response_export_values = ["properties.hostName"]
}

resource "azapi_resource" "default_database" {
  type                      = "Microsoft.Cache/redisEnterprise/databases@2025-04-01"
  name                      = "default"
  parent_id                 = azapi_resource.redis.id
  schema_validation_enabled = false

  body = {
    properties = {
      accessKeysAuthentication = "Enabled"
      clientProtocol           = "Encrypted"
      clusteringPolicy         = "NoCluster"
      evictionPolicy           = "NoEviction"
      modules = [
        {
          args = ""
          name = "RedisJSON"
        },
        {
          args = ""
          name = "RediSearch"
        }
      ]
      port = 10000
    }
  }

  response_export_values = ["properties.port"]
}

data "azapi_resource_action" "default_database_keys" {
  type        = "Microsoft.Cache/redisEnterprise/databases@2025-07-01"
  resource_id = azapi_resource.default_database.id
  action      = "listKeys"

  sensitive_response_export_values = ["primaryKey", "secondaryKey"]

  depends_on = [azapi_resource.default_database]
}

output "host_name" {
  description = "DNS host name for the Azure Managed Redis endpoint"
  value       = azapi_resource.redis.output.properties.hostName
}

output "connection_string" {
  description = "Redis URL for LangGraph checkpointer"
  value       = "rediss://:${urlencode(data.azapi_resource_action.default_database_keys.sensitive_output.primaryKey)}@${azapi_resource.redis.output.properties.hostName}:${azapi_resource.default_database.output.properties.port}/0"
  sensitive   = true
}