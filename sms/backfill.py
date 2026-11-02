"""Attributes SMS sent before category and location were recorded.

The log only kept the time, the tenant and the last four digits of the
number. Every SMS is sent right after something that left its own record, so
those records are matched to the log by time:

- verification codes: the Token, created just before its SMS
- reminders: Visit.reminder_sent_at, set right after the SMS
- results links: the "Results published to client" log entry
- questionnaire links: the "Case created" log entry

The first three also know the client's number, so its last four digits have
to match as well. A questionnaire link only has the time to go on, which is
why it is matched last, against what the others left over, and only shortly
after the case was created.
"""

import bisect
from dataclasses import dataclass
from datetime import datetime, timedelta

from sms.models import SMSCategory, SMSMessage
from sure.models import Token, Visit, VisitLog
from tenants.models import Location

#: Sending retries three times with a ten second timeout each.
MATCH_WINDOW = timedelta(seconds=60)
#: Only the time links a questionnaire link to its case, so keep it tight.
CASE_LINK_WINDOW = timedelta(seconds=20)


@dataclass
class Event:
    at: datetime
    category: SMSCategory
    location: Location
    #: Last four digits of the number the SMS went to, if known.
    last_digits: str | None
    window: timedelta = MATCH_WINDOW


def _last_digits(phone_number: str | None) -> str | None:
    return phone_number[-4:] if phone_number else None


def _client_number(visit: Visit) -> str | None:
    connection = getattr(visit.case, "connection", None)
    return connection.client.contact.phone_number if connection else None


def _events() -> list[Event]:
    """The strongly identified events first, questionnaire links last."""
    events = []

    for token in Token.objects.select_related("contact", "case__location__tenant"):
        events.append(
            Event(
                token.created_at,
                SMSCategory.VERIFICATION_CODE,
                token.case.location,
                _last_digits(token.contact.phone_number),
            )
        )

    reminded = Visit.objects.filter(reminder_sent_at__isnull=False).select_related(
        "case__location__tenant", "case__connection__client__contact"
    )
    for visit in reminded:
        events.append(
            Event(
                visit.reminder_sent_at,
                SMSCategory.REMINDER,
                visit.case.location,
                _last_digits(_client_number(visit)),
            )
        )

    logs = VisitLog.objects.select_related(
        "visit__case__location__tenant", "visit__case__connection__client__contact"
    )
    for log in logs.filter(action="Results published to client"):
        events.append(
            Event(
                log.timestamp,
                SMSCategory.RESULTS_LINK,
                log.visit.case.location,
                _last_digits(_client_number(log.visit)),
            )
        )

    for log in logs.filter(action="Case created"):
        events.append(
            Event(
                log.timestamp,
                SMSCategory.CASE_LINK,
                log.visit.case.location,
                None,
                CASE_LINK_WINDOW,
            )
        )

    return events


def attribute_sms(messages: list[SMSMessage], events: list[Event]) -> dict:
    """Matches events to messages, closest in time first.

    Each message is used at most once. Returns the matches as
    ``{message: event}`` without saving anything.
    """
    messages = sorted(messages, key=lambda message: message.sent_at)
    times = [message.sent_at for message in messages]
    matched: dict[SMSMessage, Event] = {}

    for event in events:
        start = bisect.bisect_left(times, event.at - event.window)
        end = bisect.bisect_right(times, event.at + event.window)
        candidates = [
            message
            for message in messages[start:end]
            if message not in matched
            and message.tenant_id in (None, event.location.tenant_id)  # ty:ignore[unresolved-attribute]
            and (event.last_digits is None or message.to[-4:] == event.last_digits)
        ]
        if candidates:
            closest = min(candidates, key=lambda m: abs(m.sent_at - event.at))
            matched[closest] = event

    return matched


def backfill(dry_run: bool = False) -> dict[str, int]:
    """Fills in category and location of unattributed messages.

    Returns how many messages were attributed per category, and how many
    stayed unknown.
    """
    messages = list(SMSMessage.objects.filter(category=""))
    matched = attribute_sms(messages, _events())

    counts = {str(category.label): 0 for category in SMSCategory}
    for message, event in matched.items():
        counts[str(event.category.label)] += 1
        if dry_run:
            continue
        message.category = event.category
        message.location = event.location
        message.tenant_id = event.location.tenant_id
        # save() would mask the already masked number again, which is
        # harmless, but update() keeps sent_at and the number untouched.
        SMSMessage.objects.filter(pk=message.pk).update(
            category=message.category,
            location=message.location,
            tenant_id=message.tenant_id,
        )

    counts["Unknown"] = len(messages) - len(matched)
    return counts
