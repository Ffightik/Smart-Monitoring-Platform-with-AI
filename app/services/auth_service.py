"""
app/services/auth_service.py
-----------------------------
Password hashing, JWT creation/verification.
"""
import uuid
import bcrypt
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from app.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM  = "HS256"
TOKEN_TTL  = 60 * 24 * 7   # 7 days in minutes


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(user_id: str, email: str, name: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_TTL)
    payload = {
        "sub":   user_id,
        "email": email,
        "name":  name,
        "exp":   expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def new_user_id() -> str:
    return str(uuid.uuid4())
