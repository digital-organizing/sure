"""Implementation for sending SMS via Twilio."""

from django.conf import settings
from twilio.rest import Client as TwilioClient


def send_sms(to: str, body: str):
    """Send an SMS message via Twilio, uses settings from Django settings."""
    twilio_client = TwilioClient(
        settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
    )
    message = twilio_client.messages.create(
        body=body,
        from_=settings.TWILIO_PHONE_NUMBER,
        to=to,
    )
    return message.sid
