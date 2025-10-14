from ninja import ModelSchema, Schema

from sure.models import (Case, ClientAnswer, ClientOption, ClientQuestion,
                         ConsultantOption, ConsultantQuestion, Questionnaire,
                         Section, Visit)


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


class CreateCaseSchema(Schema):
    location_id: int
    questionnaire_id: int
    phone: str | None = None


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
