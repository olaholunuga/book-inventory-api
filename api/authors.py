from __future__ import annotations

from typing import Tuple

from flask import Blueprint, request, jsonify, abort
from marshmallow import ValidationError
from sqlalchemy import func

from models import storage
from models.author import Author
from models.schemas.author import (
    AuthorCreateSchema,
    AuthorUpdateSchema,
    AuthorOutSchema,
)

bp = Blueprint("authors", __name__)

create_schema = AuthorCreateSchema()
update_schema = AuthorUpdateSchema()
out_schema = AuthorOutSchema()
out_list_schema = AuthorOutSchema(many=True)

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
    return (Author.name.desc() if desc else Author.name.asc(),)


@bp.post("/authors")
def create_author():
    """
    Create an author
    ---
    tags: [Authors]
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name: { type: string, maxLength: 128 }
    responses:
      201: { description: Created }
      422: { description: Validation error }
    """
    session = storage.get_session()
    data = create_schema.load(request.get_json(silent=True) or {})
    # No uniqueness on Author by design (names can collide)
    a = Author(name=data["name"])
    storage.new(a)
    storage.save()
    return jsonify({"data": out_schema.dump(a)}), 201


@bp.get("/authors")
def list_authors():
    """
    List authors (supports pagination, sorting, q search, include_deleted)
    ---
    tags: [Authors]
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

    query = session.query(Author)
    if not include_deleted:
        query = query.filter(Author.deleted_at.is_(None))
    if q:
        qnorm = f"%{q.strip().lower()}%"
        query = query.filter(func.lower(Author.name).like(qnorm))

    total = query.count()
    rows = query.order_by(*order_by).offset((page - 1) * limit).limit(limit).all()
    return jsonify({"data": out_list_schema.dump(rows), "meta": {"page": page, "limit": limit, "total": total}})


@bp.get("/authors/<author_id>")
def get_author(author_id: str):
    """
    Get an author by id
    ---
    tags: [Authors]
    parameters:
      - in: path
        name: author_id
        type: string
        required: true
    responses:
      200: { description: OK }
      404: { description: Not found }
    """
    session = storage.get_session()
    a = session.query(Author).get(author_id)
    if not a:
        abort(404)
    return jsonify({"data": out_schema.dump(a)})


@bp.patch("/authors/<author_id>")
def update_author(author_id: str):
    """
    Update an author (partial)
    ---
    tags: [Authors]
    parameters:
      - in: path
        name: author_id
        type: string
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            name: { type: string, maxLength: 128 }
    responses:
      200: { description: OK }
      404: { description: Not found }
      422: { description: Validation error }
    """
    session = storage.get_session()
    a = session.query(Author).get(author_id)
    if not a:
        abort(404)
    data = update_schema.load(request.get_json(silent=True) or {})
    if "name" in data:
        a.name = data["name"]
    storage.new(a)
    storage.save()
    return jsonify({"data": out_schema.dump(a)})


@bp.delete("/authors/<author_id>")
def delete_author(author_id: str):
    """
    Soft delete an author (sets deleted_at)
    ---
    tags: [Authors]
    parameters:
      - in: path
        name: author_id
        type: string
        required: true
    responses:
      204: { description: Deleted }
      404: { description: Not found }
    """
    session = storage.get_session()
    a = session.query(Author).get(author_id)
    if not a:
        abort(404)
    # Soft delete via mixin override
    a.delete()
    return ("", 204)

@bp.post("/authors/<author_id>/restore")
def restore_author(author_id: str):
    """restores any deleted author
    ---
    tags: [Authors]
    parameters:
      - in: path
        name: author_id
        type: string
        required: true
    responses:
      200: { description: Restored }
      404: { description: Not found }
    """
    session = storage.get_session()
    a = session.query(Author).get(author_id)
    if not a:
      abort(404)
    # restores the formerlly deleted author
    a.restore()
    return jsonify({"data": out_schema.dump(a)})