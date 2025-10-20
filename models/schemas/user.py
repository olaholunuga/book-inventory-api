from marshmallow import Schema, fields

class UserCreateSchema(Schema):
    name = fields.String()