import json
import requests
from datetime import datetime

def record_historical_data(data : dict, timestamp : datetime):
    try:
        with open("historical_data.json", "r") as historical_file:
            loaded_data = json.load(historical_file)
    except (FileNotFoundError, json.JSONDecodeError):
        loaded_data = {}

    loaded_data[str(timestamp)] = data


    with open("historical_data.json", "w") as historical_file:
        json.dump(loaded_data, historical_file, indent=4)


def get_current_weather(location : tuple):
    """
    Gets current weather for location.
    Params :
        location (tuple) : A tuple containing the latitude and logitude of the location you want to check.
    Returns :
        The temperature in Celsius and wind speed at the location.
    
    """
    url = "https://api.open-meteo.com/v1/forecast"
    
    params = {
        "latitude": location[0],
        "longitude": location[1],
        "current_weather": True
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        weather_data = response.json()
        
        current = weather_data['current_weather']
        

        return current["temperature"], current["windspeed"]

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")


if  __name__ ==  "__main__":
    location_tuple = (45.6486, 225.6061)
    get_current_weather(location_tuple)