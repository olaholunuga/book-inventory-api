from __future__ import annotations

from typing import List, Tuple, Optional
from datetime import date

from flask import Blueprint, request, jsonify, abort
from marshmallow import ValidationError
from sqlalchemy import func

from models import storage
from models.book import Book
from models.inventory_transaction import InventoryTransaction, InventoryReason
from models.schemas.transaction import (
    InventoryTransactionCreateSchema,
    InventoryTransactionOutSchema,
)
from utils.decorators import jwt_required, roles_required

bp = Blueprint("transactions", __name__)

tx_create_schema = InventoryTransactionCreateSchema()
tx_out_schema = InventoryTransactionOutSchema()
tx_list_out_schema = InventoryTransactionOutSchema(many=True)

MAX_LIMIT = 100

SORT_COLUMNS = {
    "created_at": InventoryTransaction.created_at,
    "delta_quantity": InventoryTransaction.delta_quantity,
}


def parse_pagination() -> Tuple[int, int]:
    try:
        page = int(request.args.get("page", "1"))
        limit = int(request.args.get("limit", "20"))
        if page < 1:
            page = 1
        if limit < 1:
            limit = 1
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT
        return page, limit
    except ValueError:
        abort(400, description="page and limit must be integers")


def parse_sort(default: str = "-created_at"):
    sort_param = request.args.get("sort", default)
    fields = [s.strip() for s in sort_param.split(",") if s.strip()]
    order_by = []
    for f in fields:
        desc = f.startswith("-")
        key = f[1:] if desc else f
        col = SORT_COLUMNS.get(key)
        if not col:
            abort(400, description=f"Unsupported sort field: {key}")
        order_by.append(col.desc() if desc else col.asc())
    return order_by if order_by else [InventoryTransaction.created_at.desc()]


def parse_date_param(name: str) -> Optional[date]:
    val = request.args.get(name)
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        abort(400, description=f"Invalid date format for {name}. Use YYYY-MM-DD")


def normalize_reason(raw: str) -> InventoryReason:
    if raw is None:
        raise ValidationError("reason is required")
    try:
        return InventoryReason(raw.upper())
    except ValueError:
        allowed = [r.value for r in InventoryReason]
        raise ValidationError(f"reason must be one of {allowed}")


@bp.post("/transactions")
@roles_required(["admin"])
def create_transaction():
    """
    Apply an inventory transaction (adjust stock) and record it - admin
    ---
    tags:
      - Inventory
    security:
      - Bearer: []
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            book_id: { type: string }
            delta_quantity: { type: integer, description: "positive to increase, negative to decrease", example: -2 }
            reason:
              type: string
              enum: [PURCHASE, SALE, RETURN, ADJUSTMENT]
            note: { type: string, maxLength: 255 }
    responses:
      201:
        description: Created
      400:
        description: Bad request (e.g., negative resulting quantity, invalid FK)
      404:
        description: Book not found
      422:
        description: Validation error
    """
    session = storage.get_session()
    payload = request.get_json(silent=True) or {}
    data = tx_create_schema.load(payload)

    # Validate and normalize reason to enum
    try:
        reason = normalize_reason(data["reason"])
    except ValidationError as ve:
        abort(422, description=str(ve))

    # Validate book
    b = session.query(Book).get(data["book_id"])
    if not b:
        abort(404, description="Book not found")

    delta = int(data["delta_quantity"])
    new_qty = (b.quantity or 0) + delta
    if new_qty < 0:
        abort(400, description="Resulting quantity would be negative")

    # Apply update and record transaction atomically
    b.quantity = new_qty
    tx = InventoryTransaction(
        book_id=b.id,
        delta_quantity=delta,
        reason=reason,
        note=data.get("note"),
        resulting_quantity=new_qty,
    )

    storage.new(b)
    storage.new(tx)
    storage.save()

    return jsonify({"data": tx_out_schema.dump(tx)}), 201


