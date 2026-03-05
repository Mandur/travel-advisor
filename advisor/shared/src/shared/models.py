"""Shared data models used across agents."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class UserIntent(str, Enum):
    """Possible user intents identified by the routing agent."""

    TRAVEL = "travel"
    MEETING = "meeting"
    GENERAL = "general"


class IntentResult(BaseModel):
    """Result from the routing agent's intent classification."""

    intent: UserIntent
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


class HotelPricing(BaseModel):
    """Hotel pricing information returned by the travel advisor."""

    hotel_name: str
    location: str
    check_in: date
    check_out: date
    price_per_night: float
    currency: str = "USD"
    total_price: float = 0.0
    availability: bool = True


class PriceForecast(BaseModel):
    """Price forecast for a hotel or destination."""

    destination: str
    forecast_date: date
    predicted_price: float
    currency: str = "USD"
    trend: str = ""  # "rising", "falling", "stable"


class MeetingRequest(BaseModel):
    """Meeting scheduling request handled by the meeting broker."""

    title: str
    date: date
    start_time: str
    end_time: str
    attendees: list[str] = Field(default_factory=list)
    room_preferences: list[str] = Field(default_factory=list)
    amenities: list[str] = Field(default_factory=list)
    notes: str = ""


class MeetingResponse(BaseModel):
    """Response from the meeting broker after scheduling."""

    confirmed: bool
    meeting_id: str = ""
    room_assigned: str = ""
    amenities_confirmed: list[str] = Field(default_factory=list)
    message: str = ""
