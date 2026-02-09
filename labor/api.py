import logging

from ninja import Router

from labor.schema import LabOrderSchema, LaboratorySchema, PatientDataSchema
from labor.service import generate_hl7_order
from sure.client_service import get_case

from labor.models import LabOrder, LocationToLab, OrderStatus

logger = logging.getLogger(__name__)


router = Router()


@router.get("/{case_id}/laboratory", response={200: LaboratorySchema, 404: dict})
def get_laboratory(request, case_id: str):
    visit = get_case(request, case_id)
    laboratory = LocationToLab.objects.filter(location=visit.case.location).first()

    if not laboratory:
        return 404, {"error": "No laboratory configured for this location"}

    return laboratory.labor


@router.post("/{case_id}/generate_order", response={200: LabOrderSchema, 400: dict})
def generate_order(request, case_id: str, patient_data: PatientDataSchema):
    visit = get_case(request, case_id)

    try:
        order = generate_hl7_order(visit, patient_data)
        order.save()
        return order

    except ValueError as e:
        return 400, {"error": str(e)}


@router.post(
    "/{case_id}/{order_number}/cancel", response={200: list[LabOrderSchema], 400: dict}
)
def cancel_order(request, case_id: str, order_number: str):
    visit = get_case(request, case_id)

    try:
        lab_order = LabOrder.objects.get(order_number=order_number, visit=visit)
    except LabOrder.DoesNotExist:
        return 400, {"error": "Lab order not found"}

    if lab_order.status != OrderStatus.GENERATED:
        return 400, {"error": "Only generated orders can be cancelled"}

    lab_order.status = OrderStatus.CANCELLED
    lab_order._history_user = request.user  # type: ignore
    lab_order.save()

    orders = LabOrder.objects.filter(visit=visit).order_by("-created_at")
    return orders


@router.get("/{case_id}/lab_orders", response=list[LabOrderSchema])
def list_lab_orders(request, case_id: str):
    visit = get_case(request, case_id)
    orders = LabOrder.objects.filter(visit=visit).order_by("-created_at")
    return orders
