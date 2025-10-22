"""
RefreshToken model: stores refresh tokens JTIs so we can revoke and rotate refresh tokens
Fields:
- jti (primary key)
- user_id (String(36)) - FK to users.id
- revoked (bool)
- created_at, expires_at
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from models.base_model import BaseModel, Base

class RefreshToken(BaseModel, Base):
    __tablename__ = "refresh_tokens"

    jti = Column(String(64), primary_key=True, unique=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)