import random

SENSOR_RANGES = {
    "temperature": (18.0, 26.0),
    "humidity": (30.0, 60.0),
    "motion": (0, 1),
}

WALK_STEP = 0.4


def initial_value(sensor_type):
    if sensor_type == "motion":
        return random.choice([0, 1])
    low, high = SENSOR_RANGES[sensor_type]
    return (low + high) / 2


def next_value(sensor_type, previous_value):
    if sensor_type == "motion":
        return random.choice([0, 1])

    low, high = SENSOR_RANGES[sensor_type]
    step = random.uniform(-WALK_STEP, WALK_STEP)
    return round(min(max(previous_value + step, low), high), 2)
