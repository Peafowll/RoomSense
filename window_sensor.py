import os
os.environ['GPIOZERO_PIN_FACTORY'] = 'lgpio'
from gpiozero import DistanceSensor
from time import sleep
import requests

server_ip = "192.168.253.114"
port = 5000
URL = f"http://{server_ip}:{port}/door"

sensor = DistanceSensor(echo=27, trigger=17)

print(f"Senzor pornit. Trimit date la {URL}...")

try:
    while True:
        distanta = round(sensor.distance * 100, 2)
        if distanta < 20:
            closed = True
        else:
            closed = False
        payload = {"closed": closed, "distanta": distanta}
        try:
            raspuns = requests.post(URL, json=payload, timeout=2)
            print(f"Distanta: {distanta} cm | Usa inchisa: {closed} | Status: {raspuns.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Eroare conexiune server: {e}")
        sleep(1)
except KeyboardInterrupt:
    print("\nProgram oprit de utilizator.")