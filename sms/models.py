from django.db import models

# Create your models here.


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

    def __str__(self) -> str:
        return f"SMS to {self.to} at {self.sent_at}"
