"""
security helpers:
- Argon2 password hashing via argon2-cffi
- JWT creation/verification via PyJWT
- JTI generation for token identifiers
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from flask import current_app

ph = PasswordHasher()

def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2
    """
    return ph.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    """ Verify a plaintext password using argon2
    """
    try:
        return ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False

def generate_jti() -> str:
    """Generate a unique JTI (JWT ID).
    """
    return str(uuid.uuid4())

def _now() -> datetime:
    return datetime.utcnow()

def create_access_token(subject: str, jti: str = None) -> str:
    """

    """
    jti = jti or generate_jti()
    exp = _now() + current_app.config["ACESS_TOKEN_EXPIRES"]
    payload = {
        "iss": current_app.config.get("JWT_ISSUER", "book-inventory-api"),
        "sub": str(subject),
        "iat": int(_now().timestamp()),
        "exp": int(exp.timestamp()),
        "type": "access",
        "jti": jti,
        "roles": current_app.config.get("DEFAULT_ROLES_CLAIMS", []),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm=current_app.config["JWT_ALGORITHM"])

def decode_token(token: str, expected_type: str = "access") -> Dict[str, Any]:
    """
    Decode and validate a JWT. Raises exception on invalid signature/expired jwt
    expected type must bt "access" or "refresh".
    """
    try:
        decoded = jwt.decode(
            token, current_app.config["JWT_SECRET"], algorithms=[current_app.config["JWT_ALGORITHM"]]
        )
    except jwt.ExpiredSignatureError:
        raise Exception("Token expired")
    except jwt.InvalidTokenError as exc:
        raise Exception(f"Invalid token: {exc}")
    
    if decoded.get("type") != expected_type:
        raise Exception("Wrong token type")
    return decoded