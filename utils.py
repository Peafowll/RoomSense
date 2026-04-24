import json
import os
from pathlib import Path
import requests
from datetime import datetime, timedelta



def get_current_weather(location: tuple[float, float]):
    """Get outside weather (Open-Meteo).

    Returns:
        (temperature_c, is_raining, wind_speed_m_s) or None on request failure.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": location[0],
        "longitude": location[1],
        "current": "temperature_2m,rain,wind_speed_10m"
        ,"wind_speed_unit": "ms"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        
        data = response.json()
        current_data = data.get("current", {})

        temperature_raw = current_data.get("temperature_2m")
        try:
            temperature_c = float(temperature_raw) if temperature_raw is not None else None
        except (TypeError, ValueError):
            temperature_c = None

        rain_raw = current_data.get("rain")
        try:
            rain_amount = float(rain_raw) if rain_raw is not None else 0.0
        except (TypeError, ValueError):
            rain_amount = 0.0

        wind_raw = current_data.get("wind_speed_10m")
        try:
            wind_speed_m_s = float(wind_raw) if wind_raw is not None else None
        except (TypeError, ValueError):
            wind_speed_m_s = None

        is_raining = rain_amount > 0.0

        return temperature_c, is_raining, wind_speed_m_s
        
    except requests.RequestException:
        return None
    



if  __name__ ==  "__main__":
    location_tuple = (4.6243, -74.0636)
    result = get_current_weather(location_tuple)
    print(result)