import io
from datetime import timedelta
import time

import polars as pl
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.utils import timezone

from sure.cases import get_export_dict
from sure.export import generate_pdfs
from sure.models import Questionnaire
from sure.reminder import send_reminders

from .models import ExportStatus, Visit, VisitExport, VisitStatus


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


@shared_task
def close_seen_task():
    timestamp = timezone.now() - timedelta(days=7)
    counter = 0
    for visit in Visit.objects.filter(
        status=VisitStatus.RESULTS_SEEN, published_at__lt=timestamp
    ):
        visit.status = VisitStatus.CLOSED
        visit.save(update_fields=["status"])
        counter += 1

    return f"Closed {counter} visits from RESULTS_SEEN to CLOSED."


@shared_task
def create_export(export_id: int) -> None:

    export = VisitExport.objects.filter(id=export_id).first()
    if not export:
        time.sleep(5)  # Wait for the export to be created
        export = VisitExport.objects.filter(id=export_id).get()

    queryset = Visit.objects.filter(
        created_at__date__gte=export.start_date,
        created_at__date__lte=export.end_date,
    )

    if not export.user.is_superuser:
        tenant = export.user.consultant.tenant
        queryset = queryset.filter(case__location__tenant=tenant)

    export.status = ExportStatus.IN_PROGRESS
    export.total_visits = queryset.count()
    export.save(update_fields=["status", "total_visits"])

    records = []

    for visit in queryset:
        records.append(get_export_dict(visit))
        export.progress = int(len(records) / export.total_visits * 100)
        export.save(update_fields=["progress"])

    df = pl.DataFrame(records)
    # Store the dataframe as excel in export.file

    # Store the dataframe as excel in export.file
    buffer = io.BytesIO()
    df.write_excel(buffer)
    buffer.seek(0)

    filename = f"visit_export_{export.start_date}_{export.end_date}.xlsx"
    export.file.save(filename, ContentFile(buffer.read()), save=True)
    export.status = ExportStatus.COMPLETED
    export.save(update_fields=["status"])

    if export.user.email:
        send_mail(
            subject="[SURE] Export is ready",
            message=f"Your visit export from {export.start_date} to {export.end_date} is ready for download in the admin interface.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[export.user.email],
        )


@shared_task
def send_reminder_task() -> str:
    sent, total = send_reminders()

    return f"Sent {sent} reminders out of {total} visits."


@shared_task
def generate_pdf_task(questionnaire_id: int) -> None:
    questionnaire = Questionnaire.objects.get(id=questionnaire_id)
    generate_pdfs(questionnaire)
