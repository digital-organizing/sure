from celery import shared_task

from sms.models import SMSCategory
from sms.service import send_sms
from tenants.models import Location


@shared_task
def schedule_sms_sending(to_number: str, message: str, location_id: int, category: str):
    send_sms(
        to=to_number,
        body=message,
        location=Location.objects.get(id=location_id),
        category=SMSCategory(category),
    )
