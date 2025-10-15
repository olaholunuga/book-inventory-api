from sqlalchemy.orm import relationship
from sqlalchemy import Column, String

from models.base_model import BaseModel, Base, SoftDeleteMixin
from models.book import book_authors


class Author(SoftDeleteMixin, BaseModel, Base):
    __tablename__ = "authors"

    name = Column(String(128), nullable=False)  # not unique; validate non-empty in schema

    books = relationship("Book", secondary=book_authors, back_populates="authors")