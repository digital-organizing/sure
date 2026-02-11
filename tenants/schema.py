from django.contrib.auth.models import User
from ninja import Field, ModelSchema

from tenants.models import InformationBanner, Advertisement, Location, Tag, Tenant


class TenantSchema(ModelSchema):
    class Meta:
        model = Tenant
        fields = ["id", "name", "logo"]


class LocationSchema(ModelSchema):
    class Meta:
        model = Location
        fields = ["id", "name", "tenant", "phone_number", "address", "opening_hours"]

    tenant: TenantSchema


class TagSchema(ModelSchema):
    class Meta:
        model = Tag
        fields = ["id", "name", "note"]


class UserSchema(ModelSchema):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]

    tenant: str = Field(..., alias="consultant.tenant.name")


class BannerSchema(ModelSchema):
    class Meta:
        model = InformationBanner
        fields = ["id", "name", "content", "severity"]


class AdvertisementSchema(ModelSchema):
    class Meta:
        model = Advertisement
        fields = ["id", "name", "content"]
