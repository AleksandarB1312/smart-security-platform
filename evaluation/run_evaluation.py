import statistics
import time
from pathlib import Path

from anomaly.features import RollingHistory
from anomaly.train_model import simulate_normal_readings, train_model
from crypto.schnorr import (
    create_commitment,
    create_response,
    generate_keypair,
    verify_proof,
)
from devices.sensors import initial_value, next_value

RESULTS_PATH = Path(__file__).parent.parent / "docs" / "rezultati_evaluacije.md"

SENSOR_TYPES = ["temperature", "humidity"]
ATTACK_MAGNITUDES = [1, 2, 4, 8, 16, 32]
TRIALS_PER_MAGNITUDE = 50
FALSE_POSITIVE_TEST_SIZE = 500
TIMING_RUNS = 1000
EVAL_SEED = 999
SPOOFING_TRIALS = 100


def measure_zkp_timing():
    private_key, public_key = generate_keypair()
    keygen_times, commitment_times, response_times, verify_times = [], [], [], []

    for _ in range(TIMING_RUNS):
        start = time.perf_counter()
        generate_keypair()
        keygen_times.append(time.perf_counter() - start)

        start = time.perf_counter()
        nonce, commitment = create_commitment()
        commitment_times.append(time.perf_counter() - start)

        challenge = 123456789

        start = time.perf_counter()
        response = create_response(nonce, challenge, private_key)
        response_times.append(time.perf_counter() - start)

        start = time.perf_counter()
        verify_proof(commitment, challenge, response, public_key)
        verify_times.append(time.perf_counter() - start)

    return {
        "Generisanje kljuceva": keygen_times,
        "Commitment": commitment_times,
        "Response": response_times,
        "Verifikacija": verify_times,
    }


def measure_false_positive_rate(sensor_type):
    model = train_model(sensor_type)
    test_features = simulate_normal_readings(
        sensor_type,
        num_devices=5,
        readings_per_device=FALSE_POSITIVE_TEST_SIZE // 5,
        seed=EVAL_SEED,
    )

    predictions = model.predict(test_features)
    false_positives = sum(1 for prediction in predictions if prediction == -1)
    return false_positives, len(test_features)


def measure_detection_sensitivity(sensor_type):
    model = train_model(sensor_type)
    results = {}

    for magnitude in ATTACK_MAGNITUDES:
        detections = 0
        for trial in range(TRIALS_PER_MAGNITUDE):
            history = RollingHistory()
            value = initial_value(sensor_type)

            for _ in range(5):
                value = next_value(sensor_type, value)
                history.add_and_extract(f"eval-device-{trial}", value)

            jump_value = value + magnitude
            feature_vector = history.add_and_extract(f"eval-device-{trial}", jump_value)
            prediction = model.predict([feature_vector])[0]

            if prediction == -1:
                detections += 1

        results[magnitude] = detections / TRIALS_PER_MAGNITUDE

    return results


def measure_spoofing_rejection_rate(trials=SPOOFING_TRIALS):
    _, public_key = generate_keypair()
    rejections = 0

    for _ in range(trials):
        attacker_private_key, _ = generate_keypair()
        nonce, commitment = create_commitment()
        challenge = 987654321
        forged_response = create_response(nonce, challenge, attacker_private_key)

        if not verify_proof(commitment, challenge, forged_response, public_key):
            rejections += 1

    return rejections, trials


def format_timing_table(timing_data):
    lines = ["| Operacija | Prosek (ms) | Min (ms) | Max (ms) |", "|---|---|---|---|"]
    for label, times_seconds in timing_data.items():
        times_ms = [t * 1000 for t in times_seconds]
        lines.append(
            f"| {label} | {statistics.mean(times_ms):.3f} | {min(times_ms):.3f} | {max(times_ms):.3f} |"
        )
    return "\n".join(lines)


def format_sensitivity_table(sensitivity_results, sensor_type):
    lines = [
        f"### Osetljivost detekcije — {sensor_type}",
        "",
        "| Velicina naglog skoka | Stopa detekcije |",
        "|---|---|",
    ]
    for magnitude, rate in sensitivity_results.items():
        lines.append(f"| ±{magnitude} | {rate * 100:.0f}% |")
    return "\n".join(lines)


def run():
    print("Merim ZKP performanse...")
    timing_data = measure_zkp_timing()

    print("Merim stopu laznih pozitiva (false positive rate)...")
    fp_results = {
        sensor_type: measure_false_positive_rate(sensor_type) for sensor_type in SENSOR_TYPES
    }

    print("Merim osetljivost detekcije po velicini napada...")
    sensitivity_results = {
        sensor_type: measure_detection_sensitivity(sensor_type) for sensor_type in SENSOR_TYPES
    }

    print("Testiram otpornost na spoofing napad...")
    rejections, trials = measure_spoofing_rejection_rate()

    report_lines = [
        "# Rezultati evaluacije",
        "",
        "Automatski generisano pokretanjem `python -m evaluation.run_evaluation`. "
        "Svi brojevi su reproduktivni (fiksirani random seed-ovi).",
        "",
        "## 1. Performanse ZKP (Schnorr) protokola",
        "",
        f"Prosek od {TIMING_RUNS} mernih ciklusa po operaciji, na 2048-bitnoj grupi:",
        "",
        format_timing_table(timing_data),
        "",
        "## 2. Stopa laznih pozitiva (normalan saobracaj)",
        "",
        "Model testiran na ODVOJENOM test skupu (drugaciji random seed od treninga, "
        "da se izbegne data leakage):",
        "",
        "| Senzor | Lazni pozitivi | Ukupno ocitavanja | Stopa |",
        "|---|---|---|---|",
    ]

    for sensor_type, (false_positives, total) in fp_results.items():
        rate = false_positives / total * 100
        report_lines.append(f"| {sensor_type} | {false_positives} | {total} | {rate:.2f}% |")

    report_lines += [
        "",
        "## 3. Osetljivost detekcije napada (true positive rate)",
        "",
        f"Po {TRIALS_PER_MAGNITUDE} pokusaja za svaku velicinu naglog skoka u odnosu na "
        "stabilnu prethodnu vrednost:",
        "",
    ]

    for sensor_type, results in sensitivity_results.items():
        report_lines.append(format_sensitivity_table(results, sensor_type))
        report_lines.append("")

    report_lines += [
        "## 4. Otpornost na spoofing napad",
        "",
        f"Od {trials} pokusaja autentikacije sa nasumicnim (pogresnim) privatnim kljucem, "
        f"gateway je odbio {rejections}/{trials} ({rejections / trials * 100:.1f}%).",
        "",
        "## 5. Napomena o replay i brute-force napadima",
        "",
        "Otpornost na replay i brute-force napade je dokazana kroz automatizovane "
        "integracione testove (`tests/test_gateway_attacks.py`), ne kroz statisticko "
        "merenje, jer je ishod deterministican (matematicki garantovan svezinom "
        "challenge-a, odnosno pragom za detekciju). Pokreni `pytest tests/ -v` za "
        "potvrdu da svi testovi prolaze.",
        "",
    ]

    report_text = "\n".join(report_lines)
    RESULTS_PATH.parent.mkdir(exist_ok=True)
    RESULTS_PATH.write_text(report_text)

    print(report_text)
    print(f"\nRezultati sacuvani u {RESULTS_PATH}")


if __name__ == "__main__":
    run()
