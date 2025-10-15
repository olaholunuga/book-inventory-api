from marshmallow import Schema, fields, validates, ValidationError


class PublisherCreateSchema(Schema):
    name = fields.String(required=True, validate=lambda s: len(s.strip()) > 0 and len(s) <= 128)


class PublisherUpdateSchema(Schema):
    name = fields.String(validate=lambda s: len(s.strip()) > 0 and len(s) <= 128)


class PublisherOutSchema(Schema):
    id = fields.String()
    name = fields.String()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()