from __future__ import annotations

from typing import Tuple

from flask import Blueprint, request, jsonify, abort
from marshmallow import ValidationError
from sqlalchemy import func

from models import storage
from models.category import Category
from models.schemas.category import (
    CategoryCreateSchema,
    CategoryUpdateSchema,
    CategoryOutSchema,
)

bp = Blueprint("categories", __name__)

create_schema = CategoryCreateSchema()
update_schema = CategoryUpdateSchema()
out_schema = CategoryOutSchema()
out_list_schema = CategoryOutSchema(many=True)

MAX_LIMIT = 100


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
    return (Category.name.desc() if desc else Category.name.asc(),)


def exists_name_case_insensitive(session, name: str, exclude_id: str | None = None) -> bool:
    q = session.query(Category).filter(func.lower(Category.name) == name.lower())
    if exclude_id:
        q = q.filter(Category.id != exclude_id)
    # Exclude soft-deleted to behave as “active name uniqueness”
    q = q.filter(Category.deleted_at.is_(None))
    return session.query(q.exists()).scalar()


@bp.post("/categories")
def create_category():
    """
    Create a category
    ---
    tags: [Categories]
    consumes: [application/json]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name: { type: string, maxLength: 64 }
    responses:
      201: { description: Created }
      409: { description: Name already exists }
      422: { description: Validation error }
    """
    session = storage.get_session()
    data = create_schema.load(request.get_json(silent=True) or {})
    if exists_name_case_insensitive(session, data["name"]):
        abort(409, description="Category name already exists.")
    c = Category(name=data["name"])
    storage.new(c)
    storage.save()
    return jsonify({"data": out_schema.dump(c)}), 201


@bp.get("/categories")
def list_categories():
    """
    List categories (pagination, sorting, q search, include_deleted)
    ---
    tags: [Categories]
    parameters:
      - in: query
        name: page
        type: integer
        default: 1
      - in: query
        name: limit
        type: integer
        default: 20
      - in: query
        name: sort
        type: string
        default: name
        description: "Allowed: name or -name"
      - in: query
        name: q
        type: string
      - in: query
        name: include_deleted
        type: boolean
        default: false
    responses:
      200: { description: OK }
    """
    session = storage.get_session()
    page, limit = parse_pagination()
    order_by = parse_sort()

    include_deleted = request.args.get("include_deleted", "false").lower() in ("1", "true", "yes")
    q = request.args.get("q")

    query = session.query(Category)
    if not include_deleted:
        query = query.filter(Category.deleted_at.is_(None))
    if q:
        qnorm = f"%{q.strip().lower()}%"
        query = query.filter(func.lower(Category.name).like(qnorm))

    total = query.count()
    rows = query.order_by(*order_by).offset((page - 1) * limit).limit(limit).all()
    return jsonify({"data": out_list_schema.dump(rows), "meta": {"page": page, "limit": limit, "total": total}})


@bp.get("/categories/<category_id>")
def get_category(category_id: str):
    """
    Get a category by id
    ---
    tags: [Categories]
    parameters:
      - in: path
        name: category_id
        type: string
        required: true
    responses:
      200: { description: OK }
      404: { description: Not found }
    """
    session = storage.get_session()
    c = session.query(Category).get(category_id)
    if not c:
        abort(404)
    return jsonify({"data": out_schema.dump(c)})


@bp.patch("/categories/<category_id>")
def update_category(category_id: str):
    """
    Update a category (partial)
    ---
    tags: [Categories]
    parameters:
      - in: path
        name: category_id
        type: string
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name: { type: string, maxLength: 64 }
    responses:
      200: { description: OK }
      404: { description: Not found }
      409: { description: Name already exists }
      422: { description: Validation error }
    """
    session = storage.get_session()
    c = session.query(Category).get(category_id)
    if not c:
        abort(404)
    data = update_schema.load(request.get_json(silent=True) or {})
    if "name" in data:
        if exists_name_case_insensitive(session, data["name"], exclude_id=c.id):
            abort(409, description="Category name already exists.")
        c.name = data["name"]
    storage.new(c)
    storage.save()
    return jsonify({"data": out_schema.dump(c)})


@bp.delete("/categories/<category_id>")
def delete_category(category_id: str):
    """
    Soft delete a category (sets deleted_at)
    ---
    tags: [Categories]
    parameters:
      - in: path
        name: category_id
        type: string
        required: true
    responses:
      204: { description: Deleted }
      404: { description: Not found }
    """
    session = storage.get_session()
    c = session.query(Category).get(category_id)
    if not c:
        abort(404)
    c.delete()  # Soft delete via mixin
    return ("", 204)

@bp.post("categories/<category_id>/restore")
def restore_category(category_id: str):
    """
    restores all soft-deleted categories
    ---
    tags: [Categories]
    parameters:
      - in: path
        name: category_id
        type: string
        required: true
    responces:
      200: { description: Restored }
      404: { description: Not found }
    """
    session = storage.get_session()
    c = session.query(Category).get(category_id)
    if not c:
        abort(404)
    # Enforce active uniqueness on restore
    if c.deleted_at is not None and exists_name_case_insensitive(session, c.name, exclude_id=c.id):
        abort(409, description="Another active category with the same name exists.")
    c.restore()
    return jsonify({"data": out_schema.dump(c)})