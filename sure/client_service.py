"""Functions for creating and managing clients and their cases."""

import phonenumbers
from django.conf import settings
from django.utils import timezone

import tenants.models
from sure.twilio import send_sms

from .models import Case, Client, Connection, ConsentChoice, Contact


def canonicalize_phone_number(phone_number: str) -> str:
    """Convert a phone number to E.164 format."""
    return phonenumbers.format_number(
        phonenumbers.parse(phone_number, settings.DEFAULT_REGION),
        phonenumbers.PhoneNumberFormat.E164,
    )


def create_case(location: tenants.models.Location) -> Case:
    """Create a new case at the given location."""
    case = Case.objects.create(location=location)
    return case


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
