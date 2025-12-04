from datetime import timedelta

from celery import shared_task
from constance import config
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template import Context, Template
from django.utils import timezone
from django_otp import devices_for_user


@shared_task
def send_background_mail(email_data):
    print("Sending email to:", email_data["recipient_list"])
    print("Subject:", email_data["subject"])
    print("Message:", email_data["message"])
    send_mail(
        email_data["subject"],
        email_data["message"],
        email_data.get("from_email", settings.DEFAULT_FROM_EMAIL),
        email_data["recipient_list"],
        fail_silently=False,
    )


@shared_task
def check_2fa_setup():
    for user in User.objects.all():
        devices = list(devices_for_user(user, confirmed=True))
        if len(devices) > 0:
            continue
        now = timezone.now()

        if user.date_joined < now - timedelta(days=7):
            user.is_active = False
            user.save()
        elif user.date_joined < now - timedelta(days=2):
            template = Template(config.TWO_FA_REMINDER_EMAIL_TEMPLATE)

            send_mail(
                config.TWO_FA_REMINDER_SUBJECT,
                template.render(
                    Context(
                        {
                            "user": user,
                            "deadline": (user.date_joined + timedelta(days=7)).date(),
                        }
                    )
                ),
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )


@shared_task
def deactivate_inactive_users():
    now = timezone.now()
    threshold_date = now - timedelta(days=6 * 30)
    inactive_users = User.objects.filter(is_active=True, last_login__lt=threshold_date)
    inactive_users.update(is_active=False)
