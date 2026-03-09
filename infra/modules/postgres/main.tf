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

# ---------------------------------------------------------------------------
# Admin password — generated once, stored in Terraform state
# ---------------------------------------------------------------------------

resource "random_password" "postgres_admin" {
  length           = 24
  special          = true
  override_special = "!#$%&*-_=+?"
}

# ---------------------------------------------------------------------------
# PostgreSQL Flexible Server
# ---------------------------------------------------------------------------

resource "azurerm_postgresql_flexible_server" "this" {
  name                = "${var.base_name}-psql"
  resource_group_name = var.resource_group_name
  location            = var.location

  version    = "16"
  sku_name   = "B_Standard_B1ms"
  storage_mb = 32768

  administrator_login    = "psqladmin"
  administrator_password = random_password.postgres_admin.result

  backup_retention_days        = 7
  geo_redundant_backup_enabled = false

  tags = var.tags
}

# ---------------------------------------------------------------------------
# Default database
# ---------------------------------------------------------------------------

resource "azurerm_postgresql_flexible_server_database" "langgraph" {
  name      = "langgraph"
  server_id = azurerm_postgresql_flexible_server.this.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# ---------------------------------------------------------------------------
# Firewall — allow Azure-internal services (0.0.0.0/0.0.0.0 is the Azure magic range)
# ---------------------------------------------------------------------------

resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure_services" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.this.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------

output "server_fqdn" {
  description = "Fully qualified domain name of the PostgreSQL server"
  value       = azurerm_postgresql_flexible_server.this.fqdn
}

output "connection_string" {
  description = "PostgreSQL connection string for LangGraph checkpointer (psycopg async driver)"
  value       = "postgresql+psycopg://psqladmin:${urlencode(random_password.postgres_admin.result)}@${azurerm_postgresql_flexible_server.this.fqdn}:5432/langgraph"
  sensitive   = true
}
