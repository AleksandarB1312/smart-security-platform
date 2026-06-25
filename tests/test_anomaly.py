from anomaly.features import RollingHistory
from anomaly.train_model import simulate_normal_readings, train_and_save


def test_normal_sequence_is_not_flagged():
    model = train_and_save("temperature")
    history = RollingHistory()

    value = 22.0
    flagged_as_anomaly = []
    for step in [-0.2, 0.1, -0.1, 0.2, -0.2, 0.1]:
        value += step
        feature_vector = history.add_and_extract("test-device", value)
        prediction = model.predict([feature_vector])[0]
        flagged_as_anomaly.append(prediction == -1)

    assert not any(flagged_as_anomaly)


def test_sudden_jump_is_flagged_as_anomaly():
    model = train_and_save("temperature")
    history = RollingHistory()

    for value in [22.0, 22.1, 21.9, 22.0]:
        feature_vector = history.add_and_extract("test-device", value)
        model.predict([feature_vector])

    jump_feature_vector = history.add_and_extract("test-device", 26.0)
    prediction = model.predict([jump_feature_vector])[0]

    assert prediction == -1


def test_training_features_have_small_deviation():
    features = simulate_normal_readings("temperature", num_devices=3, readings_per_device=50)
    deviations = [feature_vector[1] for feature_vector in features]

    assert max(deviations) < 2.0
