from flask import Flask
from flasgger import Swagger
from flask_cors import CORS
import os
from argon2 import PasswordHasher

from .config import get_config
from .errors import register_error_handlers
from models import storage  # DBStorage singleton (scoped_session) you already have

# Minimal Swagger config: exposes /swagger.json and UI at /apidocs
SWAGGER_TEMPLATE = {
    "swagger": "2.0.0",
    "info": {
        "title": "Book Inventory API",
        "version": "1.0.0",
        "description": "REST API for managing books, authors, categories, publishers, and inventory transactions.",
    },
    "basePath": "/",  # We'll mount blueprints under /api/v1
    "schemes": ["http"],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Enter the token with the `Bearer ` prefix, e.g. \"Bearer abcde12345\"."
        }
    }
}

SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec_1",
            "route": "/swagger.json",
            "rule_filter": lambda rule: True,   # include all endpoints
            "model_filter": lambda tag: True,   # include all models
        }
        # You can add more specs for versioning, if needed
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
}

ph = PasswordHasher()


def create_app(config_name: str | None = None) -> Flask:
    """
    Application factory: creates and configures the Flask app.
    Why use this?
      - Easier testing (create an isolated app per test)
      - Clear environment-based configuration
      - Clean dependency injection for extensions like Swagger, CORS, DB
    """
    app = Flask(__name__)

    # Load configuration (reads .env via get_config)
    app.config.from_object(get_config(config_name))

    # Cross-Origin Resource Sharing: enable for dev, configurable for prod
    CORS(app, resources={r"/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})

    # Swagger UI and JSON
    Swagger(app, template=SWAGGER_TEMPLATE, config=SWAGGER_CONFIG)

    # Register global error handlers that return your uniform error envelope
    register_error_handlers(app)

    # Register blueprints (only 'health' for Step 1)
    from .health import bp as health_bp
    from .books import bp as books_bp
    from .transactions import bp as tx_bp
    from .authors import bp as authors_bp
    from .categories import bp as categories_bp
    from .publishers import bp as publishers_bp
    from .auth import bp as auth_bp
    from .users import bp as users_bp

    app.register_blueprint(health_bp, url_prefix="/api/v1")
    app.register_blueprint(books_bp, url_prefix="/api/v1")
    app.register_blueprint(tx_bp, url_prefix="/api/v1/")
    app.register_blueprint(authors_bp, url_prefix="/api/v1/")
    app.register_blueprint(categories_bp, url_prefix="/api/v1/")
    app.register_blueprint(publishers_bp, url_prefix="/api/v1/")
    app.register_blueprint(auth_bp, url_prefix="/api/v1/")
    app.register_blueprint(users_bp,url_prefix="/api/v1/")
    # Ensure the DB session is removed at the end of each request/app context
    @app.teardown_appcontext
    def remove_session(exception=None):
        # Using your existing DBStorage helper
        # This calls scoped_session.remove(), preventing connection leaks
        storage.close()

    # Optionally expose a root route to redirect to docs or show a friendly message
    @app.route("/")
    def root():
        return {
            "message": "Welcome to Book Inventory API",
            "docs": "/apidocs/",
            "health": "/api/v1/health",
        }, 200

    return app