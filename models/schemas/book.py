from datetime import datetime
from marshmallow import Schema, fields, validates, validates_schema, ValidationError, post_load

from models.schemas.common import (
    validate_and_normalize_isbn,
    validate_not_future,
    to_decimal_2,
)


class BookBaseSchema(Schema):
    id = fields.String(dump_only=True)
    title = fields.String(required=True, validate=lambda s: 1 <= len(s) <= 255)
    isbn = fields.String(required=True)  # we will normalize/validate
    published_date = fields.Date(allow_none=True)
    pages = fields.Integer(allow_none=True)
    quantity = fields.Integer(load_default=0)
    price = fields.Decimal(as_string=True, allow_none=True)  # validate in custom fn
    description = fields.String(allow_none=True)
    publisher_id = fields.String(allow_none=True)
    # For later endpoints, we may accept/return id lists; here just placeholders for clarity
    author_ids = fields.List(fields.String(), load_only=True, required=False)
    category_ids = fields.List(fields.String(), load_only=True, required=False)

    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    @validates("published_date")
    def _validate_published_date(self, value, **kwargs):
        validate_not_future(value)

    @validates("pages")
    def _validate_pages(self, value, **kwargs):
        if value is not None and value < 1:
            raise ValidationError("pages must be >= 1.")

    @validates("quantity")
    def _validate_quantity(self, value, **kwargs):
        if value is not None and value < 0:
            raise ValidationError("quantity must be >= 0.")

    @validates("price")
    def _validate_price(self, value, **kwargs):
        # marshmallow passes strings here; use helper to validate and ensure >= 0
        if value is not None:
            to_decimal_2(value)

    @post_load
    def _normalize_isbn(self, data, **kwargs):
        # Replace input 'isbn' with normalized digits-only (or ISBN10 with X)
        if "isbn" in data:
            data["isbn"] = validate_and_normalize_isbn(data["isbn"])
        return data


class BookCreateSchema(BookBaseSchema):
    pass


class BookUpdateSchema(Schema):
    # All optional, but validate if present
    title = fields.String(validate=lambda s: 1 <= len(s) <= 255)
    isbn = fields.String()
    published_date = fields.Date()
    pages = fields.Integer()
    quantity = fields.Integer()
    price = fields.Decimal(as_string=True)
    description = fields.String()
    publisher_id = fields.String()
    author_ids = fields.List(fields.String(), load_only=True, required=False)
    category_ids = fields.List(fields.String(), load_only=True, required=False)

    @validates("published_date")
    def _validate_published_date(self, value, **kwargs):
        validate_not_future(value)

    @validates("pages")
    def _validate_pages(self, value, **kwargs):
        if value is not None and value < 1:
            raise ValidationError("pages must be >= 1.")

    @validates("quantity")
    def _validate_quantity(self, value, **kwargs):
        if value is not None and value < 0:
            raise ValidationError("quantity must be >= 0.")

    @validates("price")
    def _validate_price(self, value, **kwargs):
        if value is not None:
            to_decimal_2(value)

    @post_load
    def _normalize_isbn(self, data, **kwargs):
        if "isbn" in data:
            data["isbn"] = validate_and_normalize_isbn(data["isbn"])
        return data


class BookOutSchema(Schema):
    id = fields.String()
    title = fields.String()
    isbn = fields.String()  # already normalized in DB
    published_date = fields.Date(allow_none=True)
    pages = fields.Integer(allow_none=True)
    quantity = fields.Integer()
    price = fields.Decimal(as_string=True, allow_none=True)
    description = fields.String(allow_none=True)
    publisher_id = fields.String(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()
    # Expose IDs of related entities
    author_ids = fields.Method("get_author_ids")
    category_ids = fields.Method("get_category_ids")

    def get_author_ids(self, obj):
        try:
            return [a.id for a in getattr(obj, "authors", [])]
        except Exception:
            return []

    def get_category_ids(self, obj):
        try:
            return [c.id for c in getattr(obj, "categories", [])]
        except Exception:
            return []