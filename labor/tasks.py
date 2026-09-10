import logging

from celery import shared_task
from django.utils import timezone

from labor.models import (
    HL7Result,
    ImlementationChoices,
    Laboratory,
    LabOrder,
    LocationToLab,
    OrderStatus,
)

from .service import parse_hl7_to_db
from .team_w import (
    retrieve_results as retrieve_results_team_w,
)
from .team_w import (
    upload_order as upload_order_team_w,
)

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
def upload_single_order(pk):
    order = LabOrder.objects.get(pk=pk)
    process_order(order)


@shared_task
def retrieve_results_task(lab_id: int):
    laboratory = Laboratory.objects.get(id=lab_id)
    match laboratory.implementation:
        case ImlementationChoices.UNILABS:
            pass
        case ImlementationChoices.TEAM_W:
            retrieve_results_team_w(laboratory)


#: A result that keeps failing is a permanent problem - a message we cannot
#: map, or one of our own orders the lab left in the results directory. Retrying
#: it forever grew ``logs`` without bound on every scheduled run, so give up
#: after this many attempts and let someone look at it in the admin.
MAX_PROCESSING_ATTEMPTS = 5


def _process_result(result: HL7Result) -> bool:
    """Processes one result, recording the failure on the row itself."""
    try:
        parse_hl7_to_db(result.content)
    except Exception as e:
        result.attempts += 1
        result.logs += f"\nAttempt {result.attempts}: {e}"
        if result.attempts >= MAX_PROCESSING_ATTEMPTS:
            result.logs += (
                f"\nGiving up after {MAX_PROCESSING_ATTEMPTS} attempts. "
                "Retry from the admin once the cause is fixed."
            )
        result.save(update_fields=["attempts", "logs"])

        logging.error(f"Error processing HL7 result {result.pk}: {e}")
        return False

    result.processed_at = timezone.now()
    result.save(update_fields=["processed_at"])
    return True


@shared_task
def process_results():
    results = HL7Result.objects.filter(
        processed_at=None, attempts__lt=MAX_PROCESSING_ATTEMPTS
    )

    for result in results:
        _process_result(result)


@shared_task
def process_single_result(pk):
    """Processes one result on demand, used by the admin retry action."""
    _process_result(HL7Result.objects.get(pk=pk))
