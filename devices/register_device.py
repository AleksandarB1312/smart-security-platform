import argparse
import json
from pathlib import Path

from crypto.schnorr import generate_keypair
from devices.zkp_auth_client import register_device

KEYS_DIR = Path(__file__).parent / "keys"


def save_keys(device_id, private_key, public_key):
    KEYS_DIR.mkdir(exist_ok=True)
    key_file = KEYS_DIR / f"{device_id}.json"
    with open(key_file, "w") as file:
        json.dump({"private_key": private_key, "public_key": public_key}, file)
    return key_file


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--device-id", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    private_key, public_key = generate_keypair()
    key_file = save_keys(args.device_id, private_key, public_key)
    register_device(args.device_id, public_key)
    print(f"[{args.device_id}] registrovan na gateway-u")
    print(f"[{args.device_id}] privatni kljuc sacuvan lokalno u {key_file}")
