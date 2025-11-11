from ninja import ModelSchema

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
