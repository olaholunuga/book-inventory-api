from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    Table,
    Date,
    Numeric,
    Text,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from models.base_model import BaseModel, Base

# Association tables (UUID String(36) FKs) with CASCADE so join rows clean up when parent is deleted
book_authors = Table(
    "book_authors",
    Base.metadata,
    Column("book_id", String(36), ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", String(36), ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
)

book_categories = Table(
    "book_categories",
    Base.metadata,
    Column("book_id", String(36), ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("category_id", String(36), ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
)


class Book(BaseModel, Base):
    __tablename__ = "books"

    title = Column(String(255), nullable=False)
    # Store normalized digits-only; uniqueness enforced here
    isbn = Column(String(13), nullable=False, unique=True, index=True)
    published_date = Column(Date, nullable=True)  # validated not in future (in schema)
    pages = Column(Integer, nullable=True)  # validated >= 1 if provided (in schema)
    quantity = Column(Integer, nullable=False, default=0)  # validated >= 0
    price = Column(Numeric(10, 2), nullable=True)  # validated >= 0 if provided
    description = Column(Text, nullable=True)

    # Publisher: RESTRICT deletion if books reference it
    publisher_id = Column(String(36), ForeignKey("publishers.id", ondelete="RESTRICT"), nullable=True)

    # Relationships
    authors = relationship("Author", secondary=book_authors, back_populates="books")
    categories = relationship("Category", secondary=book_categories, back_populates="books")
    publisher = relationship("Publisher", back_populates="books")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_books_quantity_nonnegative"),
        CheckConstraint("(pages IS NULL) OR (pages >= 1)", name="ck_books_pages_positive"),
        CheckConstraint("(price IS NULL) OR (price >= 0)", name="ck_books_price_nonnegative"),
        Index("ix_books_title", "title"),
    )