# Code the Future 2026

## 🌿 RoomSense
**RoomSense** is an integrated smart environment and security monitoring system designed for hackathons. It provides real-time data on indoor air quality, lighting conditions, and window security. The project features a distributed architecture using **ESP32-C6** and **Raspberry Pi 5**, communicating via a centralized HTTP-based infrastructure.

## 🚀 Key Features
* **Climate Monitoring:** Real-time temperature and humidity tracking via DHT22.
* **Air Quality Analysis:** Detection of gases and smoke levels using the MQ3 sensor.
* **Adaptive Lighting:** Accurate calculation of light intensity in Lux using a Photoresistor (LDR).
* **Window Security:** Ultrasonic distance monitoring to track window status (Open/Closed).
* **Centralized Dashboard:** All data is pushed to a central server for processing and visualization.

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

# 💻 Software Stack
**RepositoryLink:** [GitHub RoomSense](https://github.com/Peafowll/RoomSense)

Technologies:
* **C++/Arduino:** Firmware for the ESP32-C6.
* **Python (gpiozero, requests):** Logic and communication for Raspberry Pi 5.
* **Flask/Express (Server):** Backend hosted at `192.168.253.114` to aggregate data.

# ⚙️ Setup & Installation
ESP32-C6 Configuration
* Install required libraries: `WiFi`, `HTTPClient`, and `DHT` sensor library.
* Update your Wi-Fi credentials in the source code.
* Upload the sketch using Arduino IDE or PlatformIO.

Raspberry Pi 5 Configuration
* Ensure Python 3 is installed.
* Install the necessary libraries: `pip install gpiozero lgpio requests`

Run the script: `python window_sensor.py`

# 📊 API Data Format
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

📝 Technical Implementation Details
* **Lux Calculation:** The ESP32 code uses a standard formula to convert raw ADC values into Lux, accounting for the fixed resistor ($10k\Omega$) and VIn ($3.3V$).
* **Safety Checks:** The firmware includes validation to prevent sending `NaN` values if the DHT22 sensor fails to initialize.
* **GPIO Management:** The Raspberry Pi script utilizes the `lgpio` factory to ensure compatibility with the Raspberry Pi 5 hardware architecture.