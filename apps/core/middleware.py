import logging

from django.conf import settings
from django.core.exceptions import RequestDataTooBig


logger = logging.getLogger(__name__)


class UploadLimitLoggingMiddleware:
    """Log an explicit warning when Django rejects an oversized request body."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except RequestDataTooBig:
            logger.warning(
                "Upload rejected by Django limit: path=%s method=%s content_length=%s limit_bytes=%s",
                request.path,
                request.method,
                request.META.get("CONTENT_LENGTH", "unknown"),
                settings.DATA_UPLOAD_MAX_MEMORY_SIZE,
            )
            raise
