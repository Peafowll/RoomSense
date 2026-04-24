from flask import Flask, request, jsonify
import json
import os
from pathlib import Path
from datetime import datetime
from utils import record_historical_data

app = Flask(__name__)

update_count = 0

@app.route('/update', methods=['POST'])
def update_sensors():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No JSON data received"}), 400

        temp = data.get('temperature', 0)
        hum = data.get('humidity', 0)
        gaz = data.get('Gaz', 0)
        lumina = data.get('Lumina', 0)

        print("\n--- Date Noi Primite ---")
        print(f"Temperatură: {temp}°C")
        print(f"Umiditate:   {hum}%")
        print(f"Gaz (MQ3):   {gaz}%")
        print(f"Lumină:      {lumina:.2f} Lux")
        print("------------------------")
        
        # Data translate
        current_data = {
            "temp": temp,
            "humidity": hum,
            "gas": gaz,
            "light": lumina,
            "window_open": False 
        }

        current_path = Path(__file__).with_name("current_data.json")
        tmp_path = current_path.with_suffix(current_path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(current_data, indent=4), encoding="utf-8")
        os.replace(tmp_path, current_path)

        global update_count 
        update_count+= 1
        if update_count % 5 == 0:
            now = datetime.now()
            record_historical_data(current_data, now)

        global last_data
        last_data = data

        return jsonify({"status": "success", "message": "Data saved to JSON"}), 200

    except Exception as e:
        print(f"Eroare: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "mesaj": "Serverul ruleaza!",
        "ultimele_date": last_data
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)