"""Models for the sure app

This includes clients, cases, and connections, as well as the questionnaires and the answers."""

import secrets
import uuid

import phonenumbers
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

BASE_58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

CONTACT_ID_LENGTH = 6
CASE_ID_LENGTH = 6


def generate_contact_id():
    """Generate a base 58 client ID of length CLIENT_ID_LENGTH (6)."""
    return "".join(secrets.choice(BASE_58) for _ in range(CONTACT_ID_LENGTH))


def generate_case_id():
    """Generate a base 58 case ID of length CASE_ID_LENGTH (6)."""
    return "".join(secrets.choice(BASE_58) for _ in range(CASE_ID_LENGTH))


class Case(models.Model):
    """A case is one instance of a clients visit and the questions they answer."""

    id = models.CharField(
        max_length=6,
        primary_key=True,
        default=generate_case_id,
        verbose_name=_("Case ID"),
    )
    location = models.ForeignKey(
        "tenants.Location",
        on_delete=models.CASCADE,
        related_name="cases",
        verbose_name=_("Location"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    @property
    def human_id(self):
        """SUF: Sure 'Fall' or Form/Formulaire"""
        return f"SUF-{self.id}"

    class Meta:
        verbose_name = _("Case")
        verbose_name_plural = _("Cases")


class ConsentChoice(models.TextChoices):
    """Choices for consent to store data."""

    ALLOWED = "allowed", _("Allowed")
    DENIED = "denied", _("Denied")


def generate_token():
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


class Contact(models.Model):
    """Contact model to store contact information for clients, if they choose to provide it."""

    id = models.UUIDField(
        primary_key=True, editable=False, unique=True, default=uuid.uuid4
    )
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=30, unique=True)

    tokens: models.QuerySet["Token"]

    def save(self, *args, **kwargs):
        if not phonenumbers.is_valid_number(
            phonenumbers.parse(self.phone_number, settings.DEFAULT_REGION)
        ):
            raise ValueError("Invalid phone number")
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Contact")
        verbose_name_plural = _("Contacts")

    def generate_token(self) -> str:
        """Generate a new token for this contact."""
        token = Token.objects.create(contact=self)
        return token.token


class Client(models.Model):
    """A client (person seeking help)"""

    id = models.CharField(
        max_length=6,
        primary_key=True,
        default=generate_contact_id,
        verbose_name=_("Client ID"),
    )
    contact = models.OneToOneField(
        Contact, on_delete=models.CASCADE, related_name="client"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    @property
    def human_id(self):
        """SUC: Sure 'Client' or 'Klient'"""
        return f"SUC-{self.id}"


class Connection(models.Model):
    case = models.OneToOneField(
        Case, on_delete=models.CASCADE, related_name="connection"
    )
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="connections"
    )

    consent = models.CharField(
        max_length=10,
        choices=ConsentChoice.choices,
        default=ConsentChoice.DENIED,
        verbose_name=_("Consent"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))


class Token(models.Model):
    """A token to verify the ownership of a contact method (email or phone number).

    A token is generated and sent to the client, to ensure that they own the contact method
    """

    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="tokens"
    )
    token = models.CharField(
        max_length=64, verbose_name=_("Token"), default=generate_token, unique=True
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    used_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Used At"))
