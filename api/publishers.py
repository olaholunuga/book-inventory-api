from __future__ import annotations

from typing import Tuple

from flask import Blueprint, request, jsonify, abort
from marshmallow import ValidationError
from sqlalchemy import func
from utils.decorators import roles_required

from models import storage
from models.publisher import Publisher
from models.book import Book
from models.schemas.publisher import (
    PublisherCreateSchema,
    PublisherUpdateSchema,
    PublisherOutSchema,
)

bp = Blueprint("publishers", __name__)

create_schema = PublisherCreateSchema()
update_schema = PublisherUpdateSchema()
out_schema = PublisherOutSchema()
out_list_schema = PublisherOutSchema(many=True)

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
    return (Publisher.name.desc() if desc else Publisher.name.asc(),)


def exists_name_case_insensitive(session, name: str, exclude_id: str | None = None) -> bool:
    q = session.query(Publisher).filter(func.lower(Publisher.name) == name.lower())
    if exclude_id:
        q = q.filter(Publisher.id != exclude_id)
    q = q.filter(Publisher.deleted_at.is_(None))
    return session.query(q.exists()).scalar()


@bp.post("/publishers")
@roles_required(["admin"])
def create_publisher():
    """
    Create a publisher
    ---
    tags: [Publishers]
    security:
      - Bearer: []
    consumes: [application/json]
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
      409: { description: Name already exists }
      422: { description: Validation error }
    """
    session = storage.get_session()
    data = create_schema.load(request.get_json(silent=True) or {})
    if exists_name_case_insensitive(session, data["name"]):
        abort(409, description="Publisher name already exists.")
    p = Publisher(name=data["name"])
    storage.new(p)
    storage.save()
    return jsonify({"data": out_schema.dump(p)}), 201


@bp.get("/publishers")
def list_publishers():
    """
    List publishers (pagination, sorting, q search, include_deleted)
    ---
    tags: [Publishers]
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

    query = session.query(Publisher)
    if not include_deleted:
        query = query.filter(Publisher.deleted_at.is_(None))
    if q:
        qnorm = f"%{q.strip().lower()}%"
        query = query.filter(func.lower(Publisher.name).like(qnorm))

    total = query.count()
    rows = query.order_by(*order_by).offset((page - 1) * limit).limit(limit).all()
    return jsonify({"data": out_list_schema.dump(rows), "meta": {"page": page, "limit": limit, "total": total}})


@bp.get("/publishers/<publisher_id>")
def get_publisher(publisher_id: str):
    """
    Get a publisher by id
    ---
    tags: [Publishers]
    parameters:
      - in: path
        name: publisher_id
        type: string
        required: true
    responses:
      200: { description: OK }
      404: { description: Not found }
    """
    session = storage.get_session()
    p = session.query(Publisher).get(publisher_id)
    if not p:
        abort(404)
    return jsonify({"data": out_schema.dump(p)})


@bp.patch("/publishers/<publisher_id>")
@roles_required(["admin"])
def update_publisher(publisher_id: str):
    """
    Update a publisher (partial)
    ---
    tags: [Publishers]
    security:
      - Bearer: []
    parameters:
      - in: path
        name: publisher_id
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
      409: { description: Name already exists }
      422: { description: Validation error }
    """
    session = storage.get_session()
    p = session.query(Publisher).get(publisher_id)
    if not p:
        abort(404)
    data = update_schema.load(request.get_json(silent=True) or {})
    if "name" in data:
        if exists_name_case_insensitive(session, data["name"], exclude_id=p.id):
            abort(409, description="Publisher name already exists.")
        p.name = data["name"]
    storage.new(p)
    storage.save()
    return jsonify({"data": out_schema.dump(p)})


@bp.delete("/publishers/<publisher_id>")
@roles_required(["admin"])
def delete_publisher(publisher_id: str):
    """
    Soft delete a publisher (sets deleted_at)
    Note: This is a soft delete, so we do not invoke FK RESTRICT.
    Hard delete would be restricted if books reference this publisher.
    ---
    tags: [Publishers]
    security:
      - Bearer: []
    parameters:
      - in: path
        name: publisher_id
        type: string
        required: true
    responses:
      204: { description: Deleted }
      404: { description: Not found }
    """
    session = storage.get_session()
    p = session.query(Publisher).get(publisher_id)
    if not p:
        abort(404)
    p.delete()  # Soft delete via mixin
    return ("", 204)


@bp.post("/publishers/<publisher_id>/restore")
@roles_required(["admin"])
def restore_publisher(publisher_id: str):
    """
    Restore a soft-deleted publisher
    ---
    tags: [Publishers]
    security:
      - Bearer: []
    parameters:
      - in: path
        name: publisher_id
        type: string
        required: true
    responses:
      200: { description: Restored }
      404: { description: Not found }
      409: { description: Active publisher with same name exists }
    """
    session = storage.get_session()
    p = session.query(Publisher).get(publisher_id)
    if not p:
        abort(404)
    if p.deleted_at is not None and exists_name_case_insensitive(session, p.name, exclude_id=p.id):
        abort(409, description="Another active publisher with the same name exists.")
    p.restore()
    return jsonify({"data": out_schema.dump(p)})