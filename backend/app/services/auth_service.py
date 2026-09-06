import base64
import hashlib
import hmac
import json
import secrets
import time

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import AUTH_SECRET, AUTH_TOKEN_HOURS
from app.core.database import get_db
from app.models.models import User


ROLES = {'viewer', 'engineer', 'admin'}
bearer = HTTPBearer(auto_error=False)


def encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip('=')


def decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 310_000)
    return 'pbkdf2_sha256$310000$' + encode(salt) + '$' + encode(digest)


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt, expected = stored.split('$', 3)
        if algorithm != 'pbkdf2_sha256':
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), decode(salt), int(rounds))
        return hmac.compare_digest(actual, decode(expected))
    except (ValueError, TypeError):
        return False


def create_token(user: User) -> str:
    payload = encode(json.dumps({
        'sub': user.username,
        'role': user.role,
        'exp': int(time.time()) + AUTH_TOKEN_HOURS * 3600,
    }, separators=(',', ':')).encode())
    signature = encode(hmac.new(AUTH_SECRET.encode(), payload.encode(), hashlib.sha256).digest())
    return f'{payload}.{signature}'


def token_payload(token: str):
    try:
        payload, signature = token.split('.', 1)
        expected = encode(hmac.new(AUTH_SECRET.encode(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError
        result = json.loads(decode(payload))
        if int(result['exp']) < int(time.time()):
            raise ValueError
        return result
    except (ValueError, KeyError, json.JSONDecodeError):
        raise HTTPException(401, 'Invalid or expired session', headers={'WWW-Authenticate': 'Bearer'})


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    if not credentials:
        raise HTTPException(401, 'Authentication required', headers={'WWW-Authenticate': 'Bearer'})
    payload = token_payload(credentials.credentials)
    user = db.query(User).filter(User.username == payload['sub'], User.is_active.is_(True)).first()
    if not user or user.role != payload['role']:
        raise HTTPException(401, 'Account is unavailable')
    return user


def require_roles(*allowed):
    def dependency(user: User = Depends(get_current_user)):
        if user.role not in allowed:
            raise HTTPException(403, f"This action requires: {', '.join(allowed)}")
        return user
    return dependency
