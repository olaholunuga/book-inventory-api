from models.base_model import Base, BaseModel
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship


class User(BaseModel, Base):
    __tablename__ = "user"
    f_name = Column(String(255), nullable=True)
    l_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(100), nullable=False)
    admin = Column(Boolean, default=False)

    author = relationship(
        "Author",
        back_populates="user",
        uselist=False,
        passive_deletes=True
    )