import argparse
import json
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from devices.sensors import SENSOR_RANGES, initial_value, next_value


def build_payload(device_id, sensor_type, value):
    return json.dumps({
        "device_id": device_id,
        "sensor_type": sensor_type,
        "value": value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def run(broker_host, broker_port, device_id, sensor_type, interval, max_messages=None):
    topic = f"home/{device_id}/{sensor_type}"
    client = mqtt.Client(client_id=device_id)
    client.connect(broker_host, broker_port)

    value = initial_value(sensor_type)
    sent = 0
    try:
        while max_messages is None or sent < max_messages:
            value = next_value(sensor_type, value)
            payload = build_payload(device_id, sensor_type, value)
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
    run(
        args.broker_host,
        args.broker_port,
        args.device_id,
        args.sensor_type,
        args.interval,
        args.max_messages,
    )
