variable "base_name" {
  description = "Base name for all resources"
  type        = string
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "swedencentral"
}

variable "resource_group_name" {
  description = "Name of the Azure resource group"
  type        = string
}

variable "bearer_token" {
  description = "Bearer token for the RFP API"
  type        = string
  default     = ""
  sensitive   = true
}

variable "rfp_api_base_url" {
  description = "Base URL for the RFP API"
  type        = string
  default     = "https://mockzilla-api-erfpmad.delightfulmoss-ca1544a1.eastus.azurecontainerapps.io/mock/rfp"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    project     = "hack-trial"
    environment = "dev"
  }
}
