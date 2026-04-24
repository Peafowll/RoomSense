from flask import Flask, request, jsonify

app = Flask(__name__)

# Variabilă globală pentru a stoca ultimele date (opțional)
last_data = {}

@app.route('/update', methods=['POST'])
def update_sensors():
    try:
        # Extragem datele JSON trimise de ESP32
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "No JSON data received"}), 400

        # Extragem valorile individuale
        temp = data.get('temperature')
        hum = data.get('humidity')
        gaz = data.get('Gaz')
        lumina = data.get('Lumina')

        # Afișăm datele frumos în consola Raspberry Pi
        print("\n--- Date Noi Primite ---")
        print(f"Temperatură: {temp}°C")
        print(f"Umiditate:   {hum}%")
        print(f"Gaz (MQ3):   {gaz}%")
        print(f"Lumină:      {lumina:.2f} Lux")
        print("------------------------")

        # Aici poți adăuga logică pentru salvare în baza de date sau fișier
        global last_data
        last_data = data

        return jsonify({"status": "success", "message": "Data received"}), 200

    except Exception as e:
        print(f"Eroare: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Rută opțională pentru a vedea datele într-un browser
@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "mesaj": "Serverul ruleaza!",
        "ultimele_date": last_data
    })

if __name__ == '__main__':
    # RULARE: host='0.0.0.0' este CRUCIAL pentru a fi accesibil din retea
    app.run(host='0.0.0.0', port=5000, debug=True)