import json
import os
from pathlib import Path
import requests
from datetime import datetime, timedelta


def record_historical_data(data : dict, timestamp : datetime):
    """
    Writes a dictionary of data to the `historical_data.json` file, at a timestamp.
    Params :
        data (dict) : The data to be saved.
        timestamp (datetime) : The time at which the data was recorded.
    """
    historical_path = Path(__file__).with_name("historical_data.json")

    try:
        loaded_data = json.loads(historical_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        loaded_data = {}

    loaded_data[timestamp.isoformat()] = data

    cutoff_time = timestamp - timedelta(days=2)
    filtered_data = {}

    for time_str, val in loaded_data.items():
        try:
            record_time = datetime.fromisoformat(time_str)
            if record_time >= cutoff_time:
                filtered_data[time_str] = val
                
        except ValueError:
            continue

    # Atomic write to avoid dashboard reading partial JSON mid-write.
    tmp_path = historical_path.with_suffix(historical_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(filtered_data, indent=4), encoding="utf-8")
    try:
        os.replace(tmp_path, historical_path)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

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