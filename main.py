import os
import hashlib
import secrets
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from bson.objectid import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="Trust Cars 4U API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory token store for demo. In production, use JWT or a token store.
sessions: dict[str, str] = {}


def hash_password(password: str, salt_hex: Optional[str] = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.sha256(salt + password.encode()).hexdigest()
    return digest, salt.hex()


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


class AppointmentRequest(BaseModel):
    name: str
    phone: str
    car_model: str
    datetime_iso: str
    purpose: str


def get_user_by_email(email: str) -> Optional[dict]:
    user = db["userauth"].find_one({"email": email}) if db else None
    return user


@app.get("/")
def root():
    return {"message": "Trust Cars 4U Backend Running"}


@app.post("/api/signup", response_model=AuthResponse)
def signup(payload: SignupRequest):
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")

    existing = get_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    pwd_hash, salt = hash_password(payload.password)
    user_doc = {
        "name": payload.name,
        "email": str(payload.email),
        "password_hash": pwd_hash,
        "salt": salt,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    inserted_id = db["userauth"].insert_one(user_doc).inserted_id

    token = secrets.token_hex(24)
    sessions[token] = str(inserted_id)
    return {"token": token, "user": {"id": str(inserted_id), "name": payload.name, "email": payload.email}}


@app.post("/api/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")

    user = get_user_by_email(payload.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    pwd_hash, _ = hash_password(payload.password, user.get("salt"))
    if pwd_hash != user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = secrets.token_hex(24)
    sessions[token] = str(user["_id"])
    return {"token": token, "user": {"id": str(user["_id"]), "name": user.get("name"), "email": user.get("email")}}


def require_auth(token: Optional[str]) -> str:
    if not token or token not in sessions:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return sessions[token]


@app.post("/api/appointments")
def create_appointment(payload: AppointmentRequest, token: Optional[str] = None):
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")

    user_id = require_auth(token)

    doc = {
        "user_id": user_id,
        "name": payload.name,
        "phone": payload.phone,
        "car_model": payload.car_model,
        "datetime_iso": payload.datetime_iso,
        "purpose": payload.purpose,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    inserted_id = db["appointment"].insert_one(doc).inserted_id
    return {"id": str(inserted_id), "message": "Appointment booked successfully"}


@app.get("/api/appointments")
def list_my_appointments(token: Optional[str] = None):
    if not db:
        raise HTTPException(status_code=500, detail="Database not configured")

    user_id = require_auth(token)
    appts = list(db["appointment"].find({"user_id": user_id}).sort("datetime_iso", 1))

    for a in appts:
        a["id"] = str(a.pop("_id"))
    return appts


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db as testdb
        if testdb is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = testdb.name if hasattr(testdb, 'name') else "✅ Connected"
            try:
                collections = testdb.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
