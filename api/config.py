"""
Environment-aware configuration.
We keep it minimal in Step 1: security key, CORS, and env flags.
Database URL is handled by your DBStorage for now; we'll align in Step 2.
"""
import os
from dotenv import load_dotenv

load_dotenv()  # Read .env if present


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")  # Set a strong key in production
    DEBUG = False
    TESTING = False
    # CORS: in dev we usually allow '*', in prod supply a comma-separated list in env
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    # Keep a copy of env for visibility
    APP_ENV = os.getenv("APP_ENV", "dev")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


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