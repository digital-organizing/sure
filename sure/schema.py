from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

import phonenumbers
from django.conf import settings
from django.db.models import Q
from django.utils.timezone import localtime, make_aware
from ninja import ModelSchema, Schema
from pydantic import BeforeValidator

from sure.models import (
    Case,
    ClientAnswer,
    ClientOption,
    ClientQuestion,
    ConsultantAnswer,
    ConsultantOption,
    ConsultantQuestion,
    Questionnaire,
    Section,
    Visit,
)


class ClientOptionSchema(ModelSchema):
    class Meta:
        model = ClientOption
        fields = [
            "id",
            "order",
            "text",
            "code",
            "choices",
            "allow_text",
        ]


class ClientQuestionSchema(ModelSchema):
    class Meta:
        model = ClientQuestion
        fields = [
            "id",
            "order",
            "code",
            "question_text",
            "format",
            "validation",
            "show_for_options",
            "copy_paste",
            "do_not_show_directly",
        ]

    options: list[ClientOptionSchema]

    @staticmethod
    def resolve_options(question: ClientQuestion) -> list[ClientOption]:
        return list(question.options.all())


class SectionSchema(ModelSchema):
    class Meta:
        model = Section
        fields = [
            "id",
            "order",
            "title",
            "description",
        ]

    client_questions: list[ClientQuestionSchema]

    @staticmethod
    def resolve_client_questions(section: Section) -> list[ClientQuestion]:
        return list(section.client_questions.all())


class QuestionnaireSchema(ModelSchema):
    class Meta:
        model = Questionnaire
        fields = [
            "id",
            "name",
        ]

    sections: list[SectionSchema]

    @staticmethod
    def resolve_sections(questionnaire: Questionnaire) -> list[Section]:
        return list(questionnaire.sections.all())

class QuestionnaireListingSchema(ModelSchema):
    class Meta:
        model = Questionnaire
        fields = [
            "id",
            "name",
        ]


class ConsultantOptionSchema(ModelSchema):
    class Meta:
        model = ConsultantOption
        fields = [
            "id",
            "order",
            "text",
            "code",
            "choices",
            "allow_text",
        ]


class ConsultantQuestionSchema(ModelSchema):
    class Meta:
        model = ConsultantQuestion
        fields = [
            "id",
            "order",
            "code",
            "question_text",
            "format",
            "validation",
            "copy_paste",
        ]

    options: list[ConsultantOptionSchema]

    @staticmethod
    def resolve_options(question: ConsultantQuestion) -> list[ConsultantOption]:
        return list(question.options.all())


class InternalQuestionnaireSchema(QuestionnaireSchema):
    consultant_questions: list[ConsultantQuestionSchema]

    @staticmethod
    def resolve_consultant_questions(
        questionnaire: Questionnaire,
    ) -> list[ConsultantQuestion]:
        return list(questionnaire.consultant_questions.all())


def validate_phone_number(value: Any) -> str | None:
    if value is None or value == "":
        return value
    if isinstance(value, phonenumbers.PhoneNumber):
        return phonenumbers.format_number(value, phonenumbers.PhoneNumberFormat.E164)
    try:
        phone_number = phonenumbers.parse(value, settings.DEFAULT_REGION)
    except phonenumbers.NumberParseException as exc:
        raise ValueError("Invalid phone number") from exc
    if not phonenumbers.is_valid_number(phone_number):
        raise ValueError("Invalid phone number")
    return phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)


class CreateCaseSchema(Schema):
    location_id: int
    questionnaire_id: int
    phone: Annotated[str | None, BeforeValidator(validate_phone_number)] = None
    external_id: Annotated[str | None, BeforeValidator(str.strip)] = None


class CreateCaseResponse(Schema):
    link: str
    case_id: str


class ChoiceSchema(Schema):
    code: str
    text: str


class AnswerSchema(Schema):
    questionId: int
    choices: list[ChoiceSchema]


class ClientAnswerSchema(ModelSchema):
    class Meta:
        model = ClientAnswer
        fields = [
                "id",
            "question",
            "choices",
            "texts",
            "created_at",
            "user",
        ]

    choices: list[int]
    texts: list[str]


class ConsultantAnswerSchema(ModelSchema):
    class Meta:
        model = ConsultantAnswer
        fields = [
                "id",
            "question",
            "choices",
            "texts",
            "created_at",
            "user",
        ]

    choices: list[int]
    texts: list[str]


class CaseHistory(Schema):
    client_answers: list[ClientAnswerSchema]
    consultant_answers: list[ConsultantAnswerSchema]


class SubmitCaseSchema(Schema):
    answers: list[AnswerSchema]


class SubmitCaseResponse(Schema):
    success: bool
    warnings: list[str] | None = None


class CaseSchema(ModelSchema):
    class Meta:
        model = Case
        fields = [
            "id",
            "location",
        ]


class VisitSchema(ModelSchema):
    class Meta:
        model = Visit
        fields = [
            "created_at",
            "questionnaire",
            "status",
            "case",
        ]

    client_answers: list[ClientAnswerSchema]


