from models.base_model import Base, BaseModel
from sqlalchemy import Column, String, JSON, text
from sqlalchemy.orm import relationship


class User(BaseModel, Base):
    __tablename__ = "users"
    f_name = Column(String(255), nullable=True)
    l_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(100), nullable=False)
    roles = Column(JSON, nullable=True, default=lambda: ['user'])

    author = relationship(
        "Author",
        back_populates="user",
        uselist=False,
        passive_deletes=True
    )

    @property
    def password(self):
        raise AttributeError("Password: Write-only field")