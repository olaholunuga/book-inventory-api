"""
Authentication blueprint:
- POST /auth/register
- POST /auth/login
- POST /auth/refresh
- POST /auth/logout
- GET  /auth/me
- POST /auth/users/<user_id>/roles (admin only) -> to assign roles

The implementation:
- Uses argon2 for password hashing (via utils.security)
- Issues short-lived access tokens and longer-lived refresh tokens (JWTs signed with HS256)
- Stores refresh tokens in DB (RefreshToken model) so we can revoke / rotate them
- Implement JWT validation without using flask-jwt-extended
"""
from __future__ import annotations

from datetime import datetime
import uuid
from flask import Blueprint, request, jsonify, g, abort, current_app
from marshmallow import ValidationError
from typing import Tuple


from models import storage
from models.user import User
from models.refresh_token import RefreshToken
from models.schemas.user import UserCreateSchema, UserOutSchema, UserLoginSchema, UserListOutSchema

from utils.decorators import jwt_required, roles_required
from utils.security import (
    hash_password,
    verify_password,
    create_jwt_token,
    decode_token,
    generate_jti
)

MAX_LIMIT = 100

bp = Blueprint("auth", __name__, url_prefix="/auth")

user_create_schema = UserCreateSchema()
user_out_schema = UserOutSchema()
user_login_schema = UserLoginSchema()
user_list_out_schema = UserListOutSchema(many=True)



@bp.post("/register")
def register():
    """
    register a new user.
    ---
    tags:
      - Auth
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            email: { type: string }
            password: { type: string }
            f_name: { type: string }
            l_name: { type: string }
    responses:
      201:
        description: Created
      422:
        description: Validation error
    """
    payload = request.get_json(silent=True) or {}
    data = user_create_schema.load(payload)

    session = storage.get_session()
    if session.query(User).filter(User.email == data.get("email")).first():
        abort(409, description="Email already registered")
    
    pw_hash = hash_password(data["password"])
    user = User(
        email=data["email"],
        password_hash=pw_hash,
        f_name=data["f_name"],
        l_name=data["l_name"]
    )

    storage.new(user)
    storage.save()

    return jsonify(
        {
            "data": user_out_schema.dump(user)
        }
    ), 201

@bp.post("/login")
def login():
    """
    Login: return access_token and refresh_token
    ---
    tags:
      - Auth
    consumes:
      - application/json
    parameters:
      -  in: body
         name: body
         schema:
           type: object
           properties:
             email: { type: string }
             password: { type: string }
    responses:
      200:
        description: OK (returns tokens)
      401:
        description: Unauthorized
    """
    payload = request.get_json(silent=True) or {}
    payload = user_login_schema.load(payload)
    email = payload.get("email")
    password = payload.get("password")
    if not email or not password:
        abort(422, description="email and password are required")
    
    session = storage.get_session()
    user: User = session.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        abort(401, description="Invalid credential")
    
    token_jti = generate_jti()
    jwt_token = create_jwt_token(subject=str(user.id), jti=token_jti)

    # rft = RefreshToken(
    #     jti=refresh_jti,
    #     user_id=str(user.id),
    #     revoked=False,
    #     expires_at=datetime.utcnow() + current_app.config["REFRESH_TOKEN_EXPIRES"]
    # )

    # storage.new(rft)
    # storage.save()

    return jsonify(
        {
            "access_token": jwt_token,
            "token_type": "bearer",
            "expires_in": int(current_app.config["JWT_TOKEN_EXPIRES"].total_seconds())
        }
    ), 200

@bp.post("/refresh")
def refresh():
    """
    Use refreah token to obtain new access and refresh tokens (rotaion)
    Body: { "refresh_token": "<token>" }
    """
    payload = request.get_json(silent=True) or {}
    token = payload.get("refresh_token")
    if not token:
        abort(422, description="refresh_token is required")
    
    try:
        decoded = decode_token(token, expected_type="refresh")
    except Exception as e:
        abort(401, description=str(e))
    
    session = storage.get_session()

    jti = decoded.get(jti)
    rt = session.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if not rt or rt.revoked:
        abort(401, description="Invalid or revoked refresh token")
    
    rt.revoked = True
    storage.new(rt)

    new_token_jti = generate_jti()
    new_jwt = create_jwt_token(sub=decoded["sub"], jti=new_token_jti)
    
    # new_rt = RefreshToken(
    #     jti=new_re_jti,
    #     user_id=decoded["sub"],
    #     revoked=False,
    #     expires_at=datetime.utcnow() + current_app.config["REFRESH_TOKEN_EXPIRES"]
    # )
    # storage.new(new_rt)
    # storage.save()

    return jsonify(
        {
            "jwt_token": new_jwt,
            "token_type": "bearer",
            "expires_in": int(current_app.config["JWT_TOKEN_REFRESH"].total_seconds()),
        }
    ), 200

@bp.post("/logout")
@jwt_required()
def logout():
    """
    logout: revokes jwt_token
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    consumes:
      - application/json
    parameters:
      -  in: body
         name: body
         schema:
           type: object
           properties:
             jwt_token: { type: string }
    responses:
      204:
        description: ""
      401:
        description: Unauthorized
    """
    payload = request.get_json(silent=True) or {}
    refresh_token =payload.get("jwt_token")

    session = storage.get_session()

    if refresh_token:
        try:
            decoded = decode_token(refresh_token, expected_type="refresh")
        except Exception:
            return ("", 204)
        jti = decoded.get("jti")
        rt = session.query(RefreshToken).filter(RefreshToken.jti == jti).first()
        if rt:
            rt.revoked = True
            storage.new(rt)
            storage.save()
      
        return ("", 204)