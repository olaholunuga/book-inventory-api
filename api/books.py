from __future__ import annotations

from datetime import datetime, date
from typing import List, Tuple, Optional

from flask import Blueprint, request, jsonify, abort
from sqlalchemy import or_, and_, func
from marshmallow import ValidationError
from utils.decorators import roles_required

from models import storage
from models.book import Book, book_authors, book_categories
from models.author import Author
from models.category import Category
from models.publisher import Publisher
from models.inventory_transaction import InventoryTransaction
from models.schemas.book import BookCreateSchema, BookUpdateSchema, BookOutSchema
from models.schemas.common import validate_and_normalize_isbn

bp = Blueprint("books", __name__)

# Schemas
book_create_schema = BookCreateSchema()
book_update_schema = BookUpdateSchema()
book_out_schema = BookOutSchema()
books_out_schema = BookOutSchema(many=True)

# Sorting allowlist: API field -> SQLAlchemy column
SORT_COLUMNS = {
    "title": Book.title,
    "published_date": Book.published_date,
    "price": Book.price,
    "created_at": Book.created_at,
    "updated_at": Book.updated_at,
}

MAX_LIMIT = 100


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


def parse_sort() -> List:
    sort_param = request.args.get("sort", "title")
    fields = [s.strip() for s in sort_param.split(",") if s.strip()]
    order_by = []
    for f in fields:
        desc = f.startswith("-")
        key = f[1:] if desc else f
        col = SORT_COLUMNS.get(key)
        if not col:
            abort(400, description=f"Unsupported sort field: {key}")
        order_by.append(col.desc() if desc else col.asc())
    return order_by if order_by else [Book.title.asc()]


def parse_date_param(name: str) -> Optional[date]:
    val = request.args.get(name)
    if not val:
        return None
    try:
        return date.fromisoformat(val)
    except ValueError:
        abort(400, description=f"Invalid date format for {name}. Use YYYY-MM-DD")


def normalize_isbn_for_filter(val: Optional[str]) -> Optional[str]:
    if val is None:
        return None
    try:
        return validate_and_normalize_isbn(val)
    except ValidationError:
        abort(400, description="Invalid ISBN provided for filtering.")


def apply_filters(query):
    # Filters
    author_id = request.args.get("author_id")
    category_id = request.args.get("category_id")
    publisher_id = request.args.get("publisher_id")
    isbn = normalize_isbn_for_filter(request.args.get("isbn"))
    price_min = request.args.get("price_min")
    price_max = request.args.get("price_max")
    published_from = parse_date_param("published_from")
    published_to = parse_date_param("published_to")
    q = request.args.get("q")

    # M2M joins when needed
    if author_id:
        query = (
            query.join(book_authors, book_authors.c.book_id == Book.id)
                 .join(Author, Author.id == book_authors.c.author_id)
                 .filter(Author.deleted_at.is_(None))
                 .filter(Author.id == author_id)
        )

    if category_id:
        query = (
            query.join(book_categories, book_categories.c.book_id == Book.id)
                 .join(Category, Category.id == book_categories.c.category_id)
                 .filter(Category.deleted_at.is_(None))
                 .filter(Category.id == category_id)
        )

    if publisher_id:
        query = query.filter(Book.publisher_id == publisher_id)

    if isbn:
        query = query.filter(Book.isbn == isbn)

    if price_min is not None:
        try:
            # Let DB do decimal comparison (SQLAlchemy Numeric)
            query = query.filter(Book.price >= price_min)
        except Exception:
            abort(400, description="Invalid price_min")

    if price_max is not None:
        try:
            query = query.filter(Book.price <= price_max)
        except Exception:
            abort(400, description="Invalid price_max")

    if published_from:
        query = query.filter(Book.published_date >= published_from)

    if published_to:
        query = query.filter(Book.published_date <= published_to)

    if q:
        # Case-insensitive search across Book.title and Author.name
        qnorm = f"%{q.strip().lower()}%"
        # outerjoin authors so we can OR across both, and distinct to dedupe
        query = (
            query.outerjoin(book_authors, book_authors.c.book_id == Book.id)
                 .outerjoin(Author, Author.id == book_authors.c.author_id)
                 .filter(
                     or_(
                         func.lower(Book.title).like(qnorm),
                         and_(Author.deleted_at.is_(None), func.lower(Author.name).like(qnorm)),
                     )
                 )
        )

    return query


@bp.post("/books")
@roles_required(["admin", "author"])
def create_book():
    """
    Create a new book
    ---
    tags:
      - Books
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
            title: { type: string, maxLength: 255 }
            isbn: { type: string, description: "ISBN-10 or ISBN-13" }
            published_date: { type: string, format: date }
            pages: { type: integer, minimum: 1 }
            quantity: { type: integer, minimum: 0, default: 0 }
            price: { type: string, example: "19.99" }
            description: { type: string }
            publisher_id: { type: string }
            author_ids:
              type: array
              items: { type: string }
            category_ids:
              type: array
              items: { type: string }
    responses:
      201:
        description: Created
      409:
        description: Book with same ISBN already exists
      422:
        description: Validation error
    """
    session = storage.get_session()
    payload = request.get_json(silent=True) or {}
    data = book_create_schema.load(payload)

    # Idempotency: check for existing ISBN (normalized)
    existing = session.query(Book).filter(Book.isbn == data["isbn"]).first()
    if existing:
        abort(409, description="A book with this ISBN already exists.")

    # Validate foreign keys if provided
    if data.get("publisher_id"):
        if not session.query(Publisher).get(data["publisher_id"]):
            abort(400, description="publisher_id not found")

    authors = []
    if data.get("author_ids"):
        authors = session.query(Author).filter(Author.id.in_(data["author_ids"])).all()
        if len(authors) != len(set(data["author_ids"])):
            abort(400, description="One or more author_ids not found")

    categories = []
    if data.get("category_ids"):
        categories = (
            session.query(Category).filter(Category.id.in_(data["category_ids"])).all()
        )
        if len(categories) != len(set(data["category_ids"])):
            abort(400, description="One or more category_ids not found")

    # Create Book
    b = Book(
        title=data["title"],
        isbn=data["isbn"],
        published_date=data.get("published_date"),
        pages=data.get("pages"),
        quantity=data.get("quantity", 0),
        price=data.get("price"),
        description=data.get("description"),
        publisher_id=data.get("publisher_id"),
    )
    # Set relationships
    if authors:
        b.authors = authors
    if categories:
        b.categories = categories

    storage.new(b)
    storage.save()

    return jsonify({"data": book_out_schema.dump(b)}), 201


