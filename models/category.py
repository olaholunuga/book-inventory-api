from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Index

from models.base_model import BaseModel, Base, SoftDeleteMixin
from models.book import book_categories


class Category(SoftDeleteMixin, BaseModel, Base):
    __tablename__ = "categories"

    name = Column(String(64), nullable=False, unique=True)

    books = relationship("Book", secondary=book_categories, back_populates="categories")

    __table_args__ = (
        Index("ix_categories_name", "name"),
    )