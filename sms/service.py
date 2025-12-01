from enum import Enum

import requests
from django.conf import settings

from sms.models import SMSMessage
from tenants.models import Tenant


class SMSUpStatus(Enum):
    OK = 1
    AUTH_ERROR = -1
    XML_ERROR = -2
    NOT_ENOUGH_CREDITS = -3
    INCORRECT_DATE_DELAY = -4
    RESOURCE_NOT_FOUND = -5
    JSON_ERROR = -6
    DATA_ERROR = -7
    MODERATION = -8
    UNKNOWN_ERROR = -99


def send_sms(to: str, body: str, tenant: Tenant) -> None:
    """Send an SMS message via SMS Up, uses settings from Django settings."""
    headers = {
        "Authorization": f"Bearer {settings.SMSUP_API_TOKEN}",
        "Accept": "application/json",
    }

    if to.startswith("+"):  # API requires no '+' sign
        to = to[1:]

    params = {
        "to": to,
        "text": body,
        "pushtype": "alert",
        "sender": "SURE",
    }

    if settings.SIMULATE_SMS:
        print(f"Simulating SMS send to {to}: {body}")

    response = requests.get(
        "https://api.smsup.ch/send/simulate"
        if settings.SIMULATE_SMS
        else "https://api.smsup.ch/send",
        headers=headers,
        params=params,
        timeout=10,
    )

    response.raise_for_status()
    data = response.json()
    status_code = data.get("status", SMSUpStatus.UNKNOWN_ERROR.value)

    if status_code not in [SMSUpStatus.OK.value, SMSUpStatus.MODERATION.value]:
        raise Exception(f"Failed to send SMS: {data}")

    if data.get("sent") != 1:
        raise Exception(f"SMS not sent: {data}")

    SMSMessage.objects.create(
        to=to,
        response=data,
        tenant=tenant,
    )
