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
    azure_openai_api_key: Annotated[str, Field(validation_alias="AZURE_OPENAI_API_KEY")] = ""
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
    azure_openai_api_version: Annotated[str, Field(validation_alias="AZURE_OPENAI_API_VERSION")] = "2025-04-01-preview"
    redis_url: Annotated[str, Field(validation_alias="REDIS_URL")] = ""
    # Sub-agent dispatch: empty = in-process (import), URL = HTTP call to /chat
    rfp_agent_url: Annotated[str, Field(validation_alias="RFP_AGENT_URL")] = ""
    property_planning_agent_url: Annotated[str, Field(validation_alias="PROPERTY_PLANNING_AGENT_URL")] = ""
    # Hotelligence360 GraphQL advisor endpoint
    hotelligence_graphql_url: Annotated[str, Field(validation_alias="HOTELLIGENCE_GRAPHQL_URL")] = "https://hotelligence360-stage.travelclick.com/chatbot/graphql"
    hotelligence_bearer_token: Annotated[str, Field(validation_alias="HOTELLIGENCE_BEARER_TOKEN")] = ""
    hotelligence_timeout: Annotated[float, Field(validation_alias="HOTELLIGENCE_TIMEOUT")] = 120.0
    # Browser-based token fetcher credentials (token_fatcher).
    # When all three are set, advisor-agent fetches a fresh token at startup
    # and auto-refreshes on 401/403 from the Hotelligence API.
    # Falls back to HOTELLIGENCE_BEARER_TOKEN when not configured.
    hotelligence_web_ui_url: Annotated[str, Field(validation_alias="WEB_UI_URL")] = ""
    hotelligence_login_email: Annotated[str, Field(validation_alias="UI_LOGIN_EMAIL")] = ""
    hotelligence_login_password: Annotated[str, Field(validation_alias="UI_LOGIN_PASSWORD")] = ""
    # Path to the Chrome/Chromium binary used by the token fetcher.
    # In Docker, set to /usr/bin/chromium (installed via apt).
    # Defaults to the bundled binary in the token_fatcher package if present,
    # or pyppeteer's own downloaded Chromium if empty.
    chrome_executable_path: Annotated[str, Field(validation_alias="CHROME_EXECUTABLE_PATH")] = ""
    # SSL / TLS
    # Set SSL_VERIFY=false to disable certificate verification (e.g. corporate proxies).
    # Set SSL_CA_BUNDLE=/path/to/ca-bundle.crt to trust a custom CA (preferred over disabling).
    ssl_verify: Annotated[bool, Field(validation_alias="SSL_VERIFY")] = True
    ssl_ca_bundle: Annotated[str, Field(validation_alias="SSL_CA_BUNDLE")] = ""


@lru_cache(maxsize=1)
def get_config() -> AgentConfig:
    """Get cached configuration singleton."""
    return AgentConfig()
