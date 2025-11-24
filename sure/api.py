import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Func, Prefetch
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone, translation
from django.utils.translation import get_language_from_request
from ninja import Form, Query, Router, Schema
from ninja.errors import HttpError
from ninja.pagination import PageNumberPagination, paginate
from ninja.utils import contribute_operation_args

from sure.cases import annotate_last_modified
from sure.client_service import can_connect_case
from sure.client_service import connect_case as connect_case_service
from sure.client_service import (
    create_case,
    create_visit,
    get_case,
    get_case_link,
    get_case_unverified,
    record_client_answers,
    record_consultant_answers,
    send_case_link,
)
from sure.client_service import send_token as send_token_service
from sure.client_service import strip_id, verify_access_to_location
from sure.models import (
    Case,
    ClientOption,
    ClientQuestion,
    ConsultantOption,
    ConsultantQuestion,
    FreeFormTest,
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
    ConnectSchema,
    ConsultantAnswerSchema,
    CreateCaseResponse,
    CreateCaseSchema,
    FreeFormTestSchema,
    InternalQuestionnaireSchema,
    OptionSchema,
    PhoneNumberSchema,
    QuestionnaireListingSchema,
    QuestionnaireSchema,
    RelatedCaseSchema,
    StatusSchema,
    SubmitCaseResponse,
    SubmitCaseSchema,
    SubmitTestResultsSchema,
    SubmitTestsSchema,
    TestCategorySchema,
    TestResultOptionSchema,
    TestSchema,
)
from tenants.models import Consultant

logger = logging.getLogger(__name__)


def _activate_language_for_request(request, lang: str | None = None):
    if lang is None:
        lang = (
            get_language_from_request(request)
            or settings.MODELTRANSLATION_DEFAULT_LANGUAGE
        )

    if lang:
        translation.activate(lang)


class LangSchema(Schema):
    lang: str | None = settings.MODELTRANSLATION_DEFAULT_LANGUAGE


def inject_language(func: Callable) -> Callable:
    """Inject language parameter into Django Ninja endpoint."""

    @wraps(func)
    def view_with_language(request: HttpRequest, **kwargs: Any) -> Any:
        # Extract the language parameter that Ninja injected
        lang = kwargs.pop("lang", None)

        _activate_language_for_request(request, lang.lang)

        return func(request, **kwargs)

    contribute_operation_args(
        view_with_language,
        arg_name="lang",
        arg_type=LangSchema,
        arg_source=Query(...),  # type: ignore
    )

    return view_with_language


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


@router.get(
    "/case/{pk}/questionnaire/",
    response={200: QuestionnaireSchema, 302: StatusSchema, 403: StatusSchema},
    auth=None,
)
@inject_language
def get_case_questionnaire(request, pk: str):  # pylint: disable=unused-argument
    """Get the questionnaire associated with a case."""
    pk = strip_id(pk)

    visit = get_object_or_404(Visit, case_id=pk)
    if visit.status == VisitStatus.CLIENT_SUBMITTED and visit.case.key == "":
        return 302, {
            "success": False,
            "message": "Questionnaire already submitted, key not set",
        }

    if visit.status != VisitStatus.CREATED and request.user.is_authenticated is False:
        return 403, {
            "success": False,
            "message": "Access denied to the case questionnaire",
        }

    questionnaire = _prefetch_questionnaire().get(pk=visit.questionnaire.pk)

    return questionnaire


@router.post(
    "/case/{pk}/send-token/", auth=None, response={200: StatusSchema, 400: StatusSchema}
)
def send_token(request: HttpRequest, pk: str, phone_number: PhoneNumberSchema):
    """Send a token to the given phone number for accessing the case."""
    visit = get_case_unverified(pk)
    request.session["phone_number"] = phone_number.phone_number

    if not can_connect_case(visit.case):
        return 400, StatusSchema(success=False, message="Case cannot be connected")

    try:
        send_token_service(phone_number.phone_number, visit.case)
    except ValueError as e:
        return 400, StatusSchema(success=False, message=str(e))
    return StatusSchema(success=True, message=phone_number.phone_number)


@router.post(
    "/case/{pk}/connect/", auth=None, response={200: StatusSchema, 400: StatusSchema}
)
@inject_language
def connect_case(request: HttpRequest, pk: str, data: ConnectSchema):
    visit = get_case_unverified(pk)

    if not can_connect_case(visit.case):
        raise HttpError(400, "Case cannot be connected")

    if "phone_number" not in request.session:
        raise HttpError(400, "Phone number not provided. Please request a token first.")

    if request.session["phone_number"] != data.phone_number:
        raise HttpError(
            400, "Phone number does not match the one used for token request."
        )

    try:
        contact = connect_case_service(
            visit.case, data.phone_number, data.token, data.consent
        )
    except ValueError as e:
        return 400, StatusSchema(success=False, message=str(e))
    if contact is None:
        return 400, StatusSchema(success=False, message="Failed to connect case")

    return StatusSchema(success=True, message="Case connected successfully")


