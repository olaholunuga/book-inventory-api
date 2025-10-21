from marshmallow import Schema, fields

class UserCreateSchema(Schema):
    l_name = fields.String()
    f_name = fields.String()
    email = fields.String()
    password = fields.String()

class UserLoginSchema(Schema):
    email = fields.String()
    password = fields.String()

class UserUpdateSchema(Schema):
    f_name = fields.String(allow_none=True)
    l_name = fields.String(allow_none=True)
    email = fields.String(allow_none=True)
    password = fields.String(allow_none=True)

class UserOutSchema(Schema):
    f_name = fields.String(allow_none=True)
    l_name = fields.String(allow_none=True)
    email = fields.String(allow_none=True)
    admin = fields.Boolean()
    literary_name = fields.String(allow_none=True)