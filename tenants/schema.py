from ninja import ModelSchema
from tenants.models import Location, Tenant


class TenantSchema(ModelSchema):
    class Config:
        model = Tenant
        model_fields = ["id", "name"]

    locations: list["LocationSchema"]


class LocationSchema(ModelSchema):
    class Config:
        model = Location
        model_fields = ["id", "name", "tenant"]

    tenant: TenantSchema
