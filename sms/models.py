from django.db import models


class SMSCategory(models.TextChoices):
    """Why an SMS was sent, so the usage can be broken down for billing."""

    CASE_LINK = "case_link", "Questionnaire link"
    RESULTS_LINK = "results_link", "Results link"
    VERIFICATION_CODE = "verification_code", "Verification code"
    REMINDER = "reminder", "Reminder"


class SMSMessage(models.Model):
    to = models.CharField(max_length=15)
    sent_at = models.DateTimeField(auto_now_add=True)
    response = models.JSONField()

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="sms_messages",
        blank=True,
        null=True,
    )
    # Empty for messages sent before these were recorded and that the
    # backfill_sms_categories command could not attribute.
    location = models.ForeignKey(
        "tenants.Location",
        on_delete=models.SET_NULL,
        related_name="sms_messages",
        blank=True,
        null=True,
    )
    category = models.CharField(
        max_length=20, choices=SMSCategory.choices, blank=True, default=""
    )

    def __str__(self) -> str:
        return f"SMS to {self.to} at {self.sent_at}"

    def save(self, *args, **kwargs) -> None:
        # Mask the phone number for privacy
        self.to = "X" * (len(self.to) - 4) + self.to[-4:]
        super().save(*args, **kwargs)
