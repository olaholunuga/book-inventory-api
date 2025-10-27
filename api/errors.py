from flask import jsonify, current_app
from werkzeug.exceptions import HTTPException
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
import logging


def error_response(error: str, message: str, status: int, details: dict | None = None):
    payload = {"error": error, "message": message, "status": status}
    if details:
        payload["details"] = details
    return jsonify(payload), status


def register_error_handlers(app):
    # 400 Bad Request (generic)
    @app.errorhandler(400)
    def bad_request(e):
        if current_app and current_app.debug:
            logging.exception("Unhandled exception", exc_info=e)
        message = getattr(e, "description", "Bad request")
        return error_response("BAD_REQUEST", message, 400)

    # 404 Not Found
    @app.errorhandler(404)
    def not_found(e):
        if current_app and current_app.debug:
            logging.exception("Unhandled exception", exc_info=e)
        return error_response("NOT_FOUND", "Resource not found", 404)

    # 409 Conflict
    @app.errorhandler(409)
    def conflict(e):
        if current_app and current_app.debug:
            logging.exception("Unhandled exception", exc_info=e)
        message = getattr(e, "description", "Conflict")
        return error_response("CONFLICT", message, 409)

    # 422 Unprocessable Entity (validation)
    @app.errorhandler(422)
    def unprocessable(e):
        if current_app and current_app.debug:
            logging.exception("Unhandled exception", exc_info=e)
        message = getattr(e, "description", "Unprocessable entity")
        return error_response("VALIDATION_ERROR", message, 422)

    # Marshmallow validation errors map to 422
    @app.errorhandler(ValidationError)
    def handle_validation_error(err: ValidationError):
        # err.messages contains field-level details
        if current_app and current_app.debug:
            logging.exception("Unhandled exception", exc_info=err)
        return error_response("VALIDATION_ERROR", "Invalid input", 422, details=err.messages)

    # Integrity errors (unique constraints, FK violations, check constraints)
    @app.errorhandler(IntegrityError)
    def handle_integrity_error(err: IntegrityError):
        # Rollback is managed where the session is used, but this ensures a clean response
        message = str(getattr(err, "orig", err))
        lower_msg = message.lower()
        if current_app and current_app.debug:
            logging.exception("Unhandled exception", exc_info=err)
        # Heuristics: tailor the status
        if "unique constraint" in lower_msg or "unique violation" in lower_msg:
            return error_response("CONFLICT", "Unique constraint violated.", 409, details={"db_error": message})
        if "foreign key constraint" in lower_msg or "foreign key mismatch" in lower_msg:
            return error_response("BAD_REQUEST", "Foreign key constraint failed.", 400, details={"db_error": message})
        if "check constraint" in lower_msg or "constraint failed" in lower_msg:
            return error_response("BAD_REQUEST", "Check constraint failed.", 400, details={"db_error": message})
        # Generic integrity issue
        return error_response("BAD_REQUEST", "Integrity error.", 400, details={"db_error": message})

    # Werkzeug HTTPExceptions map to their status codes
    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        return error_response("BAD_REQUEST", err.description, err.code or 400)

    # 500 Internal Error (catch-all)
    @app.errorhandler(Exception)
    def internal_error(err: Exception):
        # In dev, include exception details to speed up debugging
        details = None
        if current_app and current_app.debug:
            logging.exception("Unhandled exception", exc_info=err)
            details = {"type": err.__class__.__name__, "message": str(err)}
        return error_response("INTERNAL_ERROR", "An unexpected error occurred", 500, details=details)

    # # 500 Internal Error (catch-all)
    # @app.errorhandler(Exception)
    # def internal_error(err: Exception):
    #     # In production you would log the exception with stack trace here
    #     return error_response("INTERNAL_ERROR", "An unexpected error occurred", 500)