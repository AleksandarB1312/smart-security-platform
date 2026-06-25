import requests

from crypto.schnorr import create_commitment, create_response

GATEWAY_URL = "http://localhost:8000"


def register_device(device_id, public_key):
    response = requests.post(
        f"{GATEWAY_URL}/devices/register",
        json={"device_id": device_id, "public_key": public_key},
        timeout=5,
    )
    response.raise_for_status()
    return response.json()


def authenticate(device_id, private_key):
    nonce, commitment = create_commitment()

    commitment_response = requests.post(
        f"{GATEWAY_URL}/auth/commitment",
        json={"device_id": device_id, "commitment": commitment},
        timeout=5,
    )
    commitment_response.raise_for_status()
    challenge = commitment_response.json()["challenge"]

    response_value = create_response(nonce, challenge, private_key)

    response_response = requests.post(
        f"{GATEWAY_URL}/auth/response",
        json={"device_id": device_id, "response": response_value},
        timeout=5,
    )
    response_response.raise_for_status()
    return response_response.json()["token"]
