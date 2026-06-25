import secrets
import time

import jwt
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from crypto.schnorr import verify_proof
from gateway.database import (
    count_recent_failures,
    get_device_public_key,
    init_db,
    list_devices,
    list_recent_failures,
    log_failed_attempt,
    register_device,
)

SECRET_KEY = "dev-secret-change-in-production"
TOKEN_TTL_SECONDS = 300
SESSION_TTL_SECONDS = 30
BRUTE_FORCE_THRESHOLD = 3
BRUTE_FORCE_WINDOW_SECONDS = 60

app = FastAPI(title="Smart Home Security Platform - Auth Gateway")
pending_sessions = {}

init_db()


class RegisterRequest(BaseModel):
    device_id: str
    public_key: int


class CommitmentRequest(BaseModel):
    device_id: str
    commitment: int


class ResponseRequest(BaseModel):
    device_id: str
    response: int


@app.post("/devices/register")
def register(payload: RegisterRequest):
    register_device(payload.device_id, payload.public_key)
    return {"status": "registered", "device_id": payload.device_id}


@app.get("/devices")
def devices():
    return list_devices()


@app.post("/auth/commitment")
def submit_commitment(payload: CommitmentRequest):
    public_key = get_device_public_key(payload.device_id)
    if public_key is None:
        raise HTTPException(status_code=404, detail="Uređaj nije registrovan")

    challenge = secrets.randbits(256)
    pending_sessions[payload.device_id] = {
        "commitment": payload.commitment,
        "challenge": challenge,
        "public_key": public_key,
        "created_at": time.time(),
    }
    return {"challenge": challenge}


@app.post("/auth/response")
def submit_response(payload: ResponseRequest, request: Request):
    session = pending_sessions.pop(payload.device_id, None)
    if session is None:
        raise HTTPException(status_code=400, detail="Nema aktivne auth sesije za ovaj uređaj")

    if time.time() - session["created_at"] > SESSION_TTL_SECONDS:
        raise HTTPException(status_code=408, detail="Auth sesija je istekla, pokušaj ponovo")

    is_valid = verify_proof(
        commitment=session["commitment"],
        challenge=session["challenge"],
        response=payload.response,
        public_key=session["public_key"],
    )

    if not is_valid:
        client_ip = request.client.host if request.client else "unknown"
        log_failed_attempt(payload.device_id, client_ip)

        recent_failures = count_recent_failures(payload.device_id, BRUTE_FORCE_WINDOW_SECONDS)
        if recent_failures >= BRUTE_FORCE_THRESHOLD:
            print(
                f"[UPOZORENJE] {payload.device_id} ima {recent_failures} neuspelih "
                f"pokusaja u poslednjih {BRUTE_FORCE_WINDOW_SECONDS}s — moguc napad"
            )

        raise HTTPException(status_code=401, detail="ZKP dokaz nije validan")

    token = jwt.encode(
        {"sub": payload.device_id, "exp": time.time() + TOKEN_TTL_SECONDS},
        SECRET_KEY,
        algorithm="HS256",
    )
    return {"token": token}


@app.get("/security/failed-attempts")
def failed_attempts():
    return list_recent_failures()
