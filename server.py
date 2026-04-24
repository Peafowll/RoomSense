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
DOOR_CURRENT_PATH = Path(__file__).with_name("door_current.json")
DOOR_EVENTS_PATH = Path(__file__).with_name("door_events.json")
AIR_OXYGENATION_PATH = Path(__file__).with_name("air_oxygen_bars.json")
AIR_OXYGENATION_FALLBACK_PATH = Path(__file__).with_name("air_oxygenation_bars.json")


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


def _get_current_oxygenation() -> int | None:
    """Read current oxygenation (0-100) from air_oxygen(_ation)_bars.json."""
    for path in (AIR_OXYGENATION_PATH, AIR_OXYGENATION_FALLBACK_PATH):
        payload = _load_json_file(path)
        if not isinstance(payload, dict):
            continue
        value = payload.get("current_oxygen")
        try:
            value_num = int(value)
        except (TypeError, ValueError):
            continue
        return max(0, min(100, value_num))

    return None

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
        
        # Data translate (sensor-only; door/window is tracked separately)
        current_data = {
            "temp": temp,
            "humidity": hum,
            "gas": gaz,
            "light": lumina,
        }

        oxygenation = _get_current_oxygenation()
        if oxygenation is not None:
            current_data["oxygenation"] = oxygenation

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
        distanta = data.get("distanta", None)

        door_current = _load_json_file(DOOR_CURRENT_PATH)
        if not isinstance(door_current, dict):
            door_current = {}

        prev_window_open = door_current.get("window_open", None)
        prev_closed = door_current.get("closed", None)

        now = datetime.now()
        door_current.update({
            "window_open": window_open,
            "closed": closed_bool,
            "distanta": distanta,
            "updated_at": now.isoformat(),
        })

        _atomic_write_json(DOOR_CURRENT_PATH, door_current)

        event_saved = False
        state_changed = (prev_window_open is None) or (bool(prev_window_open) != window_open)
        state_changed = state_changed or (prev_closed is None) or (bool(prev_closed) != closed_bool)
        if state_changed:
            try:
                events = _load_json_file(DOOR_EVENTS_PATH)
                if not isinstance(events, dict):
                    events = {}

                ts = now.isoformat()
                # Extremely unlikely collision, but keep keys unique.
                while ts in events:
                    now = datetime.now()
                    ts = now.isoformat()

                events[ts] = {
                    "window_open": window_open,
                    "closed": closed_bool,
                    "distanta": distanta,
                }
                _atomic_write_json(DOOR_EVENTS_PATH, events)
                event_saved = True
            except Exception as history_error:
                print(f"Door event write failed: {history_error}")

        print({"door": data, "window_open": window_open, "event_saved": event_saved})
        return jsonify({
            "status": "success",
            "message": "Data received",
            "window_open": window_open,
            "event_saved": event_saved,
        }), 200
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