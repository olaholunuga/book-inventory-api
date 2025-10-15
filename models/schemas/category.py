from marshmallow import Schema, fields, validates, ValidationError


class CategoryCreateSchema(Schema):
    name = fields.String(required=True, validate=lambda s: len(s.strip()) > 0 and len(s) <= 64)


class CategoryUpdateSchema(Schema):
    name = fields.String(validate=lambda s: len(s.strip()) > 0 and len(s) <= 64)


class CategoryOutSchema(Schema):
    id = fields.String()
    name = fields.String()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()