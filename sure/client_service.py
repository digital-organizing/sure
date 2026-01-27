"""Functions for creating and managing clients and their cases."""

import logging
from datetime import timedelta
from typing import Iterable

import phonenumbers
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

import tenants.models
from sms.service import send_sms
from sure.cases import annotate_last_modified
from sure.schema import AnswerSchema
from texts.translate import translate

from .models import (
    Case,
    Client,
    ClientAnswer,
    Connection,
    ConsentChoice,
    Contact,
    Questionnaire,
    Visit,
    VisitStatus,
)

logger = logging.getLogger(__name__)


def canonicalize_phone_number(phone_number: str) -> str:
    """Convert a phone number to E.164 format."""
    return phonenumbers.format_number(
        phonenumbers.parse(phone_number, settings.DEFAULT_REGION),
        phonenumbers.PhoneNumberFormat.E164,
    )


def human_format_phone_number(phone_number: str) -> str:
    """Convert a phone number to a human-readable format."""
    parsed = phonenumbers.parse(phone_number, settings.DEFAULT_REGION)
    if phonenumbers.region_code_for_number(parsed) != settings.DEFAULT_REGION:
        return phonenumbers.format_number(
            parsed,
            phonenumbers.PhoneNumberFormat.INTERNATIONAL,
        )

    return phonenumbers.format_number(
        parsed,
        phonenumbers.PhoneNumberFormat.NATIONAL,
    )


def verify_access_to_location(location: tenants.models.Location, user) -> bool:
    """Verify that the user has access to the given location."""
    if user.is_superuser:
        return True
    if not hasattr(user, "consultant"):
        return False
    consultant: tenants.models.Consultant = user.consultant
    return consultant.locations.filter(id=location.pk).exists()


def location_can_view_case(location_ids: Iterable[int], case: Case) -> bool:
    """Verify that the location has access to the given case."""
    if case.location.pk in location_ids:
        return True

    connection = Connection.objects.filter(case=case).first()

    if not connection:
        return False

    return connection.client.connections.filter(
        case__location_id__in=location_ids
    ).exists()


def create_case(
    location_id: int, user, external_id: str | None = None, language: str = "en"
) -> Case:
    """Create a new case at the given location."""
    location = get_object_or_404(tenants.models.Location, pk=location_id)
    if not verify_access_to_location(location, user):
        raise PermissionError("User does not have access to this location")
    case = Case.objects.create(
        location=location,
        external_id=external_id or "",
        language=language,
    )
    return case


def create_visit(case: Case, questionnaire: Questionnaire) -> Visit:
    """Create a new visit for the given case and questionnaire."""
    visit = Visit.objects.create(
        case=case,
        questionnaire=questionnaire,
        status=VisitStatus.CREATED,
    )
    return visit


def strip_id(human_id: str) -> str:
    """Strip the prefix from a human-readable ID."""
    if human_id.lower().startswith("suf-") or human_id.lower().startswith("suc-"):
        return human_id[4:]
    return human_id


def get_case_link(case: Case) -> str:
    """Get a link to access the case."""
    return settings.SITE_URL + "?case=" + case.human_id


def generate_token(phone_number: str, case: Case) -> tuple[Contact, str]:
    """Generate a token for the given phone number, creating a contact if necessary."""
    contact, _ = Contact.objects.get_or_create(
        phone_number=canonicalize_phone_number(phone_number),
        active=True,
    )
    token = contact.generate_token(case)
    return contact, token


def send_case_link(case: Case, phone_number: str):
    """Send a link to access the case to the given phone number."""
    contact, token = Contact.objects.get_or_create(
        phone_number=canonicalize_phone_number(phone_number),
        active=True,
    )

    link = get_case_link(case)

    msg = translate("case-link-message", language=case.language).format(
        link=link, case_id=case.human_id
    )

    send_sms(contact.phone_number, msg, case.location.tenant)


def send_results_link(case: Case):
    connection = Connection.objects.filter(case=case).first()
    if not connection:
        return
    contact = connection.client.contact
    link = settings.SITE_URL + "/results?case=" + case.human_id

    msg = translate("results-link-message", language=case.language).format(link=link)

    send_sms(contact.phone_number, msg, case.location.tenant)


def send_token(phone_number: str, case: Case):
    """Send a verification token to the given phone number"""

    contact, _ = Contact.objects.get_or_create(
        phone_number=canonicalize_phone_number(phone_number),
        active=True,
    )
    if contact.has_recent_token():
        raise ValueError(translate("recent-token-error"))

    token = contact.generate_token(case)
    msg_template = translate("verification-code-message")
    msg = msg_template.format(site_url=settings.SITE_URL, token=token)

    send_sms(contact.phone_number, msg, case.location.tenant)


def verify_token(token: str, phone_number: str, case: Case) -> Contact | None:
    """Verify that the given token is valid for the given phone number.

    If 'use' is True, mark the token as used.
    """

    contact = Contact.objects.filter(
        phone_number=canonicalize_phone_number(phone_number),
        active=True,
    ).first()

    if not contact:
        return None

    if not contact.verify_token(token, case):
        return None

    return contact


