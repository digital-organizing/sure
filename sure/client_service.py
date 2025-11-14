"""Functions for creating and managing clients and their cases."""

import phonenumbers
from django.conf import settings
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone

import tenants.models
from sure.cases import annotate_last_modified
from sure.schema import AnswerSchema
from sure.twilio import send_sms

from .models import (
    Case,
    Client,
    Connection,
    ConsentChoice,
    Contact,
    Questionnaire,
    Visit,
    VisitStatus,
)


def canonicalize_phone_number(phone_number: str) -> str:
    """Convert a phone number to E.164 format."""
    return phonenumbers.format_number(
        phonenumbers.parse(phone_number, settings.DEFAULT_REGION),
        phonenumbers.PhoneNumberFormat.E164,
    )


def verify_access_to_location(location: tenants.models.Location, user) -> bool:
    """Verify that the user has access to the given location."""
    if user.is_superuser:
        return True
    if user.tenants.filter(id=location.tenant.pk).exists():
        return True
    return False


def create_case(location_id: int, user, external_id: str | None) -> Case:
    """Create a new case at the given location."""
    location = get_object_or_404(tenants.models.Location, pk=location_id)
    if not verify_access_to_location(location, user):
        raise PermissionError("User does not have access to this location")
    case = Case.objects.create(
        location=location,
        external_id=external_id or "",
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


def generate_token(phone_number: str) -> tuple[Contact, str]:
    """Generate a token for the given phone number, creating a contact if necessary."""
    contact, _ = Contact.objects.get_or_create(
        phone_number=canonicalize_phone_number(phone_number),
    )
    token = contact.generate_token()
    return contact, token


def send_case_link(case: Case, phone_number: str):
    """Send a link to access the case to the given phone number."""
    contact, token = generate_token(phone_number)

    link = get_case_link(case) + "&token=" + token

    msg = "Open this link to access your case: " + link

    send_sms(contact.phone_number, msg)


def send_token(phone_number: str):
    """Send a verification token to the given phone number"""

    contact, _ = Contact.objects.get_or_create(
        phone_number=canonicalize_phone_number(phone_number),
    )
    token = contact.generate_token()
    # Send the token via SMS (implementation not shown)
    link = f"{settings.SITE_URL}/verify/?token={token}"

    msg = "Click this link to verify your phone number: " + link

    send_sms(contact.phone_number, msg)


def verify_token(token: str, phone_number: str, use=False) -> Contact | None:
    """Verify that the given token is valid for the given phone number.

    If 'use' is True, mark the token as used.
    """

    contact = Contact.objects.filter(
        phone_number=canonicalize_phone_number(phone_number),
    ).first()

    if not contact:
        return None

    valid_token = contact.tokens.filter(token=token, used_at__isnull=True).first()
    if not valid_token:
        return None

    if use:
        valid_token.used_at = timezone.now()
        valid_token.save()

    return contact


def connect_case(case: Case, phone_number: str, token: str, consent: str) -> Connection:
    """Connect a case to a client identified by the given phone number and token."""
    if consent != ConsentChoice.ALLOWED:
        raise ValueError("Consent must be allowed to connect case")

    contact = verify_token(token, phone_number, use=True)
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
        visit.client_answers.create(
            question_id=answer.questionId,
            choices=choices,
            texts=texts,
            user=user,
        )

    visit.status = VisitStatus.CLIENT_SUBMITTED
    visit.save()


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
    visit.status = VisitStatus.CONSULTANT_SUBMITTED
    visit.save()

    return warnings


def get_case(request, pk):
    pk = strip_id(pk)

    visit = get_object_or_404(annotate_last_modified(Visit.objects.all()), case_id=pk)

    if not verify_access_to_location(visit.case.location, request.user):
        raise PermissionError("User does not have access to this location")

    return visit
