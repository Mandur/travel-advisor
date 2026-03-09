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
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
  storage_use_azuread = true
}

provider "azapi" {}

# Current Azure AD tenant — used when registering the bot with UserAssignedMSI
data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

module "acr" {
  source = "./modules/acr"

  name                = replace(var.base_name, "-", "")
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

module "foundry" {
  source = "./modules/foundry"

  base_name           = var.base_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  key_vault_id        = module.keyvault.vault_id
  tags                = var.tags
}

module "monitoring" {
  source = "./modules/monitoring"

  base_name           = var.base_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

module "postgres" {
  source = "./modules/postgres"

  base_name           = var.base_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

module "keyvault" {
  source = "./modules/keyvault"

  base_name           = var.base_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

# --- Managed Identity ---

resource "azurerm_user_assigned_identity" "agents" {
  name                = "${var.base_name}-identity"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

# --- RBAC Role Assignments ---

resource "azurerm_role_assignment" "acr_pull" {
  scope                = module.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.agents.principal_id
}

resource "azurerm_role_assignment" "openai_user" {
  scope                = module.foundry.ai_services_id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.agents.principal_id
}

# Required for the agent framework to call the AI Foundry Agents API
# (Microsoft.CognitiveServices/accounts/AIServices/agents/write)
resource "azurerm_role_assignment" "azure_ai_user" {
  scope                = module.foundry.ai_services_id
  role_definition_name = "Azure AI User"
  principal_id         = azurerm_user_assigned_identity.agents.principal_id
}

resource "azurerm_role_assignment" "kv_secrets" {
  scope                = module.keyvault.vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.agents.principal_id
}

# No additional RBAC needed for PostgreSQL — the connection string carries
# the admin credentials; access is controlled via firewall rules.

# --- Container Apps for Agents ---

module "appservice" {
  source = "./modules/appservice"

  base_name                      = var.base_name
  location                       = azurerm_resource_group.main.location
  resource_group_name            = azurerm_resource_group.main.name
  acr_login_server               = module.acr.login_server
  managed_identity_id            = azurerm_user_assigned_identity.agents.id
  managed_identity_client_id     = azurerm_user_assigned_identity.agents.client_id
  project_endpoint               = module.foundry.project_endpoint
  postgres_connection_string     = module.postgres.connection_string
  keyvault_uri                   = module.keyvault.vault_uri
  appinsights_connection_string  = module.monitoring.application_insights_connection_string
  bot_app_id                     = azurerm_user_assigned_identity.agents.client_id
  bot_app_tenant_id              = data.azurerm_client_config.current.tenant_id
  tags                           = var.tags
}

# --- Agents (Foundry Hosted Agent metadata) ---

module "agents" {
  source = "./modules/agents"

  foundry_project_name = module.foundry.project_name
  acr_login_server     = module.acr.login_server
  location             = azurerm_resource_group.main.location
  tags                 = var.tags
}

# --- Azure Bot Service + Teams Channel ---

module "bot" {
  source = "./modules/bot"

  base_name                  = var.base_name
  resource_group_name        = azurerm_resource_group.main.name
  advisor_agent_fqdn         = module.appservice.container_app_urls["advisor-agent"]
  managed_identity_id        = azurerm_user_assigned_identity.agents.id
  managed_identity_client_id = azurerm_user_assigned_identity.agents.client_id
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  tags                       = var.tags
}
