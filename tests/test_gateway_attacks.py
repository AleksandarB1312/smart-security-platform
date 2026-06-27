import os
import tempfile

os.environ["GATEWAY_DB_PATH"] = tempfile.mktemp(suffix=".db")

from fastapi.testclient import TestClient

from crypto.schnorr import create_commitment, create_response, generate_keypair
from gateway.main import app

client = TestClient(app)


def register_test_device(device_id):
    private_key, public_key = generate_keypair()
    client.post("/devices/register", json={"device_id": device_id, "public_key": public_key})
    return private_key, public_key


def perform_full_auth(device_id, private_key):
    nonce, commitment = create_commitment()
    commitment_response = client.post(
        "/auth/commitment", json={"device_id": device_id, "commitment": commitment}
    )
    challenge = commitment_response.json()["challenge"]
    response_value = create_response(nonce, challenge, private_key)
    return client.post(
        "/auth/response", json={"device_id": device_id, "response": response_value}
    )


def test_legitimate_device_authenticates_successfully():
    private_key, _ = register_test_device("test-device-legit")
    response = perform_full_auth("test-device-legit", private_key)

    assert response.status_code == 200
    assert "token" in response.json()


def test_spoofing_attack_is_rejected():
    register_test_device("test-device-spoofed")
    attacker_private_key, _ = generate_keypair()

    response = perform_full_auth("test-device-spoofed", attacker_private_key)

    assert response.status_code == 401


def test_replay_attack_is_rejected():
    private_key, _ = register_test_device("test-device-replay")

    nonce, commitment = create_commitment()
    first_commitment_response = client.post(
        "/auth/commitment", json={"device_id": "test-device-replay", "commitment": commitment}
    )
    challenge_one = first_commitment_response.json()["challenge"]
    response_one = create_response(nonce, challenge_one, private_key)

    legitimate_response = client.post(
        "/auth/response", json={"device_id": "test-device-replay", "response": response_one}
    )
    assert legitimate_response.status_code == 200

    second_commitment_response = client.post(
        "/auth/commitment", json={"device_id": "test-device-replay", "commitment": commitment}
    )
    challenge_two = second_commitment_response.json()["challenge"]
    assert challenge_two != challenge_one

    replayed_response = client.post(
        "/auth/response", json={"device_id": "test-device-replay", "response": response_one}
    )

    assert replayed_response.status_code == 401


def test_brute_force_is_logged():
    register_test_device("test-device-bruteforce")

    for _ in range(4):
        attacker_private_key, _ = generate_keypair()
        perform_full_auth("test-device-bruteforce", attacker_private_key)

    failures = client.get("/security/failed-attempts").json()
    matching_failures = [f for f in failures if f["device_id"] == "test-device-bruteforce"]

    assert len(matching_failures) >= 4


def test_unregistered_device_cannot_start_auth():
    response = client.post(
        "/auth/commitment", json={"device_id": "ghost-device-never-registered", "commitment": 12345}
    )
    assert response.status_code == 404
