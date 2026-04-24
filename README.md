
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

The system utilizes a distributed dual-node architecture designed to capture a complete picture of your indoor living environment:

### 1. Environmental Wellness Node (`ESP32-C6`)

This node focuses on the biological and atmospheric factors that influence daily health and sleep quality.
-   **Microcontroller:** ESP32-C6 (leveraging Wi-Fi 6 for stable, low-power data transmission).
-   **Sensors & Health Impact:**
    -   **DHT22:** Monitors temperature and humidity to ensure optimal thermal comfort and prevent respiratory irritation.
    -   **LDR (Photoresistor):** Tracks ambient light levels to provide "Smart Sleep" advice, helping regulate the user's circadian rhythm.
    -   **MQ-3:** Functions as an air quality proxy, detecting volatile particles to ensure the living space remains fresh.
-   **Protocol:** Transmits structured JSON payloads via `POST` requests to the `/update` endpoint.
    

### 2. Ventilation & Oxygenation Node (`Raspberry Pi 5`)

This node monitors the physical interaction with the outdoor environment to manage room "breathing" cycles.
-   **Compute Unit:** Raspberry Pi 5.
-   **Sensor:** **HC-SR04 Ultrasonic Sensor**.
-   **Logic (Fresh Air Tracking):** The system monitors the window's position via proximity detection. A distance of **< 20cm** indicates the window is closed.
-   **Actionable Insight:** This state triggers the "Oxygenation Bar" logic on the dashboard, tracking how long the room has been ventilated relative to the current season and outdoor weather.
-   **Protocol:** Syncs window status via `POST` requests to the `/door` endpoint (maintained for API compatibility).


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


## 🛠️ Technical Implementation & Optimization
-   **Precision Light Sensing:** To provide accurate sleep tips, the ESP32 performs on-board calculations to convert raw analog signals into **Lux**. This involves a voltage divider circuit logic ($10k\Omega$ fixed resistor at $3.3V$) to ensure the lighting data matches real-world conditions.
-   **Data Integrity & Reliability:** The firmware features a robust validation layer. It prevents the propagation of "Ghost Data" by filtering `NaN` (Not a Number) values from the DHT22 sensor, ensuring the health tips are always based on valid environmental readings.
-   **RPi 5 Hardware Integration:** The window monitoring logic is optimized for the **Raspberry Pi 5** architecture. By utilizing the `lgpio` library, the system ensures low-latency response times for the ultrasonic sensor, allowing for real-time updates to the "Oxygenation Bar."
-   **Predictive Analytics Engine:** The system bridges local sensor data with the **Open-Meteo API**. By applying a thermal gradient formula between the indoor and outdoor temperatures, the dashboard calculates a predictive cooling curve to tell users exactly how their room's climate will change over the next 5 minutes.


