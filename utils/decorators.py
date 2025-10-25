from __future__ import annotations
from functools import wraps
from flask import request, g, abort
from utils.security import decode_token
from models import storage
from models.user import User


def jwt_required():
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer "):
                abort(401, description="Missing or invalid Authorization header")
            token = auth.split(" ", 1)[1].strip()
            try:
                decoded = decode_token(token, expected_type="refresh")
            except Exception as e:
                abort(401, description=str(e))

            user_id = decoded.get("sub")
            session = storage.get_session()
            user = session.query(User).get(user_id)
            if not user:
                abort(401, description="User not found")
            # optionally attach token jti and roles from token
            g.current_user = user
            g.current_user_roles = decoded.get("roles", getattr(user, "roles", []))
            g.current_token_jti = decoded.get("jti")
            return fn(*args, **kwargs)

        return wrapper

    return decorator

def roles_required(required_roles: list[str]):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user_roles = set(getattr(g, "current_user_roles", []))

            # required_roles = set(required_roles or [])
            if not set(required_roles).issubset(user_roles):
                abort(403, description="Insuficient role")
            return fn(*args, **kwargs)
        
        return wrapper
    
    return decorator