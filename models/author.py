from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Integer
from models.book import book_authors
from models.base_model import BaseModel, Base


class Author(BaseModel, Base):
    __tablename__ = 'authors'
    name = Column(String)

    books = relationship(
        'Book',
        secondary=book_authors,
        back_populates='authors'
    )