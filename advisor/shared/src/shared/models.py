"""Shared data models used across agents."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


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
