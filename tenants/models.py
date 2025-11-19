"""Models for tenants (organizations) using the service."""

from django.db import models
from django.db.models import QuerySet

# Create your models here.

INVITIATION_MAIL_TEMPLATE = """Hello {{ first_name }},

A new account has been created for you for {{ tentant.name }} on SURE by {{ user.get_full_name }}.

To set your password and activate your account, please click the following link:
{{ activation_link }}

If you did not expect this email, please ignore it.

"""

INVITATION_MAIL_SUBJECT = "Your new account on SURE"


class Tenant(models.Model):
    """A tenant (organization) using the service."""

    name = models.CharField(max_length=255)

    admins = models.ManyToManyField("auth.User", related_name="tenants")

    owner = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="owned_tenants"
    )

    locations: QuerySet["Location"]

    invitation_mail_template = models.TextField(
        default=INVITIATION_MAIL_TEMPLATE,
        help_text="Template for invitation emails sent to new users.",
    )
    invitation_mail_subject = models.CharField(
        max_length=255,
        default=INVITATION_MAIL_SUBJECT,
        help_text="Subject for invitation emails sent to new users.",
    )

    logo = models.ImageField(upload_to="tenant_logos/", blank=True, null=True)

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
        help_text="JSON field to store opening hours.",
        default=default_opening_hours,
    )

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

    def __str__(self) -> str:
        return f"{self.user.get_full_name()} ({self.tenant.name})"

    class Meta:
        ordering = ["user__last_name", "user__first_name"]


class Tag(models.Model):
    """A tag for categorizing cases."""

    name = models.CharField(max_length=50, unique=True)
    note = models.TextField(blank=True, null=True)

    available_in = models.ManyToManyField(Location, related_name="tags")
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
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="information_banners"
    )

    locations = models.ManyToManyField(Location, related_name="information_banners")

    name = models.CharField(max_length=100)
    content = models.TextField()
    severity = models.CharField(
        max_length=20,
        choices=SeverityLevel.choices,
        default=SeverityLevel.INFO,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)

    def __str__(self) -> str:
        return f"Banner for {self.tenant.name} ({self.pk})"
