# Code the Future 2026

## 🌿 RoomSense
**RoomSense** is an intelligent indoor environment analyzer designed to improve user well-being. Unlike standard monitoring systems, RoomSense doesn't just show data—it provides **actionable health tips** based on environmental factors, circadian rhythms, and outdoor weather integration.

## 🚀 Key Features
### 🛌 Circadian Rhythm Support
-   **Smart Lighting Alerts:** Using a Photoresistor (LDR), the system monitors light intensity. After **10:00 PM**, if high light levels are detected, the dashboard advises the user to dim the lights to improve sleep quality and maintain a healthy internal clock.

### 🌬️ Dynamic Oxygenation & Air Quality
-   **Oxygenation Bar:** A real-time visual indicator that "charges up" when the window is detected as open.
-   **Intelligent Ventilation:** Based on the current **season** and **weather conditions** (via Open-Meteo API), the system recommends ventilation schedules (e.g., in Spring: 6 times a day for at least 5 minutes).
-   **Air Quality Proxy:** Utilizes an MQ-3 sensor to monitor volatile organic compounds and general air freshness.

### 🌡️ Predictive Thermal Analytics
-   **Cooling Prediction:** By comparing internal temperature with external data from **Open-Meteo**, the system predicts how fast the room will cool down and estimates the temperature for the next 5 minutes.
-   **Weather Awareness:** Integration of rain and extreme cold alerts to suggest whether opening the window is advisable.

### 📈 Historical Data & Visualization
-   **JSON Logging:** All data is stored in JSON format.
-   **Streamlit Dashboard:** Users can upload historical logs to generate interactive graphs, allowing them to track their living habits over time.

## 🛠️ Hardware Architecture
The system consists of two specialized sensor nodes and a central server:
1. Environment Node (ESP32-C6) 
Handles ambient data collection and Wi-Fi transmission.
* **Microcontroller:** ESP32-C6 (Next-gen Wi-Fi 6 support).
* **Sensors:**
	* DHT22: Digital Temperature & Humidity.
	* LDR: Analog Light Intensity (converted to Lux).
	* MQ3: Analog Gas/Smoke levels (mapped to percentage).
* **Protocol:** Sends JSON payloads via `POST` requests to the `/update` endpoint.

2. Window Security Node (Raspberry Pi 5) 
Monitors the physical state of a window using proximity detection.
* **Compute:** Raspberry Pi 5.
* **Sensor**: HC-SR04 Ultrasonic Sensor.
* **Logic:** The system treats the window as Closed if the distance detected is less than 20cm.
* **Technical Note:** Although the internal code/API uses door terminology, it is functionally applied to Window Monitoring.
* **Protocol:** Sends state data via `POST` requests to the `/door` endpoint.

## 💻 Software Stack

Technologies:
-   **Frontend & Dashboard:** Streamlit (Python)
-   **Backend Logic:** Python (FastAPI/Flask)
-   **Firmware:** C++/Arduino (ESP32-C6)
-   **External APIs:** Open-Meteo (Weather Data)
-   **Data Format:** JSON

## 🔄 System Flow

1.  **Data Collection:** ESP32 and Raspberry Pi gather environmental and proximity data.
2.  **Transmission:** Nodes send HTTP POST requests with JSON payloads to the central server.
3.  **Processing:** The backend receives the data and stores/updates the current room state.
4.  **Visualization:** **Streamlit** fetches the data and displays it in an intuitive, user-friendly interface for the end-user.

## ⚙️ Setup & Installation
ESP32-C6 Configuration
* Install required libraries: `WiFi`, `HTTPClient`, and `DHT` sensor library.
* Update your Wi-Fi credentials in the source code.
* Upload the sketch using Arduino IDE or PlatformIO.

Raspberry Pi 5 Configuration
* Ensure Python 3 is installed.
* Install the necessary libraries: `pip install gpiozero lgpio requests`
* Run the monitoring script:  `python window_sensor.py`

### Server & Dashboard Configuration
Install backend requirements: `pip install flask streamlit plotly pandas requests`
Start the Flask data aggregation server: `python server.py` 

In a separate terminal, launch the interactive dashboard: `streamlit run dashboard.py`

## 📊 API Data Format
Environment Update (ESP32) Endpoint: `POST /update`
`{
"temperature": 24.5,
"humidity": 45.2,
"Gaz": 15,
"Lumina": 320.5
}`

Window Status Update (RPi 5) Endpoint: `POST /door` (Context: Window Status)
`{
"closed": true,
"distanta": 12.5
}`

## 📝 Technical Implementation Details
* **Lux Calculation:** The ESP32 code uses a standard formula to convert raw ADC values into Lux, accounting for the fixed resistor ($10k\Omega$) and VIn ($3.3V$).
* **Safety Checks:** The firmware includes validation to prevent sending `NaN` values if the DHT22 sensor fails to initialize.
* **GPIO Management:** The Raspberry Pi script utilizes the `lgpio` factory to ensure compatibility with the Raspberry Pi 5 hardware architecture.


