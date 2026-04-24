from flask import Flask, request, jsonify
import json
import os
from pathlib import Path
from datetime import datetime
from utils import record_historical_data

app = Flask(__name__)

update_count = 0
last_data = None

CURRENT_DATA_PATH = Path(__file__).with_name("current_data.json")


def _load_json_file(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}


def _atomic_write_json(path: Path, payload: dict) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=4), encoding="utf-8")
    try:
        os.replace(tmp_path, path)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

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
        existing = _load_json_file(CURRENT_DATA_PATH)
        window_open = bool(existing.get("window_open", False))
        current_data = {
            "temp": temp,
            "humidity": hum,
            "gas": gaz,
            "light": lumina,
            "window_open": window_open,
        }

        _atomic_write_json(CURRENT_DATA_PATH, current_data)

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

@app.route('/door', methods=['POST'])
def door():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"status": "error", "message": "No JSON data received"}), 400
        
        closed = data.get("closed", None)
        if closed is None:
            return jsonify({"status": "error", "message": "Missing 'closed' field"}), 400

        if isinstance(closed, str):
            closed_normalized = closed.strip().lower()
            if closed_normalized in {"true", "1", "yes", "y"}:
                closed_bool = True
            elif closed_normalized in {"false", "0", "no", "n"}:
                closed_bool = False
            else:
                return jsonify({"status": "error", "message": "Invalid 'closed' value"}), 400
        else:
            closed_bool = bool(closed)

        window_open = not closed_bool
        existing = _load_json_file(CURRENT_DATA_PATH)
        if not isinstance(existing, dict):
            existing = {}
        existing["window_open"] = window_open

        _atomic_write_json(CURRENT_DATA_PATH, existing)

        print({"door": data, "window_open": window_open})
        return jsonify({"status": "success", "window_open": window_open}), 200
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