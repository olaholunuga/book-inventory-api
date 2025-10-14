from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from models.base_model import BaseModel, Base
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import fields, validates, ValidationError

class Publisher(BaseModel, Base):
    __tablename__ = "publishers"
    name = Column(String(128), nullable=False, unique=True)

    # Publisher has many books, but deleting publisher should not cascade delete books
    books = relationship("Book", back_populates="publisher", cascade="all, delete-orphan", passive_deletes=True)

class PublisherSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Publisher
        load_instance = True  # Enables deserialization to model
        include_fk = True     # To load publisher_id if needed

    name = fields.String(required=True, validate=lambda x: len(x) >= 2)

    @validates("name")
    def validate_name(self, value):
        if not value.strip():
            raise ValidationError("Publisher name cannot be empty.")