"""Models for tenants (organizations) using the service."""

from django.db import models
from django.db.models import QuerySet

# Create your models here.


class Tenant(models.Model):
    """A tenant (organization) using the service."""

    name = models.CharField(max_length=255)

    admins = models.ManyToManyField("auth.User", related_name="tenants")

    owner = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="owned_tenants"
    )

    locations: QuerySet["Location"]

    def __str__(self) -> str:
        return f"{self.name}"


class Location(models.Model):
    """A location belonging to a tenant."""

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="locations"
    )
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return f"{self.name} ({self.tenant.name}, {self.pk})"


class Consultant(models.Model):
    """A consultant belonging to a tenant."""

    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="consultants"
    )
    user = models.OneToOneField("auth.User", on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"{self.user.get_full_name()} ({self.tenant.name})"
