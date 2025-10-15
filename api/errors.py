"""
Centralized error handling that returns your standard error envelope:
{ "error": "<CODE>", "message": "<human readable>", "details": { ... }, "status": <http status int> }
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException
from marshmallow import ValidationError


def error_response(error: str, message: str, status: int, details: dict | None = None):
    payload = {"error": error, "message": message, "status": status}
    if details:
        payload["details"] = details
    return jsonify(payload), status


def register_error_handlers(app):
    # 400 Bad Request (generic)
    @app.errorhandler(400)
    def bad_request(e):
        message = getattr(e, "description", "Bad request")
        return error_response("BAD_REQUEST", message, 400)

    # 404 Not Found
    @app.errorhandler(404)
    def not_found(e):
        return error_response("NOT_FOUND", "Resource not found", 404)

    # 409 Conflict
    @app.errorhandler(409)
    def conflict(e):
        message = getattr(e, "description", "Conflict")
        return error_response("CONFLICT", message, 409)

    # 422 Unprocessable Entity (validation)
    @app.errorhandler(422)
    def unprocessable(e):
        message = getattr(e, "description", "Unprocessable entity")
        return error_response("VALIDATION_ERROR", message, 422)

    # Marshmallow validation errors map to 422
    @app.errorhandler(ValidationError)
    def handle_validation_error(err: ValidationError):
        # err.messages contains field-level details
        return error_response("VALIDATION_ERROR", "Invalid input", 422, details=err.messages)

    # Werkzeug HTTPExceptions map to their status codes
    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        return error_response("BAD_REQUEST", err.description, err.code or 400)

    # 500 Internal Error (catch-all)
    @app.errorhandler(Exception)
    def internal_error(err: Exception):
        # In production you would log the exception with stack trace here
        return error_response("INTERNAL_ERROR", "An unexpected error occurred", 500)