import json
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

if __name__ == "__main__":
    current_data = {
        "temp" : 40,
        "air" : 60,
        "humidity" : 70,
        "light" : 0,
        "window_open" : True
    }

    record_historical_data(data=current_data, timestamp=datetime.now())