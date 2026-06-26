import json
import threading
import time
from collections import deque

import paho.mqtt.client as mqtt
import requests
from flask import Flask, jsonify, render_template

GATEWAY_URL = "http://localhost:8000"
BROKER_HOST = "localhost"
BROKER_PORT = 1883
HISTORY_LENGTH = 30
ALERTS_LENGTH = 50

app = Flask(__name__)
state_lock = threading.Lock()
device_readings = {}
anomaly_alerts = deque(maxlen=ALERTS_LENGTH)


def handle_sensor_message(payload):
    device_id = payload.get("device_id")
    sensor_type = payload.get("sensor_type")
    value = payload.get("value")
    if device_id is None or value is None:
        return

    with state_lock:
        device = device_readings.setdefault(device_id, {
            "sensor_type": sensor_type,
            "history": deque(maxlen=HISTORY_LENGTH),
        })
        device["sensor_type"] = sensor_type
        device["last_value"] = value
        device["last_seen"] = time.time()
        device["history"].append({"t": time.time(), "v": value})


def handle_alert_message(payload):
    with state_lock:
        anomaly_alerts.appendleft({
            "device_id": payload.get("device_id"),
            "sensor_type": payload.get("sensor_type"),
            "value": payload.get("value"),
            "time": time.time(),
        })


def on_connect(client, userdata, flags, rc):
    client.subscribe("home/+/+")
    client.subscribe("alerts/+/+")


def on_message(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode())
    except json.JSONDecodeError:
        return

    if message.topic.startswith("alerts/"):
        handle_alert_message(payload)
    else:
        handle_sensor_message(payload)


def start_mqtt_listener():
    client = mqtt.Client(client_id="dashboard-listener")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect_async(BROKER_HOST, BROKER_PORT)
    client.loop_start()
    return client


def get_security_failures():
    try:
        response = requests.get(f"{GATEWAY_URL}/security/failed-attempts", timeout=2)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    with state_lock:
        devices = [
            {
                "device_id": device_id,
                "sensor_type": data["sensor_type"],
                "last_value": data["last_value"],
                "last_seen": data["last_seen"],
                "history": list(data["history"]),
            }
            for device_id, data in device_readings.items()
        ]
        alerts = list(anomaly_alerts)

    return jsonify({
        "devices": devices,
        "alerts": alerts,
        "security_failures": get_security_failures(),
    })


mqtt_client = start_mqtt_listener()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
