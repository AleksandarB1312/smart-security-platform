import secrets
import time

import jwt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from crypto.schnorr import verify_proof
from gateway.database import get_device_public_key, init_db, list_devices, register_device

SECRET_KEY = "dev-secret-change-in-production"
TOKEN_TTL_SECONDS = 300
SESSION_TTL_SECONDS = 30

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
def submit_response(payload: ResponseRequest):
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
        raise HTTPException(status_code=401, detail="ZKP dokaz nije validan")

    token = jwt.encode(
        {"sub": payload.device_id, "exp": time.time() + TOKEN_TTL_SECONDS},
        SECRET_KEY,
        algorithm="HS256",
    )
    return {"token": token}
