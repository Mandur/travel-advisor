# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------

variable "base_name" {
  description = "Base name prefix for all bot resources"
  type        = string
}

variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "advisor_agent_fqdn" {
  description = "FQDN of the advisor-agent Container App (without scheme)"
  type        = string
}

variable "managed_identity_id" {
  description = "Resource ID of the user-assigned managed identity"
  type        = string
}

variable "managed_identity_client_id" {
  description = "Client ID of the user-assigned managed identity (used as the Bot App ID)"
  type        = string
}

variable "tenant_id" {
  description = "Azure AD tenant ID"
  type        = string
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
}

# ---------------------------------------------------------------------------
# Azure Bot Service
# ---------------------------------------------------------------------------

resource "azurerm_bot_service_azure_bot" "main" {
  name                = "${var.base_name}-bot"
  resource_group_name = var.resource_group_name

  # Azure Bot Service is always deployed to the "global" location regardless
  # of where the backing Container App runs.
  location = "global"

  # The Bot App ID is the client_id of the user-assigned managed identity.
  # No client secret is required when microsoft_app_type = "UserAssignedMSI".
  microsoft_app_id        = var.managed_identity_client_id
  microsoft_app_type      = "UserAssignedMSI"
  microsoft_app_msi_id    = var.managed_identity_id
  microsoft_app_tenant_id = var.tenant_id

  sku = "S1"

  # The messaging endpoint is the advisor-agent Container App's /api/messages
  # route, served over HTTPS via the Container Apps ingress TLS termination.
  endpoint = "https://${var.advisor_agent_fqdn}/api/messages"

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Teams Channel
# ---------------------------------------------------------------------------

resource "azurerm_bot_channel_ms_teams" "teams" {
  bot_name            = azurerm_bot_service_azure_bot.main.name
  location            = azurerm_bot_service_azure_bot.main.location
  resource_group_name = var.resource_group_name
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "bot_name" {
  description = "Name of the Azure Bot Service resource"
  value       = azurerm_bot_service_azure_bot.main.name
}

output "microsoft_app_id" {
  description = "Microsoft App ID (= managed identity client_id) for the bot"
  value       = var.managed_identity_client_id
}

output "microsoft_app_tenant_id" {
  description = "Azure AD tenant ID for the bot"
  value       = var.tenant_id
}

output "messaging_endpoint" {
  description = "Bot Framework messaging endpoint URL"
  value       = azurerm_bot_service_azure_bot.main.endpoint
}
