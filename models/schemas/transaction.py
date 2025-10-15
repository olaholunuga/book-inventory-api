from marshmallow import Schema, fields, validates, ValidationError


class InventoryTransactionCreateSchema(Schema):
    book_id = fields.String(required=True)
    delta_quantity = fields.Integer(required=True)
    reason = fields.String(required=True)
    note = fields.String(required=False, allow_none=True, validate=lambda s: s is None or len(s) <= 255)

    @validates("delta_quantity")
    def _validate_delta(self, value):
        if value == 0:
            raise ValidationError("delta_quantity cannot be zero.")


class InventoryTransactionOutSchema(Schema):
    id = fields.String()
    book_id = fields.String()
    delta_quantity = fields.Integer()
    reason = fields.String()
    note = fields.String(allow_none=True)
    resulting_quantity = fields.Integer()
    created_at = fields.DateTime()