@bp.get("/transactions")
@jwt_required()
def list_transactions():
    """
    List inventory transactions with pagination, sorting, and filters - user
    ---
    tags:
      - Inventory
    security:
      - Bearer: []
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
        description: "Allowed: -created_at (default), created_at, delta_quantity, -delta_quantity"
        default: "-created_at"
      - in: query
        name: book_id
        type: string
      - in: query
        name: reason
        type: string
        enum: [PURCHASE, SALE, RETURN, ADJUSTMENT]
      - in: query
        name: created_from
        type: string
        format: date
        description: "YYYY-MM-DD (inclusive)"
      - in: query
        name: created_to
        type: string
        format: date
        description: "YYYY-MM-DD (inclusive)"
    responses:
      200:
        description: List of transactions
    """
    session = storage.get_session()
    page, limit = parse_pagination()
    order_by = parse_sort(default="-created_at")

    query = session.query(InventoryTransaction)

    book_id = request.args.get("book_id")
    if book_id:
        query = query.filter(InventoryTransaction.book_id == book_id)

    reason_str = request.args.get("reason")
    if reason_str:
        try:
            reason = normalize_reason(reason_str)
            query = query.filter(InventoryTransaction.reason == reason)
        except ValidationError as ve:
            abort(422, description=str(ve))

    created_from = parse_date_param("created_from")
    created_to = parse_date_param("created_to")
    if created_from:
        query = query.filter(func.date(InventoryTransaction.created_at) >= created_from)
    if created_to:
        query = query.filter(func.date(InventoryTransaction.created_at) <= created_to)

    total = query.count()
    rows = (
        query.order_by(*order_by)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return jsonify(
        {
            "data": tx_list_out_schema.dump(rows),
            "meta": {
                "page": page,
                "limit": limit,
                "total": total,
                "sort": request.args.get("sort", "-created_at"),
                "filters": {k: v for k, v in request.args.items()},
            },
        }
    )


@bp.get("/transactions/<tx_id>")
@jwt_required()
def get_transaction(tx_id: str):
    """
    Get a single inventory transaction by id - user
    ---
    tags:
      - Inventory
    security:
      - Bearer: []
    parameters:
      - in: path
        name: tx_id
        type: string
        required: true
    responses:
      200:
        description: Transaction found
      404:
        description: Not found
    """
    session = storage.get_session()
    tx = session.query(InventoryTransaction).get(tx_id)
    if not tx:
        abort(404)
    return jsonify({"data": tx_out_schema.dump(tx)})


@bp.get("/books/<book_id>/transactions")
@jwt_required()
def list_transactions_for_book(book_id: str):
    """
    List inventory transactions for a specific book - user
    ---
    tags:
      - Inventory
    security:
      - Bearer: []
    parameters:
      - in: path
        name: book_id
        type: string
        required: true
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
        description: "Allowed: -created_at (default), created_at, delta_quantity, -delta_quantity"
        default: "-created_at"
      - in: query
        name: created_from
        type: string
        format: date
      - in: query
        name: created_to
        type: string
        format: date
    responses:
      200:
        description: List of transactions for the book
      404:
        description: Book not found
    """
    session = storage.get_session()
    # Ensure book exists (consistent with 404 expectations)
    b = session.query(Book).get(book_id)
    if not b:
        abort(404, description="Book not found")

    page, limit = parse_pagination()
    order_by = parse_sort(default="-created_at")

    query = session.query(InventoryTransaction).filter(InventoryTransaction.book_id == book_id)

    created_from = parse_date_param("created_from")
    created_to = parse_date_param("created_to")
    if created_from:
        query = query.filter(func.date(InventoryTransaction.created_at) >= created_from)
    if created_to:
        query = query.filter(func.date(InventoryTransaction.created_at) <= created_to)

    total = query.count()
    rows = (
        query.order_by(*order_by)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return jsonify(
        {
            "data": tx_list_out_schema.dump(rows),
            "meta": {
                "page": page,
                "limit": limit,
                "total": total,
                "sort": request.args.get("sort", "-created_at"),
                "filters": {k: v for k, v in request.args.items()},
                "book_id": book_id,
            },
        }
    )