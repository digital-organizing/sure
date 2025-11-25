import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from guard.models import BlockedIdentifier, ProtectedEndpoint

logger = logging.getLogger(__name__)


@shared_task
def send_block_notification_email(block_id: int):
    block = BlockedIdentifier.objects.get(pk=block_id)
    endpoint: ProtectedEndpoint = block.reason

    email = endpoint.notification_email

    if not email:
        logger.warning(
            "No notification email set for endpoint %s: %s, skipping notification.",
            endpoint.path_matcher,
            endpoint.status_code,
        )
        return

    send_mail(
        subject=f"[Alert] {block.identifier} blocked for endpoint {endpoint.path_matcher} ({endpoint.status_code})",
        message=(
            f"""The identifier {block.identifier} has been blocked until {block.disabled_at} for exceeding the allowed number of errors on the endpoint matching '{endpoint.path_matcher}' with status code {endpoint.status_code}.

{endpoint.description}

Please review the activity for this identifier. You can view and manage the block at {settings.SITE_URL}/admin/guard/blockedidentifier/{block.pk}/change/

To configure or disable notifications for this endpoint, edit the Protected Endpoint at {settings.SITE_URL}/admin/guard/protectedendpoint/{endpoint.pk}/change/"""
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )
