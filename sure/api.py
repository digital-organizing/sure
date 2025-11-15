import logging

from django.db.models import F, Func, Prefetch
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.errors import HttpError
from ninja.pagination import PageNumberPagination, paginate

from sure.cases import annotate_last_modified
from sure.client_service import (
    create_case,
    create_visit,
    get_case,
    get_case_link,
    record_client_answers,
    record_consultant_answers,
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
    Test,
    TestCategory,
    TestKind,
    Visit,
    VisitStatus,
)
from sure.schema import (
    CaseFilters,
    CaseHistory,
    CaseListingSchema,
    ClientAnswerSchema,
    ConsultantAnswerSchema,
    CreateCaseResponse,
    CreateCaseSchema,
    InternalQuestionnaireSchema,
    OptionSchema,
    QuestionnaireListingSchema,
    QuestionnaireSchema,
    SubmitCaseResponse,
    SubmitCaseSchema,
    TestCategorySchema,
    TestResultOptionSchema,
)
from tenants.models import Consultant

logger = logging.getLogger(__name__)

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
    if visit.status != VisitStatus.CREATED and request.user.is_authenticated is False:
        raise HttpError(403, "Questionnaire already submitted")

    questionnaire = _prefetch_questionnaire().get(pk=visit.questionnaire.pk)

    return questionnaire


@router.get("/case/{pk}/internal/", response=InternalQuestionnaireSchema)
def get_case_internal(request, pk: str):
    """Get the internal questionnaire associated with a case."""
    visit = get_case(request, pk)

    questionnaire = _prefetch_questionnaire(internal=True).get(
        pk=visit.questionnaire.pk
    )

    return questionnaire


@router.get("/case/{pk}/visit/", response=CaseListingSchema)
def get_visit(request, pk: str):
    """Get the client answers for a case."""

    visit = get_case(request, pk)
    return visit


@router.get("/case/{pk}/visit/client-answers/", response=list[ClientAnswerSchema])
def get_visit_client_answers(request, pk: str):
    visit = get_case(request, pk)
    # Only get latest per querstion_id
    return (
        visit.client_answers.all()
        .order_by("question_id", "-created_at")
        .distinct("question_id")
    )


@router.get(
    "/case/{pk}/visit/consultant-answers/", response=list[ConsultantAnswerSchema]
)
def get_visit_consultant_answers(request, pk: str):
    visit = get_case(request, pk)
    return (
        visit.consultant_answers.all()
        .order_by("question_id", "-created_at")
        .distinct("question_id")
    )


@router.get("/case/{pk}/visit/history/", response=CaseHistory)
def get_visit_history(request, pk: str, offset: int = 0, limit: int = 100):
    visit = get_case(request, pk)

    client_answers = visit.client_answers.all().order_by("-created_at")
    consultant_answers = visit.consultant_answers.all().order_by("-created_at")
    return {
        "client_answers": client_answers[offset : offset + limit],
        "consultant_answers": consultant_answers[offset : offset + limit],
    }


@router.post("/case/{pk}/submit/", auth=None, response=SubmitCaseResponse)
def submit_case(request, pk: str, answers: SubmitCaseSchema):
    """Submit client answers for a case."""
    pk = strip_id(pk)

    visit = get_object_or_404(Visit, case_id=pk)
    if request.user.is_authenticated:
        if not verify_access_to_location(visit.case.location, request.user):
            raise PermissionError("User does not have access to this location")

    try:
        record_client_answers(
            visit,
            answers.answers,
            request.user if request.user.is_authenticated else None,
        )
    except ValueError as e:
        raise HttpError(400, str(e)) from e

    return {"success": True}


@router.post("/case/{pk}/consultant/submit/", response=SubmitCaseResponse)
def submit_consultant_case(request, pk: str, answers: SubmitCaseSchema):
    visit = get_case(request, pk)
    warnings = record_consultant_answers(visit, answers.answers, request.user)

    return {"success": True, "warnings": warnings}


@router.post("/case/{pk}/tests/", response=SubmitCaseResponse)
def update_case_tests(request, pk: str, test_pks: list[int]):
    visit = get_case(request, pk)
    warnings = []

    exisitng = set(visit.tests.values_list("test_kind_id", flat=True))
    new = set(test_pks) - exisitng

    tests = [Test(visit=visit, test_kind_id=test_kind_id) for test_kind_id in new]
    Test.objects.bulk_create(tests)

    visit.status = VisitStatus.CONSULTANT_SUBMITTED
    visit.save()

    return {"success": True, "warnings": warnings}


@router.post("/case/{pk}/status/", response=SubmitCaseResponse)
def update_case_status(request, pk: str, status: str):
    """Update status for a case."""
    visit = get_case(request, pk)
    if status not in dict(VisitStatus.choices):
        raise ValueError(f"Invalid status: {status}")
    visit.status = status
    visit.save()
    return {"success": True}


