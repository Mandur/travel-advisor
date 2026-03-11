"""Travel advisor agent definition using LangGraph."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from copilotkit import CopilotKitMiddleware
from langchain.agents import create_agent as _build_agent
from langchain_core.tools import tool

from shared.config import get_config
from shared.models import HotelPricing, PriceForecast
from shared.utils import create_llm, setup_logging

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from langgraph.checkpoint.base import BaseCheckpointSaver

logger = setup_logging("travel-advisor-agent")

TRAVEL_ADVISOR_INSTRUCTIONS = """\
You are a travel advisor agent for a hospitality platform.
You help users find hotel pricing information and provide price forecasts.

Use the available tools to retrieve pricing data and forecasts.
Always present information clearly with prices, dates, and availability status."""


@tool
def get_hotel_pricing(
    hotel_name: str,
    location: str,
    check_in: str,
    check_out: str,
) -> dict:
    """Look up current hotel pricing and availability.

    Args:
        hotel_name: Name of the hotel.
        location: City or region of the hotel.
        check_in: Check-in date in YYYY-MM-DD format.
        check_out: Check-out date in YYYY-MM-DD format.

    Returns:
        Hotel pricing details including availability and total cost.
    """
    check_in_date = date.fromisoformat(check_in)
    check_out_date = date.fromisoformat(check_out)
    nights = (check_out_date - check_in_date).days

    # Placeholder -- replace with actual pricing API integration
    price_per_night = 150.0
    pricing = HotelPricing(
        hotel_name=hotel_name,
        location=location,
        check_in=check_in_date,
        check_out=check_out_date,
        price_per_night=price_per_night,
        total_price=price_per_night * nights,
        availability=True,
    )
    logger.info("Retrieved pricing for %s: $%.2f/night", hotel_name, price_per_night)
    return pricing.model_dump(mode="json")


@tool
def get_price_forecast(
    destination: str,
    forecast_date: str,
) -> dict:
    """Get a price forecast for a destination on a specific date.

    Args:
        destination: City or region to forecast prices for.
        forecast_date: Target date in YYYY-MM-DD format.

    Returns:
        Price forecast with predicted pricing and trend.
    """
    forecast = PriceForecast(
        destination=destination,
        forecast_date=date.fromisoformat(forecast_date),
        predicted_price=165.0,
        trend="stable",
    )
    logger.info(
        "Generated forecast for %s: $%.2f (%s)",
        destination,
        forecast.predicted_price,
        forecast.trend,
    )
    return forecast.model_dump(mode="json")


def create_agent(
    checkpointer: "BaseCheckpointSaver | None" = None,
) -> "CompiledStateGraph":
    """Create and return the travel advisor agent as a compiled LangGraph."""
    config = get_config()
    llm = create_llm(config.gpt5_mini_deployment)
    graph = _build_agent(
        llm,
        [get_hotel_pricing, get_price_forecast],
        middleware=[CopilotKitMiddleware()],
        system_prompt=TRAVEL_ADVISOR_INSTRUCTIONS,
        checkpointer=checkpointer,
    )
    logger.info("Travel advisor agent created successfully")
    return graph
