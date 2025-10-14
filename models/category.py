from models.base_model import BaseModel, Base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String
from models.book import book_categories
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import fields, validates, ValidationError

class Category(BaseModel, Base):
    __tablename__ = 'categories'
    name = Column(String)

    books = relationship(
        'Book',
        secondary=book_categories,
        back_populates='categories'
    )

class CategorySchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Category
        load_instance = True
        include_fk = True

    name = fields.String(required=True)
    books = fields.Nested("BookSchema", only=("id", "title"), many=True, dump_only=True)

    @validates("name")
    def validate_name(self, value):
        if not value.strip():
            raise ValidationError("Category name cannot be empty.")