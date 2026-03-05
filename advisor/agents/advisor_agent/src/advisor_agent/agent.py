"""Routing agent — supervisor that orchestrates domain agents using agent-as-tool pattern."""

from __future__ import annotations

from agent_framework import Agent
from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential

from meeting_broker.agent import create_agent as create_meeting_broker_agent
from travel_advisor_agent.agent import create_agent as create_travel_advisor_agent
from shared.config import get_config
from shared.utils import setup_logging

logger = setup_logging("routing-agent")

SUPERVISOR_INSTRUCTIONS = """You are a helpful assistant for a hospitality platform.
Users ask questions about hotel travel and meeting scheduling.
Use the specialist tools to gather information, then respond directly to the user.

Rules:
- NEVER mention tool names (travel_advisor, meeting_broker)
- NEVER say "I called a tool" or "The specialist said"
- NEVER reveal internal API names, agent names, or system names
- Synthesize information from specialists into one coherent, helpful response
- If a capability failed, describe the gap in user terms
  (e.g., "I wasn't able to retrieve pricing details right now — please try again")
- Be concise and professional"""


def create_agent() -> Agent:
    """Create and return the routing supervisor agent.

    Domain agents are wrapped as tools via ``Agent.as_tool()`` and passed to
    the supervisor.  The supervisor uses the larger model; domain agents each
    use the smaller model.
    """
    config = get_config()
    credential = DefaultAzureCredential()

    travel_advisor = create_travel_advisor_agent()
    meeting_broker = create_meeting_broker_agent()

    supervisor_client = AzureOpenAIResponsesClient(
        project_endpoint=config.azure_ai_project_endpoint,
        deployment_name=config.gpt5_2_chat_deployment,
        credential=credential,
    )

    agent = supervisor_client.as_agent(
        name="RoutingAgent",
        instructions=SUPERVISOR_INSTRUCTIONS,
        tools=[
            travel_advisor.as_tool(
                name="travel_advisor",
                description="Use for questions about hotel pricing, availability, destinations, price forecasts, and travel planning.",
            ),
            meeting_broker.as_tool(
                name="meeting_broker",
                description="Use for RFP submissions and inquiries about group meetings and events, including sourcing venue proposals, comparing conference room options, negotiating rates, and coordinating catering, AV equipment, and room setup.",
            ),
        ],
    )

    logger.info("Routing supervisor agent created successfully")
    return agent
