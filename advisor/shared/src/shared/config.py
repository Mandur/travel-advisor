"""Environment-based configuration for Foundry agents."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentConfig(BaseSettings):
    """Configuration loaded automatically from environment variables and .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    azure_ai_project_endpoint: str = ""
    azure_openai_endpoint: Annotated[str, Field(validation_alias="AZURE_OPENAI_ENDPOINT")] = ""
    gpt5_2_chat_deployment: Annotated[str, Field(validation_alias="AZURE_OPENAI_DEPLOYMENT")] = "gpt-5.2-chat"
    gpt5_mini_deployment: Annotated[str, Field(validation_alias="AZURE_OPENAI_MINI_DEPLOYMENT")] = "gpt-5-mini"
    application_insights_connection_string: Annotated[str, Field(validation_alias="APPLICATIONINSIGHTS_CONNECTION_STRING")] = ""
    # Microsoft 365 Agents SDK / Azure Bot Service auth.
    # For UserAssignedMSI bots set MICROSOFT_APP_ID to the managed identity
    # client_id and MICROSOFT_APP_TENANT_ID to the Azure tenant ID.
    # Leave blank for local dev without Teams channel validation.
    microsoft_app_id: str = ""
    microsoft_app_tenant_id: str = ""
    # RFP API
    bearer_token: Annotated[str, Field(validation_alias="BEARER_TOKEN")] = ""
    rfp_api_base_url: Annotated[str, Field(validation_alias="RFP_API_BASE_URL")] = "https://mockzilla-api-erfpmad.delightfulmoss-ca1544a1.eastus.azurecontainerapps.io/mock/rfp"
    rfp_api_timeout: Annotated[float, Field(validation_alias="RFP_API_TIMEOUT")] = 60.0
    # LangGraph / Azure OpenAI inference
    azure_openai_api_version: str = "2025-03-01-preview"
    postgres_connection_string: Annotated[str, Field(validation_alias="POSTGRES_CONNECTION_STRING")] = ""


@lru_cache(maxsize=1)
def get_config() -> AgentConfig:
    """Get cached configuration singleton."""
    return AgentConfig()
