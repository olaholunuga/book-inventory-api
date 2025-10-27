from __future__ import annotations

from datetime import datetime
from pydoc import describe
import uuid
from flask import Blueprint, request, jsonify, g, abort, current_app
from marshmallow import ValidationError
from typing import Tuple
from sqlalchemy.orm.attributes import flag_modified

from models import storage
from models.author import Author
from models.user import User
from models.schemas.user import UserCreateSchema, UserOutSchema
from utils.decorators import jwt_required, roles_required

MAX_LIMIT = 100

bp = Blueprint("users", __name__)


user_create_schema = UserCreateSchema()
user_out_schema = UserOutSchema()
user_list_out_schema = UserOutSchema(many=True)

def parse_pagination() -> Tuple[int, int]:
    try:
        page = int(request.args.get("page", "1"))
        limit = int(request.args.get("limit", "20"))
        page = max(page, 1)
        limit = max(1, min(limit, MAX_LIMIT))
        return page, limit
    except ValueError:
        abort(400, description="page and limit must be integers")

def parse_sort(default="name"):
    sort = request.args.get("sort", default)
    desc = sort.startswith("-")
    key = sort[1:] if desc else sort
    if key != "name":
        abort(400, description="Unsupported sort field. Allowed: name")
    return (User.f_name.desc() if desc else User.f_name.asc(),)

@bp.get("/users")
def list_user():
    """
    List all Users
    ---
    tags:
      - Users
    responses:
      200: { description: OK }
    """
    session = storage.get_session()
    page, limit = parse_pagination()
    order_by = parse_sort()

    query = session.query(User)

    total = query.count()
    rows = query.order_by(*order_by).offset((page - 1) * limit).limit(limit).all()
    return jsonify(
        {
            "data": user_list_out_schema.dump(rows),
            "meta": {"page": page, "limit": limit, "total": total}
        }
    )

@bp.get("/me")
@jwt_required()
def me():
    """
    Get current user info. - user
    ---
    tags:
      - Users
    security:
      - Bearer: []
    responses:
      200:
        description: OK
      401:
        description: Unauthorized
    """
    user = g.current_user
    return jsonify(
        {
            "data": user_create_schema.dump(user)
        }
    ), 200

@bp.post("/users/<user_id>/roles")
@roles_required(["admin"])
def set_roles(user_id: str):
    """
    Admin-only: set roles for a user (roles array).
    Body: { "roles": ["admin", "author", "user"] }
    ---
    tags:
      - Users
    security:
      - Bearer: []
    consumes:
      - application/json
    parameters:
      -  in: path
         name: user_id
         type: string
         required: true
      -  in: body
         name: body
         schema:
           type: object
           properties:
             roles: { type: string }
    responses:
      200: { descrpition: OK }
    """
    payload = request.get_json(silent=True) or {}
    roles = payload.get("roles")
    if not isinstance(roles, list) or not roles:
        abort(422, description="roles must be a non-empty list")
    
    session = storage.get_session()
    user = session.query(User).get(user_id)
    if not user:
        abort(404)
    if "author" in roles and not user.author:
        abort(400, description="user must be linked to a author")
    
    allowed = set(current_app.config.get("ALLOWED_ROLES", ["admin", "author", "user"]))
    if any(r not in allowed for r in roles):
        abort(422, description=f"Roles must be subset {allowed}")
    if user.roles:
        user.roles.extend(roles)
    else:
        user.roles = roles
    flag_modified(user, "roles")
    storage.new(user)
    storage.save()
    return jsonify(
      {
        "data": user_out_schema.dump(user)
      }
    ), 200

@bp.post("/users/<user_id>/author")
@roles_required(["admin"])
def link_author(user_id):
    """
    link user to Author - admin
    ---
    tags:
      - Users
    security:
      - Bearer: []
    consumes:
      - application/json
    parameters:
      - in: path
        name: user_id
        type: string
        required: true
      - in: body
        name: body
        schema:
          type: object
          properties:
            author_id: { type: string }
            author_name: { type: string }
    responses:
      200: { description: OK }
      401: { description: Unauthorized }
    """
    payload = request.get_json(silent=True) or {}
    author_id = payload.get("author_id")
    
    session = storage.get_session()
    user = session.query(User).get(user_id)
    author = session.query(Author).filter(Author.id == author_id).first()
    if not user:
        abort(404)
    if not author:
        abort(401, description="Author does not exist")
    if user.author:
        abort(409, description="user already linked to a author")
    author.user_id = user_id
    if user.roles:
        user.roles.append("author")
    else:
        user.roles = ["author"]
    flag_modified(user, "roles")
    storage.new(user)
    storage.new(author)
    storage.save()
    return jsonify(
      {
        "data": user_out_schema.dump(user)
      }
    ), 200