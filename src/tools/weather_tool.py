from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import structlog
import requests
from typing import Dict, Any, Optional
from src.config.settings import Settings

logger = structlog.get_logger(__name__)

class WeatherInput(BaseModel):
    """Input schema for WeatherTool."""
    location: str = Field(..., description="The location to get weather for")

class WeatherTool(BaseTool):
    name: str = "get_weather"
    description: str = """
    Get current weather and forecast for a location.
    Provide the location name and optionally specify if you want current conditions or forecast.
    Returns formatted weather information including temperature, conditions, and other relevant data.
    """
    args_schema: type[BaseModel] = WeatherInput

    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings  # Store settings as private attribute
        # We'll use self._settings.openweather_api_key directly in the _run method

    def _run(self, location: str) -> str:
        """
        Get weather information for a location using WeatherAPI.com.

        Args:
            location: The location to get weather for

        Returns:
            Formatted weather information as a string
        """
        try:
            # WeatherAPI.com endpoint for forecast
            url = "https://api.weatherapi.com/v1/forecast.json"
            
            # Get weather data with 3 days of forecast
            params = {
                "key": self._settings.openweather_api_key,  # Using the API key from settings
                "q": location,
                "days": 3,
                "aqi": "no",
                "alerts": "no"
            }

            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Format the response
            current = data["current"]
            forecast_days = data["forecast"]["forecastday"]
            
            # Current weather
            weather_info = f"""
            Current weather in {data['location']['name']}, {data['location']['country']}:
            Temperature: {current['temp_c']}°C
            Feels like: {current['feelslike_c']}°C
            Conditions: {current['condition']['text']}
            Humidity: {current['humidity']}%
            Wind Speed: {current['wind_kph']} km/h
            
            3-Day Forecast:
            """
            
            # Add forecast for each day
            for day in forecast_days:
                date = day["date"]
                forecast = day["day"]
                weather_info += f"""
            {date}:
            High: {forecast['maxtemp_c']}°C
            Low: {forecast['mintemp_c']}°C
            Conditions: {forecast['condition']['text']}
            Chance of rain: {forecast['daily_chance_of_rain']}%
            """

            return weather_info.strip()

        except requests.RequestException as e:
            logger.error("Weather API request failed", error=str(e))
            return f"Sorry, I encountered an error getting weather data for {location}. Error: {str(e)}"
