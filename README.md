# Book Inventory API

A Flask API for managing books, authors, categories, publishers, and inventory transactions.

- Base path: `/api/v1`
- Swagger UI: `/apidocs/`
- Swagger JSON: `/swagger.json`
- Error envelope: `{"error": "...", "message": "...", "details": {...}, "status": 400}`

This README serves both API users and developers. It explains how to run the project, the API rules and endpoints, and the design choices behind them.

---

## Table of Contents

- [Features](#features)
- [Quick Start (API Users)](#quick-start-api-users)
  - [Health](#health)
  - [Books](#books)
  - [Transactions](#transactions)
  - [Authors](#authors)
  - [Categories](#categories)
  - [Publishers](#publishers)
- [Lists: Pagination, Sorting, Filtering, Search](#lists-pagination-sorting-filtering-search)
- [Error Format](#error-format)
- [Idempotency](#idempotency)
- [Installation (Developers)](#installation-developers)
  - [Requirements](#requirements)
  - [Environment variables](#environment-variables)
  - [Run the server](#run-the-server)
  - [Database & Migrations](#database--migrations)
  - [Testing](#testing)
  - [Lint/Format](#lintformat)
- [Architecture & Design](#architecture--design)
  - [Data model summary](#data-model-summary)
  - [UUIDs & Soft/Hard Deletes](#uuids--softhard-deletes)
  - [Validation & Serialization](#validation--serialization)
  - [Swagger docs](#swagger-docs)
  - [CORS](#cors)
- [Roadmap](#roadmap)
- [References](#references)

---

## Features

- Entities: Book, Author, Category, Publisher, InventoryTransaction
- Relationships:
  - Many-to-many: Book–Author, Book–Category
  - Many-to-one: Book–Publisher
- Inventory:
  - Immutable transaction ledger with `delta_quantity` and `resulting_quantity`
  - Non-negative stock enforced (no going below zero)
- Data rules:
  - ISBN (10/13) normalized (digits-only; ISBN-10 may end with X), unique
  - `published_date` cannot be in the future
  - `quantity` default 0, `price` is USD with scale 2
- Soft delete:
  - Authors, Categories, Publishers have `deleted_at` and can be restored
- Hard delete:
  - Books delete is allowed only if no inventory transactions exist (RESTRICT)
- Listing features:
  - Pagination (`page`, `limit`)
  - Sorting (e.g., `sort=title,-published_date`)
  - Filtering (by author, category, publisher, isbn, price/published_date ranges)
  - Search (`q`) across title and author name (case-insensitive)
- Docs:
  - Flasgger Swagger at `/apidocs`

---

## Quick Start (API Users)

When the server is running (see developer setup below), browse to:
- Swagger UI: http://localhost:8000/apidocs/
- Health: http://localhost:8000/api/v1/health

Below are cURL examples. Replace `<id>` with actual UUIDs returned by the API.

### Health

```bash
curl -s http://localhost:8000/api/v1/health | jq
```

Response:
```json
{"status":"ok","version":"1.0.0"}
```

### Books

Create a book (idempotent on ISBN):
```bash
curl -s -X POST http://localhost:8000/api/v1/books \
  -H "Content-Type: application/json" \
  -d '{
        "title": "Clean Code",
        "isbn": "978-0132350884",
        "published_date": "2008-08-01",
        "pages": 464,
        "quantity": 0,
        "price": "29.99",
        "description": "A Handbook of Agile Software Craftsmanship"
      }' | jq
```

Get a book:
```bash
curl -s http://localhost:8000/api/v1/books/<book_id> | jq
```

List books (pagination, sorting, search):
```bash
curl -s "http://localhost:8000/api/v1/books?page=1&limit=20&sort=title,-published_date&q=clean" | jq
```

Update a book:
```bash
curl -s -X PATCH http://localhost:8000/api/v1/books/<book_id> \
  -H "Content-Type: application/json" \
  -d '{"pages": 480, "price": "34.50"}' | jq
```

Delete a book (fails with 409 if transactions exist):
```bash
curl -i -X DELETE http://localhost:8000/api/v1/books/<book_id>
```

### Transactions

Increase stock by 10:
```bash
curl -s -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{"book_id":"<book_id>","delta_quantity":10,"reason":"PURCHASE","note":"PO-12345"}' | jq
```

Decrease stock by 2 (sale):
```bash
curl -s -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{"book_id":"<book_id>","delta_quantity":-2,"reason":"SALE"}' | jq
```

List transactions globally:
```bash
curl -s "http://localhost:8000/api/v1/transactions?sort=-created_at&limit=20" | jq
```

List transactions for one book:
```bash
curl -s "http://localhost:8000/api/v1/books/<book_id>/transactions?sort=-created_at" | jq
```

Notes:
- `delta_quantity` > 0 increases stock; < 0 decreases.
- `reason` ∈ {PURCHASE, SALE, RETURN, ADJUSTMENT}
- Resulting quantity is returned and persisted.

### Authors

Create:
```bash
curl -s -X POST http://localhost:8000/api/v1/authors \
  -H "Content-Type: application/json" \
  -d '{"name":"Robert C. Martin"}' | jq
```

List / search:
```bash
curl -s "http://localhost:8000/api/v1/authors?q=robert&sort=-name" | jq
```

Update:
```bash
curl -s -X PATCH http://localhost:8000/api/v1/authors/<author_id> \
  -H "Content-Type: application/json" \
  -d '{"name":"Uncle Bob"}' | jq
```

Soft delete:
```bash
curl -i -X DELETE http://localhost:8000/api/v1/authors/<author_id>
```

Restore:
```bash
curl -s -X POST http://localhost:8000/api/v1/authors/<author_id>/restore | jq
```

### Categories

Create (unique name, case-insensitive in “active” space):
```bash
curl -s -X POST http://localhost:8000/api/v1/categories \
  -H "Content-Type: application/json" \
  -d '{"name":"Software Engineering"}' | jq
```

List / search:
```bash
curl -s "http://localhost:8000/api/v1/categories?q=engineering" | jq
```

Update (409 on duplicate active name):
```bash
curl -s -X PATCH http://localhost:8000/api/v1/categories/<category_id> \
  -H "Content-Type: application/json" \
  -d '{"name":"Architecture"}' | jq
```

Soft delete / Restore:
```bash
curl -i -X DELETE http://localhost:8000/api/v1/categories/<category_id>
curl -s -X POST http://localhost:8000/api/v1/categories/<category_id>/restore | jq
```

### Publishers

Create (unique name, case-insensitive in “active” space):
```bash
curl -s -X POST http://localhost:8000/api/v1/publishers \
  -H "Content-Type: application/json" \
  -d '{"name":"Pearson"}' | jq
```

List / search:
```bash
curl -s "http://localhost:8000/api/v1/publishers?q=pear" | jq
```

Update / Soft delete / Restore:
```bash
curl -s -X PATCH http://localhost:8000/api/v1/publishers/<publisher_id> \
  -H "Content-Type: application/json" \
  -d '{"name":"Pearson PLC"}' | jq

curl -i -X DELETE http://localhost:8000/api/v1/publishers/<publisher_id>

curl -s -X POST http://localhost:8000/api/v1/publishers/<publisher_id>/restore | jq
```

---

## Lists: Pagination, Sorting, Filtering, Search

- Pagination:
  - `page` default 1; `limit` default 20; max 100.
- Sorting:
  - Books: `sort=title,-published_date` (allowlist: `title, published_date, price, created_at, updated_at`)
  - Transactions: `sort=-created_at` (allowlist: `created_at, delta_quantity`)
  - Authors/Categories/Publishers: `sort=name` (or `-name`)
- Filtering (Books):
  - `author_id`, `category_id`, `publisher_id` (exact match)
  - `isbn` (exact match on normalized value)
  - `price_min`, `price_max` (numeric)
  - `published_from`, `published_to` (`YYYY-MM-DD`, inclusive)
- Search:
  - `q` (Books): case-insensitive substring across Book.title and active (non-deleted) Author.name
  - `q` (Authors/Categories/Publishers): case-insensitive substring on name
- Soft-deleted rows:
  - Lists exclude soft-deleted authors/categories/publishers by default.
  - Use `include_deleted=true` to include them.

---

## Error Format

All errors return the same envelope:

```json
{
  "error": "VALIDATION_ERROR | NOT_FOUND | CONFLICT | BAD_REQUEST | INTERNAL_ERROR",
  "message": "Human readable summary",
  "details": { "field": ["issue", "..."] },
  "status": 422
}
```

Examples:
- 409 Conflict (duplicate ISBN or duplicate active name):
  ```json
  {"error":"CONFLICT","message":"A book with this ISBN already exists.","status":409}
  ```
- 400 Bad Request (negative resulting quantity):
  ```json
  {"error":"BAD_REQUEST","message":"Resulting quantity would be negative","status":400}
  ```

---

## Idempotency

- For `POST /api/v1/books`, ISBN is normalized and enforced unique.
- If you submit the same ISBN again, the API returns `409 CONFLICT` instead of creating a duplicate.

---

## Installation (Developers)

### Requirements

- Python 3.10.12
- SQLite (dev) or Postgres (prod)
- Recommended: virtual environment

Install Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# (optional) dev tools
pip install -r requirements-dev.txt
```

### Environment variables

Create a `.env` in the project root (values shown are dev-friendly):

```
APP_ENV=dev
SECRET_KEY=change-me
CORS_ORIGINS=*
# For production:
# DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

Dev uses SQLite at `sqlite:///book-store.db` automatically. In production, set `DATABASE_URL` to a Postgres URL.

### Run the server

```bash
python -m api
# Server: http://localhost:8000
# Docs:   http://localhost:8000/apidocs/
```

### Database & Migrations

We use Alembic. For the first run on dev, you can let the models create tables automatically. For schema evolution and production we use migrations:

```bash
# Initialize alembic once (if not already present)
alembic init migrations

# Generate a migration from current models
alembic revision --autogenerate -m "initial schema"

# Apply migrations
alembic upgrade head
```

SQLite notes:
- Foreign key enforcement is enabled with PRAGMA in code.
- Some ALTER operations are limited in SQLite; for big changes, generate a fresh dev DB.

### Testing

```bash
# Requires requirements-dev.txt
pytest -q
```

The test suite uses a temporary SQLite DB set via `DATABASE_URL` so it won’t touch your dev DB file.

### Lint/Format

```bash
ruff check .
isort .
black .
```

---

## Architecture & Design

### Data model summary

- Book
  - `id`, `title`, `isbn` (normalized unique), `published_date` (DATE), `pages` (>=1), `quantity` (>=0), `price` (USD Decimal 10,2), `description`, `publisher_id`
  - M2M: `authors`, `categories`
  - Hard-delete allowed only if no `InventoryTransaction` exists

- Author (soft-deletable)
  - `id`, `name`, `deleted_at`
  - M2M with `books`

- Category (soft-deletable, unique name)
  - `id`, `name` (unique), `deleted_at`
  - M2M with `books`

- Publisher (soft-deletable, unique name)
  - `id`, `name` (unique), `deleted_at`
  - One-to-many: `books` (Book FK has `ON DELETE RESTRICT`)

- InventoryTransaction (immutable)
  - `id`, `book_id`, `delta_quantity` (≠ 0), `reason` (enum), `note`, `resulting_quantity` (>= 0), `created_at`

### UUIDs & Soft/Hard Deletes

- All IDs are UUID v4 strings (36 chars, with hyphens).
- Soft-deleted entities set `deleted_at` and are excluded from lists by default.
- Restore endpoints:
  - `POST /api/v1/authors/<id>/restore`
  - `POST /api/v1/categories/<id>/restore` (409 if an active category of the same name exists)
  - `POST /api/v1/publishers/<id>/restore` (409 if an active publisher of the same name exists)

### Validation & Serialization

- Plain Marshmallow schemas (no Flask-Marshmallow).
- ISBN:
  - Accept ISBN-10 and ISBN-13
  - Normalize input (digits-only; ISBN-10 may end with X) and validate check digits
  - Persist normalized value and return normalized in responses
- Dates: `published_date` cannot be in the future.
- Numbers:
  - `quantity >= 0`
  - `price >= 0` (Decimal 10,2)
- Transactions:
  - `delta_quantity` can be positive or negative but not zero
  - Non-negative resulting quantity enforced

### Swagger docs

- The API is documented with Flasgger docstrings.
- Visit `/apidocs/` for interactive docs and to try endpoints in the browser.

### CORS

- CORS enabled for dev with `*`.
- Configure `CORS_ORIGINS` via `.env` for production.

---

## Roadmap

This project was intentionally built incrementally for clarity. Future enhancements you can add without breaking existing APIs:

- Idempotency keys for POST /transactions (prevent double-submission)
- Eager loading and `include=authors,categories` option for Books responses
- Price normalization policy (strict vs lenient rounding at the API layer)
- Structured logging (JSON) and correlation/request IDs
- Multi-location inventory (track stock per warehouse/location)
- Report endpoints (e.g., inventory valuation, transaction summaries)

---

## References

- Flask: https://flask.palletsprojects.com
- Flasgger (Swagger UI): https://github.com/flasgger/flasgger
- SQLAlchemy ORM: https://docs.sqlalchemy.org/en/20/orm/
- Alembic (migrations): https://alembic.sqlalchemy.org
- Marshmallow: https://marshmallow.readthedocs.io
- Decimal (Python money): https://docs.python.org/3/library/decimal.html
- Many-to-many in SQLAlchemy: https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html#many-to-many
- ISBN validation:
  - ISBN-10: https://en.wikipedia.org/wiki/International_Standard_Book_Number#ISBN-10_check_digits
  - ISBN-13: https://en.wikipedia.org/wiki/International_Standard_Book_Number#ISBN-13_check_digit_calculation

---

If you have questions or want to propose changes, open an issue or PR. Happy building!