class MatchModes(StrEnum):
    STARTS_WITH = "startsWith"
    CONTAINS = "contains"
    NOT_CONTAINS = "notContains"
    ENDS_WITH = "endsWith"
    EQUALS = "equals"
    NOT_EQUALS = "notEquals"
    IN = "in"
    LESS_THAN = "lt"
    LESS_THAN_EQUAL = "lte"
    GREATER_THAN = "gt"
    GREATER_THAN_EQUAL = "gte"
    BETWEEN = "between"
    DATE_IS = "dateIs"
    DATE_IS_NOT = "dateIsNot"
    DATE_BEFORE = "dateBefore"
    DATE_AFTER = "dateAfter"


def to_date(value: str) -> str | None:
    date = datetime.fromisoformat(value)
    aware_date = make_aware(date) if date.tzinfo is None else date
    local_date = localtime(aware_date)
    return local_date.date().isoformat()


def get_filter_for_mode(
    field_name: str, match_mode: MatchModes, value: Any
) -> dict[str, Any]:
    if not value:
        return {}

    if match_mode.startswith("date"):
        value = to_date(value)

    if match_mode == MatchModes.STARTS_WITH:
        return {f"{field_name}__istartswith": value}
    if match_mode == MatchModes.CONTAINS:
        return {f"{field_name}__contains": value}
    if match_mode == MatchModes.NOT_CONTAINS:
        return {f"{field_name}__icontains__not": value}
    if match_mode == MatchModes.ENDS_WITH:
        return {f"{field_name}__iendswith": value}
    if match_mode == MatchModes.EQUALS:
        return {f"{field_name}": value}
    if match_mode == MatchModes.NOT_EQUALS:
        return {f"{field_name}__ne": value}
    if match_mode == MatchModes.IN:
        return {f"{field_name}__in": value}
    if match_mode == MatchModes.LESS_THAN:
        return {f"{field_name}__lt": value}
    if match_mode == MatchModes.LESS_THAN_EQUAL:
        return {f"{field_name}__lte": value}
    if match_mode == MatchModes.GREATER_THAN:
        return {f"{field_name}__gt": value}
    if match_mode == MatchModes.GREATER_THAN_EQUAL:
        return {f"{field_name}__gte": value}
    if match_mode == MatchModes.BETWEEN:
        return {f"{field_name}__range": value}
    if match_mode == MatchModes.DATE_IS:
        return {f"{field_name}__date": value}
    if match_mode == MatchModes.DATE_IS_NOT:
        return {f"{field_name}__date__ne": value}
    if match_mode == MatchModes.DATE_BEFORE:
        return {f"{field_name}__lt": value}
    if match_mode == MatchModes.DATE_AFTER:
        return {f"{field_name}__gt": value}

    raise ValueError(f"Unsupported match mode: {match_mode}")


class FilterData(Schema):
    value: Any | None
    matchMode: MatchModes

    class Config:
        use_enum_values = True

    def get_filter(self, field_name: str) -> Q:
        filter_dict = get_filter_for_mode(field_name, self.matchMode, self.value)
        return Q(**filter_dict)


class Operator(StrEnum):
    AND = "and"
    OR = "or"


class FilterOperator(Schema):
    operator: Operator
    constraints: list[FilterData]

    class Config:
        use_enum_values = True

    def get_filter(self, field_name: str) -> Q:
        filters = [constraint.get_filter(field_name) for constraint in self.constraints]

        q_objects = Q()

        for q in filters:
            if self.operator == Operator.AND:
                q_objects &= q
            else:
                q_objects |= q

        return q_objects


class CaseFilters(Schema):
    search: FilterData
    case: FilterData
    client_id: FilterData
    tags: FilterOperator
    location: FilterData
    status: FilterData
    last_modified_at: FilterOperator

    def get_django_filters(self) -> Q:
        q_objects = Q()

        q_objects &= self.case.get_filter("case__id")
        q_objects &= self.client_id.get_filter("case__connection__client__id")
        q_objects &= self.tags.get_filter("tags")
        q_objects &= self.location.get_filter("case__location_id")
        q_objects &= self.status.get_filter("status")
        q_objects &= self.last_modified_at.get_filter("last_modified_at")

        if self.search.value:
            if self.search.value.lower().startswith("suf-"):
                self.search.value = self.search.value[4:]
                q_objects &= self.search.get_filter("case__id")
            elif self.search.value.lower().startswith("suc-"):
                self.search.value = self.search.value[4:]
                q_objects &= self.search.get_filter("case__connection__client__id")
            else:
                q_objects &= self.search.get_filter(
                    "case__id"
                ) | self.search.get_filter("case__connection__client__id")

        return q_objects


class OptionSchema(Schema):
    label: str
    value: str


class CaseListingSchema(ModelSchema):
    location: str
    client: str | None
    last_modified_at: str
    tags: list[str]

    class Meta:
        model = Visit
        fields = [
            "case",
            "id",
            "tags",
            "status",
        ]

    @staticmethod
    def resolve_case_id(visit: Visit) -> int:
        return visit.case.human_id

    @staticmethod
    def resolve_location(visit: Visit) -> str:
        return visit.case.location.name

    @staticmethod
    def resolve_client(visit: Visit) -> str:
        connection = getattr(visit.case, "connection", None)
        if not connection:
            return ""
        return connection.client.humnan_id

    @staticmethod
    def resolve_last_modified_at(visit: Visit) -> str:
        return getattr(visit, "last_modified_at", visit.created_at).isoformat()
