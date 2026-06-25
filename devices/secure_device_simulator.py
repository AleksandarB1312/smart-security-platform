import argparse
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt

from devices.zkp_auth_client import authenticate

SENSOR_RANGES = {
    "temperature": (18.0, 26.0),
    "humidity": (30.0, 60.0),
    "motion": (0, 1),
}

KEYS_DIR = Path(__file__).parent / "keys"


def load_private_key(device_id):
    key_file = KEYS_DIR / f"{device_id}.json"
    if not key_file.exists():
        raise FileNotFoundError(
            f"Nema sacuvanog kljuca za {device_id}. "
            f"Pokreni prvo: python -m devices.register_device --device-id {device_id}"
        )
    with open(key_file) as file:
        data = json.load(file)
    return data["private_key"]


def generate_reading(sensor_type):
    if sensor_type == "motion":
        return random.choice([0, 1])
    low, high = SENSOR_RANGES[sensor_type]
    return round(random.uniform(low, high), 2)


def build_payload(device_id, sensor_type):
    return json.dumps({
        "device_id": device_id,
        "sensor_type": sensor_type,
        "value": generate_reading(sensor_type),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def run(broker_host, broker_port, device_id, sensor_type, interval, token, max_messages=None):
    topic = f"home/{device_id}/{sensor_type}"
    client = mqtt.Client(client_id=device_id)
    client.username_pw_set(device_id, token)
    client.connect(broker_host, broker_port)

    sent = 0
    try:
        while max_messages is None or sent < max_messages:
            payload = build_payload(device_id, sensor_type)
            client.publish(topic, payload)
            print(f"[{device_id}] -> {topic}: {payload}")
            sent += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--sensor-type", choices=list(SENSOR_RANGES.keys()), required=True)
    parser.add_argument("--broker-host", default="localhost")
    parser.add_argument("--broker-port", type=int, default=1883)
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--max-messages", type=int, default=None)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    private_key = load_private_key(args.device_id)

    print(f"[{args.device_id}] pokrecem ZKP autentikaciju...")
    token = authenticate(args.device_id, private_key)
    print(f"[{args.device_id}] ZKP dokaz uspesan, token dobijen")

    run(
        args.broker_host,
        args.broker_port,
        args.device_id,
        args.sensor_type,
        args.interval,
        token,
        args.max_messages,
    )
