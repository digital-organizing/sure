from ninja.schema import Schema
from ninja import Field, ModelSchema

from labor.models import LabOrder, Laboratory, TestProfile


class PatientDataSchema(Schema):
    birth_year: int
    gender: str
    note: str


class LabOrderSchema(ModelSchema):
    class Meta:
        model = LabOrder
        fields = ["order_number", "created_at", "codes", "profiles", "status"]

    codes: list[str] = Field(...)


class TestProfileSetSchema(ModelSchema):
    class Meta:
        model = TestProfile
        fields = [
            "test_kind",
            "profile_name",
            "profile_code",
            "result_label",
            "material",
            "material_code",
            "price_vct",
            "price_kk",
            "note",
        ]


class LaboratorySchema(ModelSchema):
    class Meta:
        model = Laboratory
        fields = ["id", "name"]

    profiles: list[TestProfileSetSchema] = Field(..., alias="testprofile_set")
