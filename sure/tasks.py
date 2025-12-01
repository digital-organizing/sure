from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import Visit, VisitStatus


@shared_task
def example_task(x, y):
    return x + y


@shared_task
def reset_unseen_task():
    timestamp = timezone.now() - timedelta(days=7)
    counter = 0
    for visit in Visit.objects.filter(
        status=VisitStatus.RESULTS_SENT, published_at__lt=timestamp
    ):
        visit.status = VisitStatus.RESULTS_MISSED
        visit.published_at = None
        visit.save(update_fields=["status", "published_at"])
        counter += 1

    return f"Reset {counter} visits from RESULTS_SENT to RESULTS_MISSED."
