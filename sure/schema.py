from typing import Annotated, Any, Optional
from django.conf import settings
from ninja import ModelSchema, Schema
import phonenumbers
from pydantic import BeforeValidator

from sure.models import (
    Case,
    ClientAnswer,
    ClientOption,
    ClientQuestion,
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
    if value is None:
        return value
    if isinstance(value, phonenumbers.PhoneNumber):
        return phonenumbers.format_number(value, phonenumbers.PhoneNumberFormat.E164)
    try:
        phone_number = phonenumbers.parse(value, settings.DEFAULT_REGION)
        if not phonenumbers.is_valid_number(phone_number):
            raise ValueError("Invalid phone number")
        return phonenumbers.format_number(
            phone_number, phonenumbers.PhoneNumberFormat.E164
        )
    except phonenumbers.NumberParseException:
        raise ValueError("Invalid phone number")


class CreateCaseSchema(Schema):
    location_id: int
    questionnaire_id: int
    phone: Annotated[Optional[str], BeforeValidator(validate_phone_number)] = None


class CreateCaseResponse(Schema):
    link: str


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
            "question",
            "choices",
            "texts",
            "created_at",
            "user",
        ]

    choices: list[int]
    texts: list[str]


class SubmitCaseSchema(Schema):
    answers: list[AnswerSchema]


class SubmitCaseResponse(Schema):
    success: bool


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
        ]

    client_answers: list[ClientAnswerSchema]


class CaseListingSchema(ModelSchema):
    location: str
    client: str | None
    last_modified_at: str

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
