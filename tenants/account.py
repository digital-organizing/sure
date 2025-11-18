from urllib.parse import urlencode

from constance import config
from django.conf import settings
from django.template import Context, Template
from django.utils.safestring import mark_safe
from sesame.utils import get_parameters

from .tasks import send_background_mail


def send_reset_mail(request, consultant) -> None:
    """Send the invitation email to the consultant."""
    user = consultant.user
    param = get_parameters(user=user, scope=f"setup_account:{user.email}")
    param["email"] = user.email

    link = request.build_absolute_uri("/setup") + f"?{urlencode(param)}"

    template = Template(config.PASSWORD_RESET_EMAIL_TEMPLATE)
    context = Context(
        {
            "first_name": user.first_name,
            "tenant": consultant.tenant,
            "user": request.user,
            "activation_link": mark_safe(link),  # nosec
        }
    )
    message = template.render(context)
    subject = config.PASSWORD_RESET_EMAIL_SUBJECT

    send_background_mail.delay(
        {
            "subject": subject,
            "message": message,
            "from_email": settings.DEFAULT_FROM_EMAIL,
            "recipient_list": [user.email],
        }
    )


def send_2fa_reset_mail(request, user) -> None:
    """Send the 2FA reset email to the user."""

    template = Template(config.TWO_FA_RESET_EMAIL_TEMPLATE)
    context = Context(
        {
            "user": user,
            "admin": request.user,
        }
    )
    message = template.render(context)
    subject = config.TWO_FA_RESET_EMAIL_SUBJECT

    send_background_mail.delay(
        {
            "subject": subject,
            "message": message,
            "from_email": settings.DEFAULT_FROM_EMAIL,
            "recipient_list": [user.email],
        }
    )
