from models.base_model import BaseModel, Base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String
from models.book import book_categories

class Category(Base):
    __tablename__ = 'categories'
    name = Column(String)

    books = relationship(
        'Book',
        secondary=book_categories,
        back_populates='categories'
    )