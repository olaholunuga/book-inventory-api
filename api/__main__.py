"""
Entrypoint for running the API in development.
Replaces Connexion with a pure Flask application created by create_app().
"""
import os
from . import create_app

# Respect FLASK_ENV/APP_ENV for configuration selection (handled in get_config())
app = create_app()

if __name__ == "__main__":
    # Dev-friendly defaults; in production you'd run via a WSGI server (gunicorn/uwsgi)
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", "8000"))
    debug = bool(os.getenv("FLASK_DEBUG", str(app.config.get("DEBUG", True))).lower() in ("1", "true", "yes"))
    app.run(host=host, port=port, debug=debug)