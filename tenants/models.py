"""Models for tenants (organizations) using the service."""

import datetime
import secrets

import simple_history
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import QuerySet
from django.utils.timezone import make_aware
from django.utils.translation import gettext_lazy as _
from django_clamd.validators import validate_file_infection
from html_sanitizer import Sanitizer
from simple_history.models import HistoricalRecords

simple_history.register(User, app=__package__)
# Create your models here.

INVITIATION_MAIL_TEMPLATE = """Hello {{ first_name }},

A new account has been created for you for {{ tenant.name }} on SURE by {{ user.get_full_name }}.

To set your password and activate your account, please click the following link:
{{ activation_link }}

Important: This link is only valid for creating an account. Afterwards, you must always log in via www.stay-sure.ch/login. If you did not expect this email, please ignore it.
"""

INVITATION_MAIL_SUBJECT = "Your new account on SURE"


class Tenant(models.Model):
    """A tenant (organization) using the service."""

    name = models.CharField(
        max_length=255,
        help_text=_(
            "Name of the tenant organization, which will be displayed to consultants and admins"
        ),
    )

    admins = models.ManyToManyField("auth.User", related_name="tenants")

    owner = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="owned_tenants"
    )

    locations: QuerySet["Location"]

    invitation_mail_template = models.TextField(
        default=INVITIATION_MAIL_TEMPLATE,
        help_text=_("Template for invitation emails sent to new users."),
    )
    invitation_mail_subject = models.CharField(
        max_length=255,
        default=INVITATION_MAIL_SUBJECT,
        help_text=_("Subject for invitation emails sent to new users."),
    )

    logo = models.ImageField(
        upload_to="tenant_logos/",
        blank=True,
        null=True,
        help_text=_(
            "Upload a png with white or tranparent background resolution of 250px pixels"
        ),
        validators=[
            validate_file_infection,
        ],
    )

    history = HistoricalRecords()

    def __str__(self) -> str:
        return f"{self.name}"

    class Meta:
        ordering = ["name"]


def default_opening_hours():
    weekdays = [["09:00", "12:00"], ["13:00", "17:00"]]
    weekends = []
    return {
        "monday": weekdays,
        "tuesday": weekdays,
        "wednesday": weekdays,
        "thursday": weekdays,
        "friday": weekdays,
        "saturday": weekends,
        "sunday": [],
    }


WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def validate_opening_hours(value):
    if not isinstance(value, dict):
        raise ValidationError("Opening hours must be a dictionary.")
    for day in WEEKDAYS:
        if day not in value:
            raise ValidationError(f"Opening hours must include '{day}'.")
        hours = value[day]
        if not isinstance(hours, list):
            raise ValidationError(f"Opening hours for '{day}' must be a list.")
        for period in hours:
            if (
                not isinstance(period, list)
                or len(period) != 2
                or not all(isinstance(t, str) for t in period)
            ):
                raise ValidationError(
                    f"Each opening period for '{day}' must be a list of two time strings."
                )


class Location(models.Model):
    """A location belonging to a tenant."""

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="locations"
    )
    name = models.CharField(max_length=255)

    address = models.TextField(blank=True, null=True)

    opening_hours = models.JSONField(
        blank=True,
        null=True,
        help_text=_(
            "JSON field to store opening hours. These are displayed to clients and used to prevent SMS sending outside opening hours."
        ),
        default=default_opening_hours,
        validators=[validate_opening_hours],
    )

    reminder_text = models.TextField(
        blank=True,
        null=True,
        help_text=_(
            "Additional text to include in reminder notifications sent to clients."
        ),
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text=_("Phone number displayed to clients for this location."),
    )

    excluded_questions = models.ManyToManyField(
        "sure.ClientQuestion",
        blank=True,
        related_name="excluded_in_centers",
        verbose_name=_("Not visible questions at this center."),
        help_text=_(
            "The selected questions will not be asked for cases at this center."
        ),
        limit_choices_to={"optional_for_centers": True},
    )

    included_questions = models.ManyToManyField(
        "sure.ClientQuestion",
        blank=True,
        related_name="included_in_centers",
        verbose_name=_("Visible questions at this center."),
        help_text=_("These questions will be asked for cases at this center."),
        limit_choices_to={"extra_for_centers": True},
    )

    def get_next_opening(
        self, from_datetime: datetime.datetime
    ) -> datetime.datetime | None:
        """Get the next opening datetime from a given datetime."""
        weekday = from_datetime.weekday()  # 0 = Monday, 6 = Sunday
        for i in range(7):
            day = (weekday + i) % 7
            hours = self.opening_hours.get(WEEKDAYS[day], [])
            for start_str, end_str in hours:
                start_time = datetime.datetime.strptime(start_str, "%H:%M").time()
                opening_datetime = make_aware(
                    datetime.datetime.combine(
                        from_datetime.date() + datetime.timedelta(days=i),
                        start_time,
                    )
                )
                closing_time = datetime.datetime.strptime(end_str, "%H:%M").time()
                closing_datetime = make_aware(
                    datetime.datetime.combine(
                        from_datetime.date() + datetime.timedelta(days=i),
                        closing_time,
                    )
                )

                if (
                    opening_datetime <= from_datetime
                    and from_datetime < closing_datetime
                ):
                    return opening_datetime

                if opening_datetime > from_datetime:
                    return opening_datetime
        return None

    def __str__(self) -> str:
        return f"{self.name} ({self.tenant.name}, {self.pk})"

    class Meta:
        ordering = ["name"]


