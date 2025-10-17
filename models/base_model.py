#!/usr/bin/env python3
"""
Shared SQLAlchemy base and mixins for the Book Inventory API.

Goals (aligned with your original BaseModel, but modernized):
- UUID primary key (String(36)) with defaults
- created_at / updated_at timestamps
- save() and delete() that use your existing DBStorage
- to_dict() that formats timestamps, removes SA internals, adds __class__
- SoftDeleteMixin that overrides delete() for soft-deletable models

Notes:
- We use server-side defaults (func.now()) so timestamps are set consistently by the DB.
- For SQLite, func.now() maps to CURRENT_TIMESTAMP.
- SoftDelete: put mixin FIRST in your model's inheritance list to override BaseModel.delete via MRO.
  Example:
    class Author(SoftDeleteMixin, BaseModel, Base): ...
"""

from __future__ import annotations

from datetime import datetime
import uuid

# Importing 'models' gives access to the global 'storage' instance (DBStorage)
# defined in models/__init__.py, matching your existing pattern.
import models

from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

TIME_FMT = "%Y-%m-%dT%H:%M:%S.%f"

# Declarative base for all models
Base = declarative_base()


def _uuid_str() -> str:
    """Return a canonical UUIDv4 string (36 chars, with hyphens)."""
    return str(uuid.uuid4())


class BaseModel:
    """
    Base mixin for all persistent models.

    Features retained from your original:
    - id, created_at, updated_at
    - save(), delete() wired to DBStorage
    - to_dict() with __class__ and timestamp formatting

    Improvements:
    - UUID String(36) primary key (consistent with your project decisions)
    - Server-side defaults for timestamps (func.now()), with onupdate for updated_at
    """

    id = Column(String(36), primary_key=True, default=_uuid_str, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __init__(self, *args, **kwargs):
        """
        Allow attribute initialization via kwargs without requiring a session here.
        We do NOT force created_at/updated_at in __init__; DB defaults handle those on insert.
        If you pass created_at/updated_at explicitly (e.g., in tests), they will be set.
        """
        for key, value in kwargs.items():
            if key != "__class__":
                setattr(self, key, value)
        # Ensure an id exists if user passed none
        if getattr(self, "id", None) is None:
            self.id = _uuid_str()

    def __str__(self) -> str:
        """Human-friendly representation including id and fields."""
        return f"[{self.__class__.__name__}] ({self.id}) {self.__dict__}"

    # Convenience persistence methods that use your DBStorage
    def save(self):
        """
        Update updated_at and persist the instance using your DBStorage.
        Enterprise note: in larger systems, you'd usually handle sessions/commits in a service layer.
        """
        # Let DB onupdate handle updated_at; setting here helps when the object isn't flushed yet.
        self.updated_at = datetime.utcnow()
        models.storage.new(self)
        models.storage.save()

    def delete(self):
        """
        Hard delete the current instance using your DBStorage.
        Soft-deletable models should inherit SoftDeleteMixin first to override this method.
        """
        models.storage.delete(self)
        # Intentionally not committing here; caller can decide when to commit.
        # If you prefer auto-commit on delete, uncomment the next line:
        # models.storage.save()

    def to_dict(self, save_fs=None) -> dict:
        """
        Return a dictionary of fields suitable for API responses:
        - Adds __class__ for compatibility with your original behavior
        - Formats created_at / updated_at to TIME_FMT if they are datetime objects
        - Removes SQLAlchemy internal state
        - Optionally removes sensitive fields (e.g., password) if present
        """
        d = {k: v for k, v in self.__dict__.items() if k != "_sa_instance_state"}
        if isinstance(d.get("created_at"), datetime):
            d["created_at"] = d["created_at"].strftime(TIME_FMT)
        if isinstance(d.get("updated_at"), datetime):
            d["updated_at"] = d["updated_at"].strftime(TIME_FMT)
        d["__class__"] = self.__class__.__name__

        if save_fs is None and "password" in d:
            del d["password"]

        return d


class SoftDeleteMixin:
    """
    Adds a deleted_at timestamp and overrides delete() to perform a soft delete.
    Use this for entities you want to "deactivate" while preserving history and relations.
    IMPORTANT: Place this mixin BEFORE BaseModel in your class base list so its delete() takes precedence.

    Example:
        class Category(SoftDeleteMixin, BaseModel, Base):
            __tablename__ = "categories"
            ...
    """

    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def restore(self):
        """restores an instance; sets delete_at to null and commits
        """
        self.deleted_at = None
        models.storage.new(self)
        models.storage.save()

    def soft_delete(self):
        """Explicit soft delete helper; sets deleted_at and commits."""
        self.deleted_at = datetime.utcnow()
        models.storage.new(self)
        models.storage.save()

    # Override BaseModel.delete for soft-deletable entities
    def delete(self):  # type: ignore[override]  # MRO override is intentional
        """Soft delete by setting deleted_at; persists via DBStorage."""
        self.soft_delete()