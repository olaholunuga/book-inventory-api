from models.base_model import BaseModel, Base
from sqlalchemy import Column, String, Integer, ForeignKey, Table, DateTime, Float
from sqlalchemy.orm import relationship
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from marshmallow import fields

book_authors = Table(
    "book_authors",
    Base.metadata,
    Column("book_id", ForeignKey("books.id"), primary_key=True),
    Column("author_id", ForeignKey("authors.id"), primary_key=True)
)

book_categories = Table(
    "book_categories",
    Base.metadata,
    Column("book_id", ForeignKey('books.id'), primary_key=True),
    Column("category_id", ForeignKey("categories.id"), primary_key=True)
)

class Book(BaseModel, Base):
    __tablename__ = "books"
    title = Column(String(128), nullable=False)
    isbn = Column(String(60), nullable=False)
    published_date = Column(DateTime, nullable=True)
    pages = Column(Integer)
    stock_count = Column(Integer)
    price = Column(Float)

    authors = relationship(
        "Author",
        secondary=book_authors,
        back_populates="books"
    )
    categories = relationship(
        "Categories",
        secondary=book_categories,
        back_populates="books"
    )
    publisher_id = Column(Integer, ForeignKey("publishers.id", ondelete="RESTRICT"), nullable=True)

    publisher = relationship("Publisher", back_populates="books")

class BookSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Book
        load_instance = True
        include_fk = True

    title = fields.String(required=True)
    isbn = fields.String(required=True)
    publisher_id = fields.Integer(required=False, allow_none=True)