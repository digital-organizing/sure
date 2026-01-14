import logging
from collections.abc import Callable

from django.http import JsonResponse

from .guard import (block_identifier, check_block, check_blocked, check_hit,
                    get_identifier, track_hit)

logger = logging.getLogger(__name__)


class NotFoundRateLimitMiddleware:
    """Middleware to block IPs/users after receiving too many 404s on API endpoints."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        identifier = get_identifier(request)

        if check_blocked(identifier):
            return JsonResponse(
                {"detail": "Too many invalid requests. Access blocked."}, status=429
            )

        response = self.get_response(request)

        if endpoint := check_hit(request, response):
            track_hit(identifier, endpoint)

            if check_block(identifier, endpoint):
                block_identifier(identifier, endpoint)

        return response