def can_connect_case(case: Case) -> bool:
    """Check if a case can be connected to a client."""
    if Connection.objects.filter(case=case).exists():
        return False

    if case.created_at < timezone.now() - timedelta(
        minutes=settings.CASE_CONNECTION_WINDOW_MINUTES
    ):
        return False

    return True


@transaction.atomic
def connect_case(case: Case, phone_number: str, token: str, consent: str) -> Connection:
    """Connect a case to a client identified by the given phone number and token."""

    if not can_connect_case(case):
        raise ValueError("Case cannot be connected")

    if consent != ConsentChoice.ALLOWED:
        raise ValueError("Consent must be allowed to connect case")

    contact = verify_token(token, phone_number, case)
    if not contact:
        raise ValueError("Invalid token or phone number")

    client, _ = Client.objects.get_or_create(contact=contact)
    connection, _ = Connection.objects.get_or_create(client=client, case=case)
    connection.consent = consent
    connection.save()
    return connection


def get_cases(client: Client):
    """Get all cases associated with a client, where the client has given consent."""
    return Case.objects.filter(
        connection__client=client, connection__consent=ConsentChoice.ALLOWED
    )


def get_client_by_id(client_id: str, case_id: str):
    """Get a client by its ID and case ID.
    The case id is required to ensure that the client is associated with the correct case.
    """
    try:
        connection = Connection.objects.get(client__id=client_id, case__id=case_id)
    except Connection.DoesNotExist:
        return None
    return connection.client


def record_client_answers(
    visit: Visit, answers: list[AnswerSchema], user: User | None = None
):
    """Record answers for a visit."""
    if user is None and visit.status != VisitStatus.CREATED:
        raise ValueError(
            "Cannot record answers for a visit that is not in the CREATED status"
        )

    current_answers = (
        visit.client_answers.all()
        .order_by("question_id", "-created_at")
        .distinct("question_id")
    )
    current_answer_map = {ans.question_id: ans for ans in current_answers}

    created_answers = []

    for answer in answers:
        choices = [int(choice.code) for choice in answer.choices]
        texts = [choice.text or "-" for choice in answer.choices]

        if answer.questionId in current_answer_map:
            existing_answer = current_answer_map[answer.questionId]
            if _compare_lists(existing_answer.choices, choices) and _compare_lists(
                existing_answer.texts, texts
            ):
                continue

        created_answers.append(
            ClientAnswer(
                visit=visit,
                question_id=answer.questionId,
                choices=choices,
                texts=texts,
                user=user,
            )
        )

    with transaction.atomic():
        ClientAnswer.objects.bulk_create(created_answers)
        visit.status = VisitStatus.CLIENT_SUBMITTED
        visit.save(update_fields=["status"])


def _compare_lists(list1: list, list2: list) -> bool:
    """Compare two lists for equality, ignoring order."""
    return sorted(list1) == sorted(list2)


def record_consultant_answers(visit: Visit, answers: list[AnswerSchema], user: User):
    """Record consultant answers for a visit."""
    warnings = []
    if visit.status != VisitStatus.CLIENT_SUBMITTED:
        warnings.append(
            "Recording consultant answers for a visit that is not in the CLIENT_SUBMITTED status"
        )

    current_answers = (
        visit.consultant_answers.all()
        .order_by("question_id", "-created_at")
        .distinct("question_id")
        .prefetch_related("question")
    )

    current_answer_map = {ans.question.pk: ans for ans in current_answers}

    for answer in answers:
        choices = [int(choice.code) for choice in answer.choices]
        texts = [choice.text or "-" for choice in answer.choices]
        if answer.questionId in current_answer_map:
            existing_answer = current_answer_map[answer.questionId]
            if _compare_lists(existing_answer.choices, choices) and _compare_lists(
                existing_answer.texts, texts
            ):
                continue
        visit.consultant_answers.create(
            question_id=answer.questionId,
            choices=choices,
            texts=texts,
            user=user,
        )
    with transaction.atomic():
        visit.status = VisitStatus.CONSULTANT_SUBMITTED
        visit.save(update_fields=["status"])

    return warnings


def get_case(request, pk):
    pk = strip_id(pk)

    visit = get_object_or_404(annotate_last_modified(Visit.objects.all()), case_id=pk)

    if request.user.is_superuser:
        return visit

    if not hasattr(request.user, "consultant"):
        raise PermissionError(translate("no-access-location"))

    consultant: tenants.models.Consultant = request.user.consultant

    if not location_can_view_case(
        consultant.locations.values_list("id", flat=True), visit.case
    ):
        raise PermissionError(translate("no-access-location"))

    return visit


def get_case_unverified(pk, key: str = ""):
    pk = strip_id(pk)

    visit = get_object_or_404(annotate_last_modified(Visit.objects.all()), case_id=pk)

    if not visit.case.has_key():
        return visit

    if not key:
        raise PermissionError(translate("case-key-required"))

    if not visit.case.check_key(key):
        raise PermissionError(translate("invalid-case-key"))

    return visit