@router.post("/case/{pk}/tests/results/", response=SubmitCaseResponse)
def update_case_test_results(request, pk: str, test_results: dict[int, str]):
    visit = get_case(request, pk)
    test_kinds = visit.tests.all()
    warnings = []

    for nr, label in test_results.items():
        test = test_kinds.filter(test_kind__number=nr).first()
        if not test:
            warnings.append(
                f"No test found for test kind number {nr} in case {visit.case.human_id}."
            )
            continue

        option = test.test_kind.result_options.filter(label=label).first()

        if not option:
            warnings.append(
                f"No option found for label '{label}' in "
                f"test kind {test.test_kind.name} for case {visit.case.human_id}."
            )
            continue

        test.test_results.create(result_option=option, user=request.user)


@router.post("/case/{pk}/tags/", response=SubmitCaseResponse)
def update_case_tags(request, pk: str, tags: list[str]):
    """Update tags for a case."""
    visit = get_case(request, pk)
    visit.tags.clear()
    # This is necessary for some reason, otherwise changes are not stored
    visit.save()
    visit.tags = tags
    visit.save()
    return {"success": True}


@router.post("/case/create/", response=CreateCaseResponse)
def create_case_view(request, data: CreateCaseSchema):
    """Create a new case from a questionnaire."""
    case = create_case(data.location_id, request.user, data.external_id)
    create_visit(case, get_object_or_404(Questionnaire, pk=data.questionnaire_id))

    link = get_case_link(case)

    if data.phone:
        try:
            send_case_link(case, data.phone)
        except Exception as e:
            logger.error(
                "Failed to send case link to phone number %s: %s", data.phone, e
            )

    return CreateCaseResponse(link=link, case_id=case.human_id)


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


@router.post("/cases/", response=list[CaseListingSchema])
@paginate(PageNumberPagination, page_size=20)
def list_cases(request, filters: CaseFilters):
    """List all cases the user has access to."""
    consultant = get_object_or_404(Consultant, user=request.user)
    django_filters = filters.get_django_filters()

    visits = (
        annotate_last_modified(
            Visit.objects.filter(case__location__in=consultant.locations.all())
            .select_related(
                "case", "questionnaire", "case__connection", "case__location"
            )
            .prefetch_related("client_answers", "consultant_answers", "tests")
        )
        .order_by("-last_modified_at")
        .filter(django_filters)
    )

    return visits


@router.get("/case/status/options/", response=list[OptionSchema])
def get_case_status_options(request):  # pylint: disable=unused-argument
    """Get options for case status."""
    return [
        {"label": str(label), "value": str(value)}
        for value, label in VisitStatus.choices
    ]


@router.get("/case/tags/options/", response=list[str])
def get_case_tags_options(request):
    """Get options for case tags."""
    consultant = get_object_or_404(Consultant, user=request.user)
    visits = (
        Visit.objects.filter(case__location__in=consultant.locations.all())
        .exclude(tags__isnull=True)
        .exclude(tags=[])
    )

    distinct_tags = (
        visits.annotate(tag=Func(F("tags"), function="unnest"))
        .values("tag")
        .distinct()
        .values_list("tag", flat=True)
    )

    return sorted(distinct_tags)


@router.get("/client/{pk}/cases/", response=list[CaseListingSchema])
@paginate(PageNumberPagination, page_size=20)
def list_client_cases(request, pk: str):
    """List all cases for a specific client the user has access to."""
    consultant = get_object_or_404(Consultant, user=request.user)
    client_id = strip_id(pk)

    visits = annotate_last_modified(
        Visit.objects.filter(
            case__location__in=consultant.locations.all(),
            case__connection__client__id=client_id,
        )
        .select_related("case", "questionnaire", "case__connection", "case__location")
        .prefetch_related("client_answers", "consultant_answers", "test_results")
    ).order_by("-last_modified_at")

    return visits


@router.get("/questionnaires/", response=list[QuestionnaireListingSchema], auth=None)
def list_questionnaires(request):  # pylint: disable=unused-argument
    """List all questionnaires."""
    questionnaires = Questionnaire.objects.all().only("id", "name")
    return questionnaires


@router.get("/tests/", response=list[TestCategorySchema])
def list_tests(request):  # pylint: disable=unused-argument
    """List all tests."""
    return TestCategory.objects.prefetch_related(
        "test_kinds",
        "test_kinds__test_bundles",
    ).all()


@router.get("/tests/{pk}/result-options/", response=list[TestResultOptionSchema])
def list_test_result_options(request, pk: int):  # pylint: disable=unused-argument
    """List all test result options for a given test kind."""
    test_kind = get_object_or_404(
        TestKind.objects.prefetch_related("result_options"), pk=pk
    )
    return test_kind.result_options.all()
