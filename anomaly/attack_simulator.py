import argparse
import json
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


def build_payload(device_id, sensor_type, value):
    return json.dumps({
        "device_id": device_id,
        "sensor_type": sensor_type,
        "value": value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device-id", default="attacker-device")
    parser.add_argument("--sensor-type", default="temperature")
    parser.add_argument("--value", type=float, default=85.0)
    parser.add_argument("--broker-host", default="localhost")
    parser.add_argument("--broker-port", type=int, default=1883)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--interval", type=float, default=1.0)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    client = mqtt.Client(client_id="attack-simulator")
    client.connect(args.broker_host, args.broker_port)

    topic = f"home/{args.device_id}/{args.sensor_type}"
    for _ in range(args.count):
        payload = build_payload(args.device_id, args.sensor_type, args.value)
        client.publish(topic, payload)
        print(f"[ATTACK] -> {topic}: {payload}")
        time.sleep(args.interval)

    client.disconnect()
