from celery import shared_task

from django.utils import timezone

from .service import parse_hl7_to_db
from labor.models import (
    HL7Result,
    LabOrder,
    Laboratory,
    LocationToLab,
    OrderStatus,
    ImlementationChoices,
)
from .team_w import (
    upload_order as upload_order_team_w,
    retrieve_results as retrieve_results_team_w,
)

import logging

logger = logging.getLogger(__name__)


def process_order(order: LabOrder | int):
    if isinstance(order, int):
        order = LabOrder.objects.get(id=order)
    location = order.visit.case.location
    laboratory = LocationToLab.objects.filter(location=location).first()
    if not laboratory:
        order.status = OrderStatus.CANCELLED
        order.save()
        return

    match laboratory.labor.implementation:
        case ImlementationChoices.UNILABS:
            pass
        case ImlementationChoices.TEAM_W:
            upload_order_team_w(order.content, laboratory.labor)

    order.status = OrderStatus.SENT
    order.save()


@shared_task
def upload_orders_task():
    pending_orders = LabOrder.objects.filter(status=OrderStatus.GENERATED)
    for order in pending_orders:
        process_order(order)


@shared_task
def retrieve_results_task(lab_id: int):
    laboratory = Laboratory.objects.get(id=lab_id)
    match laboratory.implementation:
        case ImlementationChoices.UNILABS:
            pass
        case ImlementationChoices.TEAM_W:
            retrieve_results_team_w(laboratory)


@shared_task
def process_results():
    results = HL7Result.objects.filter(processed_at=None)

    for result in results:
        try:
            parse_hl7_to_db(result)
            result.processed_at = timezone.now()
            result.save(update_fields=["processed_at"])
        except Exception as e:
            result.logs += f"\nError: {e}"
            result.save(update_fields=["logs"])

            logging.error(f"Error processing HL7 result {result.pk}: {e}")
