from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Integer
from models.book import book_authors
from models.base_model import BaseModel, Base
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import fields, validates, ValidationError


class Author(BaseModel, Base):
    __tablename__ = 'authors'
    name = Column(String)

    books = relationship(
        'Book',
        secondary=book_authors,
        back_populates='authors'
    )

class AuthorSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Author
        load_instance = True
        include_fk = True

    name = fields.String(required=True)
    books = fields.Nested("BookSchema", only=("id", "title"), many=True, dump_only=True)

    @validates("name")
    def validate_name(self, value):
        if not value.strip():
            raise ValidationError("Author name cannot be empty.")