from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, ForeignKey

from models.base_model import BaseModel, Base, SoftDeleteMixin
from models.book import book_authors


class Author(SoftDeleteMixin, BaseModel, Base):
    __tablename__ = "authors"

    name = Column(String(128), nullable=False)  # not unique; validate non-empty in schema

    books = relationship("Book", secondary=book_authors, back_populates="authors")

    user_id = Column(
        String(128),
        ForeignKey("users.id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
        index=True
    )

    user = relationship("User", back_populates="author")