@router.get("/case/{pk}/internal/", response=InternalQuestionnaireSchema)
@inject_language
def get_case_internal(request, pk: str):
    """Get the internal questionnaire associated with a case."""
    visit = get_case(request, pk)

    questionnaire = _prefetch_questionnaire(internal=True).get(
        pk=visit.questionnaire.pk
    )

    return questionnaire


@router.get("/case/{pk}/visit/", response=CaseListingSchema)
@inject_language
def get_visit(request, pk: str):
    """Get the client answers for a case."""

    visit = get_case(request, pk)
    return visit


@router.get("/case/{pk}/visit/client-answers/", response=list[ClientAnswerSchema])
@inject_language
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
@inject_language
def get_visit_consultant_answers(request, pk: str):
    visit = get_case(request, pk)
    return (
        visit.consultant_answers.all()
        .order_by("question_id", "-created_at")
        .distinct("question_id")
    )


@router.get("/case/{pk}/visit/history/", response=CaseHistory)
@inject_language
def get_visit_history(request, pk: str, offset: int = 0, limit: int = 100):
    visit = get_case(request, pk)

    client_answers = visit.client_answers.all().order_by("-created_at")
    consultant_answers = visit.consultant_answers.all().order_by("-created_at")
    return {
        "client_answers": client_answers[offset : offset + limit],
        "consultant_answers": consultant_answers[offset : offset + limit],
    }


@router.post("/case/{pk}/submit/", auth=None, response=SubmitCaseResponse)
@inject_language
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
@inject_language
def submit_consultant_case(request, pk: str, answers: SubmitCaseSchema):
    visit = get_case(request, pk)
    warnings = record_consultant_answers(visit, answers.answers, request.user)

    return {"success": True, "warnings": warnings}


@router.post("/case/{pk}/tests/", response=SubmitCaseResponse)
@inject_language
def update_case_tests(request, pk: str, data: SubmitTestsSchema):
    visit = get_case(request, pk)
    warnings = []

    test_pks = data.test_kind_ids

    existing = set(visit.tests.values_list("test_kind_id", flat=True))
    new = set(test_pks) - existing

    tests = [
        Test(visit=visit, test_kind_id=test_kind_id, user=request.user)
        for test_kind_id in new
    ]
    Test.objects.bulk_create(tests)

    free_form_tests = data.free_form_tests
    for test_name in free_form_tests:
        if test_name.strip() == "":
            continue
        FreeFormTest.objects.get_or_create(
            visit=visit, name=test_name, user=request.user
        )

    with transaction.atomic():
        visit.status = VisitStatus.TESTS_RECORDED
        visit.save(update_fields=["status"])

    return {"success": True, "warnings": warnings}


@router.get("/case/{pk}/tests/", response=list[TestSchema])
def get_case_tests(request, pk: str):
    visit = get_case(request, pk)
    tests = (
        visit.tests.select_related("test_kind")
        .prefetch_related("results", "results__result_option")
        .all()
    )
    return tests


@router.get("/case/{pk}/free-form-tests/", response=list[FreeFormTestSchema])
def get_case_free_form_tests(request, pk: str):
    visit = get_case(request, pk)
    free_form_tests = visit.free_form_tests.all()
    return free_form_tests


@router.post("/case/{pk}/status/", response=SubmitCaseResponse)
@inject_language
def update_case_status(request, pk: str, status: str):
    """Update status for a case."""
    visit = get_case(request, pk)
    if status not in dict(VisitStatus.choices):
        raise ValueError(f"Invalid status: {status}")
    with transaction.atomic():
        visit.status = status
        visit.save(update_fields=["status"])
    return {"success": True}


