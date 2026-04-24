#include <WiFi.h>
#include <HTTPClient.h>
#include "DHT.h"

const char* ssid = "iPhone";
const char* password = "12234567";
const char* serverUrl = "http://172.20.10.11:5000/update";

#define DHTPIN 6 
#define LDRPIN 4 
#define MQ3PIN 5 
#define DHTTYPE DHT22

DHT dht(DHTPIN, DHTTYPE);

const float VIN = 3.3;
const float R_FIXA = 10000;  
const int ADC_RES = 4095;

void setup_wifi(){
  WiFi.begin(ssid, password);
  Serial.print("Conectare la WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi conectat!");
  Serial.print("Adresa IP: ");
  Serial.println(WiFi.localIP());
}

void setup() {
  // 1. Pornim Seriala PRIMA DATA
  Serial.begin(115200);
  delay(1000); 

  // 2. Conectăm WiFi
  setup_wifi(); // Am adăugat ; aici

  analogReadResolution(12);
  dht.begin();

  Serial.println("--- Sistem pornit ---");
}

void loop() {
  // --- 1. Citire DHT22 ---
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  // --- 2. Citire LDR (Lux) ---
  int ldrRaw = analogRead(LDRPIN);
  float ldrVoltage = ldrRaw * (VIN / (float)ADC_RES);
  
  float lux = 0;
  if (ldrVoltage > 0.01) { // Protecție împărțire la zero
    float resistanceLDR = (R_FIXA * (VIN - ldrVoltage)) / ldrVoltage;
    lux = 500 / (resistanceLDR / 1000.0);
  }

  // --- 3. Citire MQ3 ---
  int mq3Raw = analogRead(MQ3PIN);
  int mq3Procent = map(mq3Raw, 1800, 3800, 0, 100);
  mq3Procent = constrain(mq3Procent, 0, 100);

  // --- Logica de trimitere date ---
  if (WiFi.status() == WL_CONNECTED) {
    // Trimitem datele doar dacă senzorul DHT returnează valori valide
    if (!isnan(h) && !isnan(t)) {
      HTTPClient http;
      http.begin(serverUrl);
      http.addHeader("Content-Type", "application/json");

      // Construim JSON-ul
      String payload = "{\"temperature\":" + String(t) + 
                       ",\"humidity\":" + String(h) + 
                       ",\"Gaz\":" + String(mq3Procent) + 
                       ",\"Lumina\":" + String(lux) + "}";
      
      int httpResponseCode = http.POST(payload);

      Serial.print("HTTP POST: ");
      Serial.println(httpResponseCode);
      http.end();
    } else {
      Serial.println("Eroare senzori: Nu trimit date JSON invalide.");
    }
  }

  // Debug Serial
  Serial.print("T: "); Serial.print(t);
  Serial.print(" | L: "); Serial.print(lux);
  Serial.print(" | G: "); Serial.println(mq3Procent);

  delay(2000);
}