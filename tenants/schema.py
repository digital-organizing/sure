from django.contrib.auth.models import User
from ninja import ModelSchema

from tenants.models import InformationBanner, Location, Tag, Tenant


class TenantSchema(ModelSchema):
    class Meta:
        model = Tenant
        fields = ["id", "name", "logo"]


class LocationSchema(ModelSchema):
    class Meta:
        model = Location
        fields = ["id", "name", "tenant"]

    tenant: TenantSchema


class TagSchema(ModelSchema):
    class Meta:
        model = Tag
        fields = ["id", "name", "note"]


class UserSchema(ModelSchema):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]


class BannerSchema(ModelSchema):
    class Meta:
        model = InformationBanner
        fields = ["id", "name", "content", "severity"]
