variable "name" {
  description = "Name of the Azure Container Registry"
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

resource "azurerm_container_registry" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
  sku                 = "Basic"
  admin_enabled       = false
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

output "login_server" {
  value = azurerm_container_registry.this.login_server
}

output "name" {
  value = azurerm_container_registry.this.name
}

output "id" {
  value = azurerm_container_registry.this.id
}