class Consultant(models.Model):
    """A consultant belonging to a tenant."""

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="consultants"
    )
    user = models.OneToOneField("auth.User", on_delete=models.CASCADE)

    locations = models.ManyToManyField(Location, related_name="consultants")

    history = HistoricalRecords()

    inactive = models.BooleanField(
        default=False,
        help_text=_(
            "Designates whether this consultant should be treated as inactive."
        ),
    )

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        if self.inactive:
            self.user.is_active = False
            self.user.set_unusable_password()
            self.user.save()

    def __str__(self) -> str:
        return f"{self.user.get_full_name()} ({self.tenant.name})"

    class Meta:
        ordering = ["user__last_name", "user__first_name"]


class Tag(models.Model):
    """A tag for categorizing cases."""

    name = models.CharField(max_length=50, unique=True)
    note = models.TextField(blank=True, null=True)

    available_in = models.ManyToManyField(Location, related_name="tags", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    owner = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="owned_tags"
    )

    def __str__(self) -> str:
        return f"{self.name}"

    class Meta:
        ordering = ["name"]


class SeverityLevel(models.TextChoices):
    SUCCESS = "success", "Success"
    INFO = "info", "Info"
    WARN = "warn", "Warning"
    ERROR = "error", "Error"
    SECONDRARY = "secondary", "Secondary"
    CONTRAST = "contrast", "Contrast"
    PRIMARY = "primary", "Primary"


class InformationBanner(models.Model):
    """
    Docstring für InformationBanner
    """

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="information_banners"
    )

    locations = models.ManyToManyField(
        Location,
        blank=True,
        related_name="information_banners",
        help_text=_("Locations for which this banner is displayed."),
    )

    name = models.CharField(max_length=100)
    content = models.TextField(
        help_text=_(
            'Content of the information banner, supports markdown or html: <a target="_blank" href="https://www.markdownguide.org/basic-syntax/">More info</a>.'
        )
    )
    severity = models.CharField(
        max_length=20,
        choices=SeverityLevel.choices,
        default=SeverityLevel.INFO,
        help_text=_("Severity level of the banner, which determines its appearance."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_(
            "Date and time when the banner becomes visible. If empty, the banner is visible immediately."
        ),
    )
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_(
            "Date and time when the banner expires. If empty, the banner does not expire."
        ),
    )

    def __str__(self) -> str:
        return f"Banner for {self.tenant.name} ({self.pk})"

    def save(self, *args, **kwargs):
        sanitizer = Sanitizer({"keep_typographic_whitespace": True})
        self.content = sanitizer.sanitize(self.content)
        super().save(*args, **kwargs)

class Advertisement(models.Model):
    """
    Docstring für Advertisement
    """

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="advertisements"
    )

    locations = models.ManyToManyField(
        Location,
        blank=True,
        related_name="advertisements",
        help_text=_("Locations for which this advertisement is displayed."),
    )

    name = models.CharField(max_length=100)
    content = models.TextField(
        help_text=_(
            'Content of the advertisement, supports markdown or html: <a target="_blank" href="https://www.markdownguide.org/basic-syntax/">More info</a>.'
        )
    )
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_(
            "Date and time when the advertisement becomes visible. If empty, the advertisement is visible immediately."
        ),
    )
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_(
            "Date and time when the advertisement expires. If empty, the advertisement does not expire."
        ),
    )

    def __str__(self) -> str:
        return f"Advertisement for {self.tenant.name} ({self.pk})"

    def save(self, *args, **kwargs):
        sanitizer = Sanitizer({"keep_typographic_whitespace": True})
        self.content = sanitizer.sanitize(self.content)
        super().save(*args, **kwargs)


def generate_name():
    return secrets.token_hex(10)


def generate_token():
    return secrets.token_hex(25)


class APIToken(models.Model):
    """API Token for a tenant."""

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="api_tokens"
    )
    name = models.CharField(max_length=30, default=generate_name)
    token = models.CharField(max_length=80, default=generate_token)

    owner = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="owned_api_tokens"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    revoked = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"API Token '{self.name}' for {self.tenant.name}"