@router.post("/case/{pk}/tests/results/", response=SubmitCaseResponse)
@inject_language
def update_case_test_results(request, pk: str, test_results: SubmitTestResultsSchema):
    visit = get_case(request, pk)
    test_kinds = visit.tests.all()
    warnings = []

    for result in test_results.test_results:
        nr = result.number
        label = result.label
        note = result.note

        test = test_kinds.filter(test_kind__number=nr).first()
        if not test:
            warnings.append(
                f"No test found for test kind number {nr} in case {visit.case.human_id}."
            )
            continue

        latest_result = test.results.order_by("-created_at").first()
        if (
            latest_result
            and latest_result.result_option.label == label
            and latest_result.note == note
        ):
            warnings.append(
                f"Test result for test kind {test.test_kind.name} in case "
                f"{visit.case.human_id} is already '{label}'. Skipping."
            )
            continue

        option = test.test_kind.result_options.filter(label=label).first()

        if not option:
            warnings.append(
                f"No option found for label '{label}' in "
                f"test kind {test.test_kind.name} for case {visit.case.human_id}."
            )
            continue

        test.results.create(result_option=option, note=note, user=request.user)

    for free_form_result in test_results.free_form_results:
        test = visit.free_form_tests.filter(id=free_form_result.id).first()
        if not test:
            warnings.append(
                f"No free form test found with id {free_form_result.id} in case {visit.case.human_id}."
            )
            continue
        test.result = free_form_result.result
        test.result_recorded_at = timezone.now()
        test.save(update_fields=["result", "result_recorded_at"])

    with transaction.atomic():
        visit.status = VisitStatus.RESULTS_RECORDED
        visit.save(update_fields=["status"])
    return {"success": True, "warnings": warnings}


@router.post("/case/{pk}/tags/", response=SubmitCaseResponse)
@inject_language
def update_case_tags(request, pk: str, tags: list[str]):
    """Update tags for a case."""
    with transaction.atomic():
        visit = get_case(request, pk)
        visit.tags = tags
        visit.save(update_fields=["tags"])
    return {"success": True}


@router.post(
    "/case/{pk}/set-key/", response={200: StatusSchema, 400: StatusSchema}, auth=None
)
def set_case_key(request, pk: str, key: Form["str"]):
    visit = get_case_unverified(pk)

    if visit.status != VisitStatus.CLIENT_SUBMITTED:
        raise HttpError(400, "Cannot set key for a case that is not in CREATED status")

    try:
        visit.case.set_key(key)
    except ValueError as e:
        return 400, {"success": False, "message": str(e)}
    except ValidationError as e:
        print(e.messages)
        return 400, {"success": False, "message": e.messages}
    return {"success": True}


@router.post("/case/{pk}/communication/", auth=None)
def view_case_communication(request, pk: str, key: Form["str"]):
    """View or log communication related to a case."""
    visit = get_case_unverified(pk)

    if not visit.case.check_key(key):
        raise HttpError(403, "Invalid access key for the case")

    if visit.status != VisitStatus.RESULTS_SENT:
        raise HttpError(400, "Results not ready for this case yet")

    # Log communication and return information
    return "ok"


@router.post("/case/create/", response=CreateCaseResponse)
@inject_language
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
@inject_language
def get_questionnaire(request, pk: int):  # pylint: disable=unused-argument
    """Get a questionnaire by its ID."""
    questionnaire = _prefetch_questionnaire().get(pk=pk)
    return questionnaire


@router.get("/internal/questionnaires/{pk}/", response=InternalQuestionnaireSchema)
@inject_language
def get_internal_questionnaire(request, pk: int):  # pylint: disable=unused-argument
    """Get a questionnaire by its ID, including consultant questions."""
    questionnaire = _prefetch_questionnaire(internal=True).get(pk=pk)
    return questionnaire


@router.post("/cases/", response=list[CaseListingSchema])
@inject_language
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
@inject_language
def get_case_status_options(request):  # pylint: disable=unused-argument
    """Get options for case status."""
    return [
        {"label": str(label), "value": str(value)}
        for value, label in VisitStatus.choices
    ]


@router.get("/case/tags/options/", response=list[str])
@inject_language
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


@router.get("/client/{pk}/cases/", response=list[RelatedCaseSchema])
@inject_language
@paginate(PageNumberPagination, page_size=20)
def list_client_cases(request, pk: str):
    """List all cases for a specific client the user has access to."""
    consultant = get_object_or_404(Consultant, user=request.user)
    client_id = strip_id(pk)

    return Case.objects.filter(
        connection__client__id=client_id,
        location__in=consultant.locations.all(),
    ).order_by("-created_at")


@router.get("/questionnaires/", response=list[QuestionnaireListingSchema], auth=None)
@inject_language
def list_questionnaires(request):  # pylint: disable=unused-argument
    """List all questionnaires."""
    questionnaires = Questionnaire.objects.all().only("id", "name")
    return questionnaires


@router.get("/tests/", response=list[TestCategorySchema])
@inject_language
def list_tests(request):  # pylint: disable=unused-argument
    """List all tests."""
    return TestCategory.objects.prefetch_related(
        "test_kinds",
        "test_kinds__test_bundles",
    ).all()


@router.get("/tests/{pk}/result-options/", response=list[TestResultOptionSchema])
@inject_language
def list_test_result_options(request, pk: int):  # pylint: disable=unused-argument
    """List all test result options for a given test kind."""
    test_kind = get_object_or_404(
        TestKind.objects.prefetch_related("result_options"), pk=pk
    )
    return test_kind.result_options.all()
