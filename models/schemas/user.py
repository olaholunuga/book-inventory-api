from marshmallow import Schema, fields, pre_load, validates, ValidationError

def _norm_email(v):
    return v.strip().lower() if isinstance(v, str) else v

class UserCreateSchema(Schema):
    f_name = fields.String(allow_none=True)
    l_name = fields.String(allow_none=True)
    email = fields.Email(required=True)
    password = fields.String(required=True, load_only=True)

    @pre_load
    def normalize(self, data, **kwargs):
        if isinstance(data, dict) and "email" in data:
            data["email"] = _norm_email(data["email"])
        return data

    @validates("password")
    def validate_password(self, value, **kwargs):
        if len(value) < 8:
            raise ValidationError("Password must be at least 8 characters long.")

class UserLoginSchema(Schema):
    email = fields.String()
    password = fields.String()

class UserUpdateSchema(Schema):
    f_name = fields.String(allow_none=True)
    l_name = fields.String(allow_none=True)
    email = fields.String(allow_none=True)
    password = fields.String(allow_none=True)

    @validates("password")
    def validate_password(self, value, **kwargs):
        if len(value) < 8:
            raise ValidationError("Password must be at least 8 characters long.")

class UserOutSchema(Schema):
    id = fields.String(allow_none=False)
    f_name = fields.String(allow_none=True)
    l_name = fields.String(allow_none=True)
    email = fields.String(allow_none=True)
    roles = fields.List(fields.String(allow_none=True))
    # author = fields.String()
    author_id = fields.Method("get_author_id")
    literary_name = fields.String(allow_none=True)

    def get_author_id(self, obj):
        try:
            return getattr(getattr(obj, "author", ""), "id", "")
        except Exception:
            return ""

class UserListOutSchema(Schema):
    id = fields.String(allow_none=False)
    f_name = fields.String(allow_none=True)
    l_name = fields.String(allow_none=True)
    email = fields.String(allow_none=False)
    roles = fields.List(fields.String(allow_none=True))
    author_id = fields.Method("get_author_id")
    literary_name = fields.String(allow_none=True)

    def get_author_id(self, obj):
        try:
            return getattr(getattr(obj, "author", ""), "id", "")
        except Exception:
            return ""