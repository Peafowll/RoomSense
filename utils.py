import json
import os
from pathlib import Path
import requests
from datetime import datetime, timedelta



def get_current_weather(location: tuple[float, float]):
    """Get outside temperature and whether it's raining (Open-Meteo).

    Returns:
        (temperature_c, is_raining) or None on request failure.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": location[0],
        "longitude": location[1],
        "current": "temperature_2m,rain"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        
        data = response.json()
        current_data = data.get("current", {})
        temperature_c = current_data.get("temperature_2m")
        rain_amount = current_data.get("rain", 0.0)
        
        is_raining = rain_amount > 0.0
        
        return temperature_c, is_raining
        
    except requests.RequestException:
        return None
    



if  __name__ ==  "__main__":
    location_tuple = (4.6243, -74.0636)
    result = get_current_weather(location_tuple)
    print(result)