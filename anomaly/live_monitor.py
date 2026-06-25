import json
from pathlib import Path

import joblib
import paho.mqtt.client as mqtt

from anomaly.features import RollingHistory

MODELS_DIR = Path(__file__).parent / "models"
ALERT_TOPIC_TEMPLATE = "alerts/{device_id}/{sensor_type}"


def load_models():
    models = {}
    for model_file in MODELS_DIR.glob("*_model.joblib"):
        sensor_type = model_file.stem.replace("_model", "")
        models[sensor_type] = joblib.load(model_file)
    return models


def on_message(client, userdata, message):
    models, history = userdata
    try:
        payload = json.loads(message.payload.decode())
    except json.JSONDecodeError:
        return

    device_id = payload.get("device_id")
    sensor_type = payload.get("sensor_type")
    value = payload.get("value")

    if sensor_type not in models or value is None:
        return

    feature_vector = history.add_and_extract(device_id, value)
    prediction = models[sensor_type].predict([feature_vector])[0]

    if prediction == -1:
        print(
            f"[ANOMALIJA] {device_id} ({sensor_type}): vrednost={value}, "
            f"devijacija={feature_vector[1]:.2f}"
        )
        client.publish(
            ALERT_TOPIC_TEMPLATE.format(device_id=device_id, sensor_type=sensor_type),
            json.dumps({"device_id": device_id, "sensor_type": sensor_type, "value": value}),
        )
    else:
        print(f"[OK] {device_id} ({sensor_type}): vrednost={value}")


def run(broker_host="localhost", broker_port=1883):
    models = load_models()
    if not models:
        raise RuntimeError("Nema sacuvanih modela. Pokreni prvo: python -m anomaly.train_model")

    history = RollingHistory()
    client = mqtt.Client(client_id="anomaly-monitor", userdata=(models, history))
    client.on_message = on_message
    client.connect(broker_host, broker_port)
    client.subscribe("home/+/+")

    print("Anomaly monitor pokrenut, slusam home/+/+ ...")
    client.loop_forever()


if __name__ == "__main__":
    run()
