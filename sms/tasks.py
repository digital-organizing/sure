from celery import shared_task

from sms.service import send_sms
from tenants.models import Tenant


@shared_task
def schedule_sms_sending(to_number: str, message: str, tenant_id: int):
    tenant = Tenant.objects.get(id=tenant_id)
    send_sms(
        to=to_number,
        body=message,
        tenant=tenant,
    )
