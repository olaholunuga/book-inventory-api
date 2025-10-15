from enum import Enum

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import Enum as SAEnum

from models.base_model import BaseModel, Base


class InventoryReason(str, Enum):
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    RETURN = "RETURN"
    ADJUSTMENT = "ADJUSTMENT"


class InventoryTransaction(BaseModel, Base):
    __tablename__ = "inventory_transactions"

    book_id = Column(String(36), ForeignKey("books.id", ondelete="RESTRICT"), nullable=False)
    delta_quantity = Column(Integer, nullable=False)  # positive or negative, but not zero
    reason = Column(SAEnum(InventoryReason, name="inventory_reason", native_enum=False), nullable=False)
    note = Column(String(255), nullable=True)
    # Snapshot after applying delta (enforced in service layer when we implement endpoints)
    resulting_quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    book = relationship("Book", backref="inventory_transactions")

    __table_args__ = (
        CheckConstraint("delta_quantity <> 0", name="ck_inv_delta_nonzero"),
        CheckConstraint("resulting_quantity >= 0", name="ck_inv_resulting_nonnegative"),
    )