@bp.get("/books")
def list_books():
    """
    List books with pagination, sorting, filtering, and search
    ---
    tags:
      - Books
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
        description: "Comma-separated fields; prefix with '-' for desc. Allowed: title, published_date, price, created_at, updated_at"
        default: "title"
      - in: query
        name: author_id
        type: string
      - in: query
        name: category_id
        type: string
      - in: query
        name: publisher_id
        type: string
      - in: query
        name: isbn
        type: string
      - in: query
        name: price_min
        type: string
      - in: query
        name: price_max
        type: string
      - in: query
        name: published_from
        type: string
        format: date
      - in: query
        name: published_to
        type: string
        format: date
      - in: query
        name: q
        type: string
        description: "Case-insensitive substring search on title and author name"
    responses:
      200:
        description: List of books
    """
    session = storage.get_session()
    page, limit = parse_pagination()
    order_by = parse_sort()

    query = session.query(Book)
    query = apply_filters(query)
    # Distinct to avoid duplicates when joins are used (q, author_id, category_id)
    total = query.distinct(Book.id).count()
    rows = (
        query.order_by(*order_by)
        .distinct(Book.id)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return jsonify(
        {
            "data": books_out_schema.dump(rows),
            "meta": {
                "page": page,
                "limit": limit,
                "total": total,
                "sort": request.args.get("sort", "title"),
                "filters": {k: v for k, v in request.args.items()},
            },
        }
    )


@bp.get("/books/<book_id>")
def get_book(book_id: str):
    """
    Get a single book by id
    ---
    tags:
      - Books
    parameters:
      - in: path
        name: book_id
        type: string
        required: true
    responses:
      200:
        description: Book found
      404:
        description: Not found
    """
    session = storage.get_session()
    b = session.query(Book).get(book_id)
    if not b:
        abort(404)
    return jsonify({"data": book_out_schema.dump(b)})


@bp.patch("/books/<book_id>")
@roles_required(["admin", "author"])
def update_book(book_id: str):
    """
    Update a book (partial)
    ---
    tags:
      - Books
    security:
      - Bearer: []
    consumes:
      - application/json
    parameters:
      - in: path
        name: book_id
        type: string
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
    responses:
      200:
        description: Updated
      404:
        description: Not found
      409:
        description: Conflict (e.g., duplicate ISBN)
      422:
        description: Validation error
    """
    session = storage.get_session()
    b = session.query(Book).get(book_id)
    if not b:
        abort(404)

    payload = request.get_json(silent=True) or {}
    data = book_update_schema.load(payload)

    # Handle ISBN update with idempotency
    if "isbn" in data and data["isbn"] != b.isbn:
        exists = session.query(Book).filter(Book.isbn == data["isbn"]).first()
        if exists:
            abort(409, description="A book with this ISBN already exists.")
        b.isbn = data["isbn"]

    # Publisher
    if "publisher_id" in data:
        if data["publisher_id"] and not session.query(Publisher).get(data["publisher_id"]):
            abort(400, description="publisher_id not found")
        b.publisher_id = data["publisher_id"]

    # Simple fields
    for field in ["title", "published_date", "pages", "quantity", "price", "description"]:
        if field in data:
            setattr(b, field, data[field])

    # Relationships: if provided, replace
    if "author_ids" in data:
        authors = session.query(Author).filter(Author.id.in_(data["author_ids"] or [])).all()
        if len(authors) != len(set(data["author_ids"] or [])):
            abort(400, description="One or more author_ids not found")
        b.authors = authors

    if "category_ids" in data:
        categories = session.query(Category).filter(Category.id.in_(data["category_ids"] or [])).all()
        if len(categories) != len(set(data["category_ids"] or [])):
            abort(400, description="One or more category_ids not found")
        b.categories = categories

    storage.new(b)
    storage.save()
    return jsonify({"data": book_out_schema.dump(b)})


@bp.delete("/books/<book_id>")
@roles_required(["author", "admin"])
def delete_book(book_id: str):
    """
    Delete a book
    ---
    tags:
      - Books
    security:
      - Bearer: []
    parameters:
      - in: path
        name: book_id
        type: string
        required: true
    responses:
      204:
        description: Deleted
      404:
        description: Not found
      409:
        description: Cannot delete due to existing transactions
    """
    session = storage.get_session()
    b = session.query(Book).get(book_id)
    if not b:
        abort(404)

    # RESTRICT: do not allow delete if transactions exist
    tx_exists = (
        session.query(InventoryTransaction)
        .filter(InventoryTransaction.book_id == b.id)
        .first()
    )
    if tx_exists:
        abort(409, description="Cannot delete book with existing inventory transactions.")

    storage.delete(b)
    storage.save()
    return ("", 204)