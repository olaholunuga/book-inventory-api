"""
Environment-aware configuration.
We keep it minimal in Step 1: security key, CORS, and env flags.
Database URL is handled by your DBStorage for now; we'll align in Step 2.
"""
import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()  # Read .env if present


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")  # Set a strong key in production
    DEBUG = False
    TESTING = False
    # CORS: in dev we usually allow '*', in prod supply a comma-separated list in env
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    # Keep a copy of env for visibility
    APP_ENV = os.getenv("APP_ENV", "dev")
    # Added jwt configurations
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv("JWT_TOKEN_EXPIRES_SECONDS", "1209600")))
    ALLOWED_ROLES = os.getenv("ALLOWED_ROLES", "admin,author,user").split(",")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    # In dev, propagate exceptions so our error handler has full context
    PROPAGATE_EXCEPTIONS = True


class ProductionConfig(BaseConfig):
    DEBUG = False


def get_config(name: str | None):
    """
    Select config class.
    - If name is provided, choose by name.
    - Else choose based on APP_ENV (dev/prod).
    """
    if name:
        name = name.lower()
    env = (name or os.getenv("APP_ENV", "dev")).lower()
    if env in ["prod", "production"]:
        return ProductionConfig
    return DevelopmentConfig