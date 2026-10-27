"""Central API error handling.

DRF already converts validation errors, 401/403/404, parse errors, etc. into
JSON. This handler adds safe JSON responses for database problems, without
leaking SQL, stack traces or other internals to the client.
"""
import logging

from django.db import DatabaseError, IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("healthcare")


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, IntegrityError):
        logger.warning("Integrity error in %s", context["view"].__class__.__name__, exc_info=exc)
        return Response(
            {"detail": "The request conflicts with existing data."},
            status=status.HTTP_409_CONFLICT,
        )

    if isinstance(exc, DatabaseError):
        logger.error("Database error in %s", context["view"].__class__.__name__, exc_info=exc)
        return Response(
            {"detail": "The service is temporarily unavailable. Please try again later."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # Anything else is unexpected: let Django log it and return its generic 500.
    return None
