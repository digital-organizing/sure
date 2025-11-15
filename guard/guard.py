import datetime
import logging
import re

from django.db.models import Q
from django.utils import timezone

from .models import BlockedEndpointHit, BlockedIdentifier, ProtectedEndpoint

logger = logging.getLogger(__name__)


def check_blocked(identifier: str) -> bool:
    """Check if the identifier is currently blocked"""
    return (
        BlockedIdentifier.objects.filter(
            identifier=identifier,
        )
        .filter(Q(disabled_at__isnull=True) | Q(disabled_at__gt=timezone.now()))
        .exists()
    )


def check_hit(request, response):
    """Check's if the request should be tracked for rate limiting.

    Returns the endpoint if it should be tracked, None otherwise"""
    endpoints = ProtectedEndpoint.objects.filter(status_code=response.status_code)

    if not endpoints.exists():
        return None

    for endpoint in endpoints:
        logger.info(
            "Checking endpoint %s against request path %s", endpoint, request.path
        )

        if endpoint.path_matcher and re.match(endpoint.path_matcher, request.path):
            logger.info("Matched path matcher for endpoint %s", endpoint)
            return endpoint

    return None


def track_hit(identifier: str, endpoint: ProtectedEndpoint):
    """Track hits for the given identifier and endpoint"""

    BlockedEndpointHit.objects.create(
        endpoint=endpoint,
        identifier=identifier,
    )


def check_block(identifier: str, endpoint: ProtectedEndpoint):
    """Check whether the identifier has exceeded max errors"""
    now = timezone.now()

    # Count hits in the defined window
    window_start = now - datetime.timedelta(seconds=endpoint.window)
    hit_count = BlockedEndpointHit.objects.filter(
        endpoint=endpoint,
        identifier=identifier,
        hit_at__gte=window_start,
    ).count()

    if hit_count >= endpoint.max_errors:
        return True
    return False


def block_identifier(identifier: str, endpoint: ProtectedEndpoint):
    block_until = (
        timezone.now() + datetime.timedelta(seconds=endpoint.block_duration)
        if endpoint.block_duration > 0
        else None
    )

    BlockedIdentifier.objects.create(
        identifier=identifier,
        reason=endpoint,
        disabled_at=block_until,
    )


def get_identifier(request) -> str:
    """Get user identifier - prioritize user ID over IP"""
    if request.user.is_authenticated:
        return f"user:{request.user.id}"

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    ip = (
        x_forwarded_for.split(",")[0].strip()
        if x_forwarded_for
        else request.META.get("REMOTE_ADDR")
    )

    return f"ip:{ip}"
