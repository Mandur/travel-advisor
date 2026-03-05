output "acr_login_server" {
  value = module.acr.login_server
}

output "foundry_project_name" {
  value = module.foundry.project_name
}

output "foundry_project_endpoint" {
  value = module.foundry.project_endpoint
}

output "postgres_server_fqdn" {
  value = module.postgres.server_fqdn
}

output "postgres_connection_string" {
  value     = module.postgres.connection_string
  sensitive = true
}

output "keyvault_uri" {
  value = module.keyvault.vault_uri
}

output "appinsights_connection_string" {
  value     = module.monitoring.application_insights_connection_string
  sensitive = true
}

output "managed_identity_client_id" {
  value = azurerm_user_assigned_identity.agents.client_id
}

# --- Container Apps Outputs ---

output "container_app_environment_id" {
  value = module.appservice.container_app_environment_id
}

output "container_app_urls" {
  value       = module.appservice.container_app_urls
  description = "URLs for the deployed agent container apps"
}

output "container_app_ids" {
  value = module.appservice.container_app_ids
}

# --- Bot Service Outputs ---

output "bot_name" {
  value       = module.bot.bot_name
  description = "Azure Bot Service resource name"
}

output "bot_messaging_endpoint" {
  value       = module.bot.messaging_endpoint
  description = "Bot Framework messaging endpoint (set as the Azure Bot endpoint)"
}

output "bot_microsoft_app_id" {
  value       = module.bot.microsoft_app_id
  description = "Bot App ID — use as 'botId' in teams-app/manifest.json"
}
