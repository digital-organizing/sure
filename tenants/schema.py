from ninja import ModelSchema

from django.contrib.auth.models import User
from tenants.models import Location, Tag, Tenant


class TenantSchema(ModelSchema):
    class Config:
        model = Tenant
        model_fields = ["id", "name"]


class LocationSchema(ModelSchema):
    class Config:
        model = Location
        model_fields = ["id", "name", "tenant"]

    tenant: TenantSchema


class TagSchema(ModelSchema):
    class Config:
        model = Tag
        model_fields = ["id", "name", "note"]


class UserSchema(ModelSchema):
    class Config:
        model = User
        model_fields = ["id", "username", "first_name", "last_name"]

