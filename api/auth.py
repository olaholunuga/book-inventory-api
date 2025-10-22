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

from models import storage
from models.user import User
from models.refresh_token import RefreshToken
from models.schemas.user import UserCreateSchema, UserOutSchema

from 