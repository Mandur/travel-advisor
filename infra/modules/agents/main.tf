variable "foundry_project_name" {
  description = "Foundry project name"
  type        = string
}

variable "acr_login_server" {
  description = "ACR login server"
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

# This module is a reference manifest for agent image metadata only.
# It provisions NO Azure resources.
#
# Actual agent runtime: Azure Container Apps defined in modules/appservice.
# Each agent is deployed as a Container App using the images listed below.
#
# Future migration path (Option C — Foundry Managed Agent Service):
#   If agents are migrated from self-hosted Container Apps to Foundry Agent Service,
#   this module can be extended with azapi_resource blocks for:
#     Microsoft.CognitiveServices/accounts/projects/agents@2025-06-01
#   Refer to the research document for the connected agents pattern.

locals {
  agent_definitions = [
    {
      name        = "advisor-agent"
      image       = "${var.acr_login_server}/advisor-agent:latest"
      port        = 8088
      description = "Routes user intent to the correct downstream agent"
    },
    {
      name        = "travel-advisor-agent"
      image       = "${var.acr_login_server}/travel-advisor-agent:latest"
      port        = 8088
      description = "Surfaces hotel pricing and forecasting information"
    },
    {
      name        = "meeting-broker-agent"
      image       = "${var.acr_login_server}/meeting-broker-agent:latest"
      port        = 8088
      description = "Handles meeting scheduling and amenities requests"
    },
  ]
}

output "agent_definitions" {
  value = local.agent_definitions
}
