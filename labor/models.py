from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords
# Create your models here.


class Laboratory(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Laboratory"
        verbose_name_plural = "Laboratories"


class FTPConnection(models.Model):
    laboratory = models.OneToOneField(Laboratory, on_delete=models.CASCADE)

    sftp = models.BooleanField(default=True)

    host = models.CharField(max_length=255)
    user = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    upload_directory = models.CharField(max_length=255)
    results_directory = models.CharField(max_length=255)

    history = HistoricalRecords()

    def __str__(self):
        return f"SFTP Settings for {self.laboratory.name}"

    class Meta:
        verbose_name = "FTP Connection"
        verbose_name_plural = "FTP Connections"


def validate_nr_kreis(value):
    if not value.isdigit():
        raise ValidationError("Nr Kreis must be numeric")
    if not LabOrderCounter.objects.filter(nr_kreis=value).exists():
        raise ValidationError(f"No LabOrderCounter found for Nr Kreis {value}")


class LocationToLab(models.Model):
    labor = models.ForeignKey(Laboratory, on_delete=models.CASCADE)
    location = models.ForeignKey("tenants.Location", on_delete=models.CASCADE)

    client_code = models.CharField(max_length=100)
    nr_kreis = models.CharField(
        max_length=10, blank=True, help_text="e.g. 9610", validators=[validate_nr_kreis]
    )

    def __str__(self):
        return f"{self.location.name} -> {self.labor.name}"

    class Meta:
        verbose_name = "Location to Laboratory Mapping"
        verbose_name_plural = "Location to Laboratory Mappings"

    history = HistoricalRecords()


class LabOrderCounter(models.Model):
    nr_kreis = models.CharField(
        max_length=10, blank=True, help_text="e.g. 9610", unique=True
    )
    base_number = models.CharField(max_length=50, help_text="e.g. 0001297740")
    last_index = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.base_number}"

    class Meta:
        verbose_name = "Lab Order Counter"

        verbose_name_plural = "Lab Order Counters"


class OrderStatus(models.TextChoices):
    GENERATED = "generated", "Generated"
    SENT = "sent", "Sent"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"


class LabOrder(models.Model):
    visit = models.ForeignKey(
        "sure.Visit", on_delete=models.CASCADE, related_name="lab_orders"
    )
    lab_order_counter = models.ForeignKey(LabOrderCounter, on_delete=models.CASCADE)
    order_number = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20, choices=OrderStatus.choices, default=OrderStatus.GENERATED
    )

    content = models.TextField(blank=True, help_text="HL7 Order content")
    profiles = ArrayField(
        models.CharField(max_length=255),
        blank=True,
        default=list,
        help_text="List of test profiles included in the order",
    )
    codes = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        help_text="List of material codes",
    )

    history = HistoricalRecords()

    def __str__(self):
        return self.order_number

    class Meta:
        verbose_name = "Lab Order"
        verbose_name_plural = "Lab Orders"


class LabResult(models.Model):
    visit = models.ForeignKey(
        "sure.Visit", on_delete=models.CASCADE, related_name="lab_results"
    )
    received_at = models.DateTimeField(auto_now_add=True)

    order = models.ForeignKey(
        LabOrder,
        on_delete=models.CASCADE,
        related_name="lab_results",
        null=True,
        blank=True,
    )

    content = models.TextField(blank=True, help_text="HL7 Result content")

    def __str__(self):
        return f"Lab Result for Visit {self.visit.id}"

    class Meta:
        verbose_name = "Lab Result"
        verbose_name_plural = "Lab Results"


class TestProfile(models.Model):
    laboratory = models.ForeignKey(
        Laboratory,
        on_delete=models.CASCADE,
        help_text="Laboratory offering this test profile",
    )
    test_kind = models.ForeignKey(
        "sure.TestKind",
        on_delete=models.CASCADE,
        help_text="Test kind associated with this profile",
    )

    profile_name = models.CharField(
        max_length=255, help_text="Name of the test profile (lab)"
    )
    profile_code = models.CharField(
        max_length=50, help_text="Code of the test profile (lab)"
    )
    result_label = models.CharField(
        max_length=100, blank=True, help_text="Label in HL7 result (OBX-3)"
    )

    material = models.CharField(max_length=50, blank=True, help_text="e.g. Serum, EDTA")
    material_code = models.CharField(max_length=10, blank=True, help_text="e.g. S")

    price_vct = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price for private patients (VCT)",
    )
    price_kk = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price for statutory health insurance (KK)",
    )
    note = models.TextField(
        blank=True, help_text="Additional notes about the test profile"
    )

    def __str__(self):
        return f"{self.profile_name} ({self.laboratory.name})"

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Test Profile"
        verbose_name_plural = "Test Profiles"
