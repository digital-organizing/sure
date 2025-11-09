from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.pagination import paginate, PageNumberPagination

from sure.cases import annotate_last_modified
from sure.client_service import (
    create_case,
    create_visit,
    get_case_link,
    record_client_answers,
    send_case_link,
    strip_id,
    verify_access_to_location,
)
from sure.models import (
    ClientOption,
    ClientQuestion,
    ConsultantOption,
    ConsultantQuestion,
    Questionnaire,
    Section,
    Visit,
)
from sure.schema import (
    CaseListingSchema,
    CreateCaseResponse,
    CreateCaseSchema,
    InternalQuestionnaireSchema,
    QuestionnaireSchema,
    SubmitCaseResponse,
    SubmitCaseSchema,
    VisitSchema,
)
from tenants.models import Consultant

router = Router()


def _prefetch_questionnaire(internal=False):
    query = Questionnaire.objects.prefetch_related(
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
    )

    if internal:
        query = query.prefetch_related(
            Prefetch(
                "consultant_questions",
                queryset=ConsultantQuestion.objects.order_by("order").prefetch_related(
                    Prefetch(
                        "options", queryset=ConsultantOption.objects.order_by("order")
                    )
                ),
            )
        )
    return query


@router.get("/case/{pk}/questionnaire/", response=QuestionnaireSchema, auth=None)
def get_case_questionnaire(request, pk: str):  # pylint: disable=unused-argument
    """Get the questionnaire associated with a case."""
    pk = strip_id(pk)

    visit = get_object_or_404(Visit, case_id=pk)
    questionnaire = _prefetch_questionnaire().get(pk=visit.questionnaire.pk)

    return questionnaire


@router.get("/case/{pk}/internal/", response=InternalQuestionnaireSchema)
def get_case_internal(request, pk: str):
    """Get the internal questionnaire associated with a case."""
    pk = strip_id(pk)

    visit = get_object_or_404(Visit, case_id=pk)

    if not verify_access_to_location(visit.case.location, request.user):
        raise PermissionError("User does not have access to this location")

    questionnaire = _prefetch_questionnaire(internal=True).get(
        pk=visit.questionnaire.pk
    )

    return questionnaire


@router.get("/case/{pk}/visit/", response=VisitSchema)
def get_visit(request, pk: str):
    """Get the client answers for a case."""
    pk = strip_id(pk)

    visit = get_object_or_404(Visit, case_id=pk)

    if not verify_access_to_location(visit.case.location, request.user):
        raise PermissionError("User does not have access to this location")

    return visit


@router.post("/case/{pk}/submit/", auth=None, response=SubmitCaseResponse)
def submit_case(request, pk: str, answers: SubmitCaseSchema):
    """Submit client answers for a case."""
    pk = strip_id(pk)

    visit = get_object_or_404(Visit, case_id=pk)
    if request.user.is_authenticated:
        if not verify_access_to_location(visit.case.location, request.user):
            raise PermissionError("User does not have access to this location")

    record_client_answers(
        visit, answers.answers, request.user if request.user.is_authenticated else None
    )

    return {"success": True}


@router.post("/case/create/")
def create_case_view(request, data: CreateCaseSchema):
    """Create a new case from a questionnaire."""
    case = create_case(data.location_id, request.user)
    create_visit(case, get_object_or_404(Questionnaire, pk=data.questionnaire_id))

    link = get_case_link(case)

    if data.phone:
        send_case_link(case, data.phone)

    return CreateCaseResponse(link=link)


@router.get("/questionnaires/{pk}/", response=QuestionnaireSchema, auth=None)
def get_questionnaire(request, pk: int):  # pylint: disable=unused-argument
    """Get a questionnaire by its ID."""
    questionnaire = _prefetch_questionnaire().get(pk=pk)
    return questionnaire


@router.get("/internal/questionnaires/{pk}/", response=InternalQuestionnaireSchema)
def get_internal_questionnaire(request, pk: int):  # pylint: disable=unused-argument
    """Get a questionnaire by its ID, including consultant questions."""
    questionnaire = _prefetch_questionnaire(internal=True).get(pk=pk)
    return questionnaire


@router.get("/cases/", response=list[CaseListingSchema])
@paginate(PageNumberPagination, page_size=20)
def list_cases(request):
    """List all cases the user has access to."""
    consultant = get_object_or_404(Consultant, user=request.user)
    visits = annotate_last_modified(
        Visit.objects.filter(case__location__tenant=consultant.tenant)
        .select_related("case", "questionnaire", "case__connection", "case__location")
        .prefetch_related("client_answers", "consultant_answers", "test_results")
    ).order_by("-last_modified_at")

    return visits
