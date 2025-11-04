from django.db.models import Prefetch
from ninja import ModelSchema, Router
from sure.models import (
    ConsultantOption,
    ConsultantQuestion,
    Questionnaire,
    Section,
    ClientQuestion,
    ClientOption,
)
from django.utils import translation
from django.utils.translation import get_language_from_request
from django.conf import settings

router = Router()

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


@router.get("/questionnaires/{pk}", response=QuestionnaireSchema)
def get_questionnaire(request, pk: int, lang: str|None = None):  # pylint: disable=unused-argument
    """Get a questionnaire by its ID."""
    if not lang:
        lang = get_language_from_request(request) or settings.MODELTRANSLATION_DEFAULT_LANGUAGE
    translation.activate(lang)
    
    questionnaire = Questionnaire.objects.prefetch_related(
        Prefetch(
            "sections",
            queryset=Section.objects.order_by("order").prefetch_related(
                Prefetch(
                    "client_questions",
                    queryset=ClientQuestion.objects.order_by("order").prefetch_related(
                        Prefetch(
                            "options", queryset=ClientOption.objects.order_by("order")
                        )
                    ),
                )
            ),
        )
    ).get(pk=pk)

    return questionnaire


@router.get("/internal/questionnaires/{pk}", response=InternalQuestionnaireSchema)
def get_internal_questionnaire(request, pk: int, lang: str|None = None):  # pylint: disable=unused-argument
    """Get a questionnaire by its ID, including consultant questions."""
    if not lang:
        lang = get_language_from_request(request) or settings.MODELTRANSLATION_DEFAULT_LANGUAGE
    translation.activate(lang)

    questionnaire = Questionnaire.objects.prefetch_related(
        Prefetch(
            "sections",
            queryset=Section.objects.order_by("order").prefetch_related(
                Prefetch(
                    "client_questions",
                    queryset=ClientQuestion.objects.order_by("order").prefetch_related(
                        Prefetch(
                            "options", queryset=ClientOption.objects.order_by("order")
                        )
                    ),
                )
            ),
        ),
        Prefetch(
            "consultant_questions",
            queryset=ConsultantQuestion.objects.order_by("order").prefetch_related(
                Prefetch("options", queryset=ConsultantOption.objects.order_by("order"))
            ),
        ),
    ).get(pk=pk)

    return questionnaire
