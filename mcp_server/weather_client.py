"""
OpenWeatherMap API client.
Handles all HTTP calls to the upstream REST API.
"""

import os
import httpx
from typing import Any

BASE_URL = "https://api.openweathermap.org/data/2.5"
GEO_URL = "http://api.openweathermap.org/geo/1.0"


def _api_key() -> str:
    key = os.getenv("OPENWEATHER_API_KEY", "")
    if not key:
        raise RuntimeError("OPENWEATHER_API_KEY environment variable is not set")
    return key


async def fetch_current_weather(city: str) -> dict[str, Any]:
    """Call /weather endpoint and return normalized payload."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{BASE_URL}/weather",
            params={"q": city, "appid": _api_key(), "units": "metric"},
        )
        r.raise_for_status()
        d = r.json()

    return {
        "city": d["name"],
        "country": d["sys"]["country"],
        "temperature_celsius": round(d["main"]["temp"], 1),
        "feels_like_celsius": round(d["main"]["feels_like"], 1),
        "humidity_percent": d["main"]["humidity"],
        "pressure_hpa": d["main"]["pressure"],
        "condition": d["weather"][0]["description"].capitalize(),
        "wind_speed_mps": d["wind"]["speed"],
        "wind_direction_deg": d["wind"].get("deg"),
        "visibility_meters": d.get("visibility"),
        "cloudiness_percent": d["clouds"]["all"],
    }


async def fetch_forecast(city: str, days: int) -> dict[str, Any]:
    """Call /forecast endpoint (3-hour intervals) and aggregate into daily summaries."""
    days = max(1, min(days, 5))
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"{BASE_URL}/forecast",
            params={"q": city, "appid": _api_key(), "units": "metric", "cnt": days * 8},
        )
        r.raise_for_status()
        d = r.json()

    daily: dict[str, list] = {}
    for item in d["list"]:
        date = item["dt_txt"].split(" ")[0]
        daily.setdefault(date, []).append(
            {
                "time": item["dt_txt"].split(" ")[1],
                "temp_celsius": round(item["main"]["temp"], 1),
                "feels_like_celsius": round(item["main"]["feels_like"], 1),
                "condition": item["weather"][0]["description"].capitalize(),
                "humidity_percent": item["main"]["humidity"],
                "wind_speed_mps": item["wind"]["speed"],
            }
        )

    return {
        "city": d["city"]["name"],
        "country": d["city"]["country"],
        "days_requested": days,
        "forecast": {date: slots for date, slots in list(daily.items())[:days]},
    }


async def fetch_air_quality(city: str) -> dict[str, Any]:
    """Resolve city → lat/lon via Geocoding API, then call /air_pollution."""
    async with httpx.AsyncClient(timeout=10) as client:
        geo = await client.get(
            f"{GEO_URL}/direct",
            params={"q": city, "limit": 1, "appid": _api_key()},
        )
        geo.raise_for_status()
        geo_data = geo.json()

        if not geo_data:
            return {"error": f"City '{city}' not found in geocoding database"}

        lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]

        aq = await client.get(
            f"{BASE_URL}/air_pollution",
            params={"lat": lat, "lon": lon, "appid": _api_key()},
        )
        aq.raise_for_status()
        aq_data = aq.json()

    aqi_labels = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}
    aqi_index = aq_data["list"][0]["main"]["aqi"]
    components = aq_data["list"][0]["components"]

    return {
        "city": city,
        "latitude": lat,
        "longitude": lon,
        "aqi_index": aqi_index,
        "aqi_label": aqi_labels.get(aqi_index, "Unknown"),
        "pollutants": {
            "pm2_5_ugm3": components["pm2_5"],
            "pm10_ugm3": components["pm10"],
            "co_ugm3": components["co"],
            "no2_ugm3": components["no2"],
            "o3_ugm3": components["o3"],
            "so2_ugm3": components["so2"],
        },
    }
