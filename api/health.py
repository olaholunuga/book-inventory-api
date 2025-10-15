from flask import Blueprint

bp = Blueprint("health", __name__)

@bp.get("/health")
def health():
    """
    Health check
    ---
    tags:
      - Health
    responses:
      200:
        description: API is up
        schema:
          type: object
          properties:
            status:
              type: string
              example: ok
            version:
              type: string
              example: 1.0.0
    """
    return {"status": "ok", "version": "1.0.0"}, 200