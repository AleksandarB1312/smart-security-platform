import random
from pathlib import Path

import joblib
from sklearn.ensemble import IsolationForest

from anomaly.features import RollingHistory
from devices.sensors import initial_value, next_value

MODELS_DIR = Path(__file__).parent / "models"
RANDOM_SEED = 42


def simulate_normal_readings(sensor_type, num_devices=10, readings_per_device=200, seed=RANDOM_SEED):
    random.seed(seed)
    features = []

    for device_index in range(num_devices):
        history = RollingHistory()
        device_id = f"train-device-{device_index}"
        value = initial_value(sensor_type)

        for _ in range(readings_per_device):
            value = next_value(sensor_type, value)
            feature_vector = history.add_and_extract(device_id, value)
            features.append(feature_vector)

    return features


def train_model(sensor_type):
    features = simulate_normal_readings(sensor_type)
    model = IsolationForest(contamination=0.02, random_state=42)
    model.fit(features)
    return model


def train_and_save(sensor_type):
    model = train_model(sensor_type)

    MODELS_DIR.mkdir(exist_ok=True)
    model_path = MODELS_DIR / f"{sensor_type}_model.joblib"
    joblib.dump(model, model_path)
    print(f"Model za '{sensor_type}' sacuvan u {model_path}")
    return model


TRAINABLE_SENSOR_TYPES = ["temperature", "humidity"]


if __name__ == "__main__":
    for sensor_type in TRAINABLE_SENSOR_TYPES:
        train_and_save(sensor_type)
