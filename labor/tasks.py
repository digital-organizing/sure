from celery import shared_task

from labor.models import LabOrder, LocationToLab, OrderStatus, ImlementationChoices
from .team_w import upload_order as upload_order_team_w




def process_order(order: LabOrder):
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
def retrieve_results_task():
    pass
