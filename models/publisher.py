from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Index

from models.base_model import BaseModel, Base, SoftDeleteMixin


class Publisher(SoftDeleteMixin, BaseModel, Base):
    __tablename__ = "publishers"

    name = Column(String(128), nullable=False, unique=True)

    # Do NOT cascade delete books. Book.publisher_id has ON DELETE RESTRICT.
    books = relationship("Book", back_populates="publisher")

    __table_args__ = (
        Index("ix_publishers_name", "name"),
    )