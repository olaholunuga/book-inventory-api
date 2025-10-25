from datetime import datetime
from time import timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from models.base_model import BaseModel, Base
from sqlalchemy.sql import func

class BlacklistedToken(BaseModel, Base):
    __tablename__ = "blacklisted_tokens"

    jti = Column(String(64), primary_key=True, unique=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    revoked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    def __repr__(self):
        return f"<BlacklistedToken token={self.jti}>"