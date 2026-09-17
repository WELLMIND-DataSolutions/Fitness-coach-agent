"""
auth.py — Password hashing + JWT token banane/verify karne ka logic.
UPDATED: passlib hata diya (naye bcrypt versions ke sath crash karta tha),
ab seedha 'bcrypt' library use ho rahi hai — zyada simple aur reliable.
"""

import os
import bcrypt
from datetime import datetime, timedelta, timezone
import jwt

# Production mein ye secret .env se aana chahiye, hardcode mat karo.
SECRET_KEY = os.environ.get("JWT_SECRET", "change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # token 7 din valid rahega


def hash_password(password: str) -> str:
    """Plain password ko bcrypt se hash karta hai — DB mein kabhi plain text save nahi karte."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Login ke waqt user ka diya password DB ke hash se match karta hai."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: int, username: str) -> str:
    """Login/register successful hone par ek JWT token banata hai jo user_id apne andar carry karta hai."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    """Token verify karta hai aur agar valid ho to user_id return karta hai, warna None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except jwt.PyJWTError:
        return None
