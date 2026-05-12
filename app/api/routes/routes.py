"""
app/api/routes/auth.py
-----------------------
POST /auth/register  — create account
POST /auth/login     — get JWT token
GET  /auth/me        — get current user info
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.database import get_db, User
from app.services.auth_service import (
    hash_password, verify_password,
    create_token, decode_token, new_user_id
)

router  = APIRouter(prefix="/auth", tags=["Auth"])
bearer  = HTTPBearer()


# ── Schemas ───────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email:    EmailStr
    password: str = Field(..., min_length=6)
    name:     str = Field(..., min_length=1, max_length=80)


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: str
    email: str
    name: str


class MeResponse(BaseModel):
    user_id: str
    email: str
    name: str


# ── Helper ────────────────────────────────────────────────────────────────────

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    try:
        return decode_token(creds.credentials)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        id        = new_user_id(),
        email     = req.email,
        name      = req.name,
        hashed_pw = hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id, user.email, user.name)
    return AuthResponse(token=token, user_id=user.id,
                        email=user.email, name=user.name)


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_pw):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user.last_login = datetime.utcnow()
    db.commit()

    token = create_token(user.id, user.email, user.name)
    return AuthResponse(token=token, user_id=user.id,
                        email=user.email, name=user.name)


@router.get("/me", response_model=MeResponse)
def me(current: dict = Depends(get_current_user)):
    return MeResponse(
        user_id = current["sub"],
        email   = current["email"],
        name    = current["name"],
    )
