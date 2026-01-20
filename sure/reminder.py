import logging
from datetime import datetime, timedelta

from django.utils import timezone
from django.utils.translation import activate

from sms.service import send_sms
from sure.models import Visit
from texts.translate import translate

logger = logging.getLogger(__name__)

REMINDER_QUESTION_LABEL = "REMINDER"


def parse_duration_string(duration_str: str) -> timedelta:
    # 2 weeks, 3 days, 4 hours, 5 minutes, 1 month, 1 year, 12 months
    number, unit = duration_str.strip().split(" ", 1)
    if not number.isdigit():
        raise ValueError(f"Invalid duration string: {duration_str}")
    number = int(number)

    if unit.startswith("week"):
        return timedelta(weeks=number)
    if unit.startswith("day"):
        return timedelta(days=number)
    if unit.startswith("month"):
        return timedelta(weeks=number * 4)
    if unit.startswith("year"):
        return timedelta(weeks=number * 52)

    raise ValueError(f"Invalid duration string: {duration_str}")


def get_reminder_date(visit: Visit) -> datetime | None:
    """Get the reminder date for the given visit."""
    # Find the latest answer to the REMINDER question
    reminder_answer = (
        visit.consultant_answers.filter(question__code=REMINDER_QUESTION_LABEL)
        .order_by("-created_at")
        .first()
    )

    if not reminder_answer:
        return None

    if len(reminder_answer.choices) != 1:
        return None

    choice = reminder_answer.choices[0]
    option = reminder_answer.question.options.filter(code=choice).first()

    if not option:
        return None

    try:
        duration = parse_duration_string(option.text_en)
    except ValueError:
        logger.warning(
            f"Invalid duration string for reminder option {option.id}: {option.text_en}"
        )
        return None

    return reminder_answer.created_at + duration


def send_reminder(visit: Visit):
    activate(visit.case.language)
    base_text = translate("reminder-notification")
    location_text = visit.case.location.reminder_text

    phone_number = visit.case.connection.client.contact.phone_number

    message = f"{base_text}\n{location_text}" if location_text else base_text

    send_sms(phone_number, message, visit.case.location.tenant)


def find_visits_for_reminders():
    """Find all visits that do not have reminders sent yet and are not marked as no reminder."""

    return Visit.objects.filter(
        no_reminder=False,
        reminder_sent_at__isnull=True,
        case__connection__isnull=False,
    )


def send_reminders():
    visits = find_visits_for_reminders()
    total = len(visits)
    sent = 0

    for visit in visits:
        reminder_date = get_reminder_date(visit)
        if reminder_date is None:
            visit.no_reminder = True
            visit.save()
            continue
        if reminder_date <= timezone.now():
            send_reminder(visit)
            visit.reminder_sent_at = timezone.now()
            visit.save()
            sent += 1
    return sent, total
