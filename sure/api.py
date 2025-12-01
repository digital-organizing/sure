import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Func, OuterRef, Prefetch, Subquery
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import File, Form, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile
from ninja.pagination import PageNumberPagination, paginate

from core.auth import auth_2fa_or_trusted
from sure.cases import annotate_last_modified
from sure.client_service import can_connect_case
from sure.client_service import connect_case as connect_case_service
from sure.client_service import (
    create_case,
    create_visit,
    get_case,
    get_case_link,
    get_case_unverified,
    human_format_phone_number,
    record_client_answers,
    record_consultant_answers,
    send_case_link,
    send_results_link,
)
from sure.client_service import send_token as send_token_service
from sure.client_service import strip_id, verify_access_to_location
from sure.lang import inject_language
from sure.models import (
    Case,
    ClientOption,
    ClientQuestion,
    ConsultantOption,
    ConsultantQuestion,
    FreeFormTest,
    Questionnaire,
    ResultInformation,
    Section,
    Test,
    TestCategory,
    TestKind,
    TestResult,
    Visit,
    VisitLog,
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
    DocumentAccessSchema,
    DocumentSchema,
    FreeFormTestSchema,
    InternalQuestionnaireSchema,
    NoteSchema,
    OptionSchema,
    PhoneNumberSchema,
    QuestionnaireListingSchema,
    QuestionnaireSchema,
    RelatedCaseSchema,
    ResultInformationSchema,
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


router = Router()


def _prefetch_questionnaire(internal=False, excluded_question_ids=None):
    client_questions_qs = ClientQuestion.objects.order_by("order").prefetch_related(
        Prefetch("options", queryset=ClientOption.objects.order_by("order"))
    )

    if excluded_question_ids:
        client_questions_qs = client_questions_qs.exclude(
            id__in=excluded_question_ids, optional_for_centers=True
        )

    query = Questionnaire.objects.prefetch_related(
        Prefetch(
            "sections",
            queryset=Section.objects.order_by("order").prefetch_related(
                Prefetch(
                    "client_questions",
                    queryset=client_questions_qs,
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


def get_test_results(visit):
    return (
        TestResult.objects.filter(test__visit=visit)
        .annotate(
            is_latest=Subquery(
                TestResult.objects.filter(test_id=OuterRef("test_id"))
                .order_by("-created_at")
                .values("id")[:1]
            )
        )
        .filter(id=F("is_latest"))
    )


def get_case_tests_with_latest_results(
    visit: Visit, filter_client=None
) -> QuerySet[Test]:
    test_latest_result_ids = get_test_results(visit)

    if (
        filter_client is True
    ):  # Clients are only allowed to see results if all results are information_by_sms=True
        if test_latest_result_ids.filter(
            result_option__information_by_sms=False
        ).exists():
            return Test.objects.none()
    if filter_client is False:  # Return only results that are not information_by_sms
        test_latest_result_ids = test_latest_result_ids.filter(
            result_option__information_by_sms=False
        )

    test_latest_result_ids = test_latest_result_ids.values_list("id", flat=True)

    visit_with_latest = (
        Visit.objects.filter(pk=visit.pk)
        .prefetch_related(
            Prefetch(
                "tests",
                queryset=Test.objects.prefetch_related(
                    Prefetch(
                        "results",
                        queryset=TestResult.objects.filter(
                            id__in=list(test_latest_result_ids)
                        ).prefetch_related("result_option"),
                    )
                ),
            )
        )
        .get()
    )

    return visit_with_latest.tests


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

    location = visit.case.location
    excluded_ids = location.excluded_questions.values_list("id", flat=True)

    questionnaire = _prefetch_questionnaire(excluded_question_ids=excluded_ids).get(
        pk=visit.questionnaire.pk
    )

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


@router.get("/case/{pk}/phone/", response=StatusSchema)
def get_phone_number(request, pk: str):
    """Get the phone number associated with a case, if the user has access."""
    visit = get_case(request, pk)
    if not verify_access_to_location(visit.case.location, request.user):
        raise PermissionError("User does not have access to this location")

    try:
        phone_number = (
            visit.case.connection.client.contact.phone_number
            if visit.case.connection
            else None
        )
    except Case.connection.RelatedObjectDoesNotExist:
        phone_number = None
    if phone_number:
        VisitLog.objects.create(
            visit=visit,
            action="Phone number accessed",
            user=request.user,
        )
        return StatusSchema(
            success=True, message=human_format_phone_number(phone_number)
        )
    else:
        return StatusSchema(
            success=False, message="No phone number associated with this case"
        )


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
    tests = visit.tests.all().order_by("-created_at")

    results = TestResult.objects.filter(test__visit=visit).order_by("-created_at")
    log = visit.logs.all().order_by("-timestamp")

    return {
        "client_answers": client_answers[offset : offset + limit],
        "consultant_answers": consultant_answers[offset : offset + limit],
        "tests": tests[offset : offset + limit],
        "test_results": results[offset : offset + limit],
        "log": log[offset : offset + limit],
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
    return get_case_tests_with_latest_results(visit)


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
        visit.logs.create(
            action=f"Status changed to {status}",
            user=request.user,
        )
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


@router.post("/case/{pk}/documents/create", response=StatusSchema)
@inject_language
def upload_document(request, pk: str, file: File[UploadedFile], name: Form[str]):
    """Update documents for a case."""
    visit = get_case(request, pk)
    visit.documents.create(
        document=file,
        name=name,
        user=request.user,
        hidden=False,
    )
    return {"success": True}


@router.post("/case/{pk}/documents/", response=list[DocumentSchema], auth=None)
@inject_language
def list_documents(request, pk: str, key: Form[str] = "", as_staff=False):
    """List documents for a case. All if authenticted, else only non-hidden."""
    authenticted = auth_2fa_or_trusted(request)
    visit = get_case(request, pk) if authenticted else get_case_unverified(pk, key)
    as_client = not authenticted or not as_staff
    if as_client:
        return visit.documents.filter(hidden=False)
    return visit.documents.all()


@router.post("/case/{pk}/documents/{doc_pk}/set-hidden/", response=StatusSchema)
def set_document_hidden(request, pk: str, doc_pk: int, hidden: Form[bool]):
    """Set document hidden status for a case."""
    visit = get_case(request, pk)
    document = get_object_or_404(visit.documents, pk=doc_pk)
    document.hidden = hidden
    document.save(update_fields=["hidden"])
    return {"success": True}


@router.post(
    "/case/{pk}/documents/{doc_pk}/link/", response=DocumentAccessSchema, auth=None
)
def get_document_link(request, pk: str, doc_pk: int, key: Form[str] = ""):
    """Get a download link for a document."""
    authenticted = auth_2fa_or_trusted(request)
    visit = get_case(request, pk) if authenticted else get_case_unverified(pk, key)
    document = get_object_or_404(visit.documents, pk=doc_pk)
    if not authenticted and document.hidden:
        raise HttpError(403, "Access denied to this document")
    link = document.document.url
    return {"link": link}


@router.post("/case/{pk}/tags/", response=SubmitCaseResponse)
@inject_language
def update_case_tags(request, pk: str, tags: list[str]):
    """Update tags for a case."""
    with transaction.atomic():
        visit = get_case(request, pk)
        if visit.tags == tags:
            return {"success": True}
        visit.logs.create(
            action=f"Tags updated to {tags}",
            user=request.user,
        )
        visit.tags = tags
        visit.save(update_fields=["tags"])
    return {"success": True}


@router.post("/case/{pk}/notes/create", response=StatusSchema)
@inject_language
def add_case_note(request, pk: str, content: Form[str]):
    """Add a note to a case."""
    visit = get_case(request, pk)
    visit.notes.create(note=content, user=request.user)
    return {"success": True}


@router.post("/case/{pk}/notes/", response=list[NoteSchema], auth=None)
@inject_language
def list_case_notes(request, pk: str, key: Form[str] = "", as_staff=False):
    visit = (
        get_case(request, pk)
        if auth_2fa_or_trusted(request)
        else get_case_unverified(pk, key)
    )
    as_client = not auth_2fa_or_trusted(request) or not as_staff
    if as_client:
        return visit.notes.filter(hidden=False)
    return visit.notes.all()


@router.post("/case/{pk}/notes/{note_pk}/set-hidden/", response=StatusSchema)
def set_case_note_hidden(request, pk: str, note_pk: int, hidden: Form[bool]):
    """Set note hidden status for a case."""
    visit = get_case(request, pk)
    note = get_object_or_404(visit.notes, pk=note_pk)
    note.hidden = hidden
    note.save(update_fields=["hidden"])
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


@router.post("/case/create/", response=CreateCaseResponse)
@inject_language
def create_case_view(request, data: CreateCaseSchema):
    """Create a new case from a questionnaire."""
    case = create_case(data.location_id, request.user, data.external_id)
    visit = create_visit(
        case, get_object_or_404(Questionnaire, pk=data.questionnaire_id)
    )

    visit.logs.create(
        action="Case created",
        user=request.user,
    )

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


@router.post("/results/{pk}/status/", auth=None, response=OptionSchema)
def get_case_status(request, pk: str, key: Form[str] = ""):
    visit = (
        get_case(request, pk)
        if auth_2fa_or_trusted(request)
        else get_case_unverified(pk, key)
    )

    test_results = get_test_results(visit)

    if test_results.filter(
        result_option__information_by_sms=False,
    ).exists():
        if visit.status == VisitStatus.CLOSED and not auth_2fa_or_trusted(request):
            return {"label": visit.get_status_display(), "value": visit.status}

        return {"label": "Results not available", "value": "not_available"}

    return {"label": visit.get_status_display(), "value": visit.status}


@router.get("/results/{pk}/non-sms/", response=list[TestSchema])
def get_non_sms_results(request, pk: str):
    visit = get_case(request, pk)

    return get_case_tests_with_latest_results(visit, filter_client=False)


@router.post("/results/{pk}/client/", auth=None, response=list[TestSchema])
def get_client_results(request, pk: str, key: Form[str] = "", as_client=False):
    """
    Get client results for a case. Returns summarized results.

    :param request: Beschreibung
    :param pk: Beschreibung
    :type pk: str
    """
    visit = (
        get_case(request, pk)
        if auth_2fa_or_trusted(request)
        else get_case_unverified(pk, key)
    )
    if not auth_2fa_or_trusted(request) and visit.status != VisitStatus.RESULTS_SENT:
        raise HttpError(400, "Results not ready for this case yet")

    if as_client and visit.status != VisitStatus.RESULTS_SENT:
        raise HttpError(400, "Results not ready for this case yet")

    return get_case_tests_with_latest_results(visit, filter_client=True)


@router.post(
    "/results/{pk}/free-form-client/", auth=None, response=list[FreeFormTestSchema]
)
def get_client_free_form_results(request, pk: str, key: Form[str] = ""):
    visit = (
        get_case(request, pk)
        if auth_2fa_or_trusted(request)
        else get_case_unverified(pk, key)
    )
    if not auth_2fa_or_trusted(request) and visit.status != VisitStatus.RESULTS_SENT:
        raise HttpError(400, "Results not ready for this case yet")

    return visit.free_form_tests.filter(result__isnull=False)


@router.post("/results/{pk}/info/", auth=None, response=list[ResultInformationSchema])
def get_result_info(request, pk: str, key: Form[str] = ""):
    visit = (
        get_case(request, pk)
        if auth_2fa_or_trusted(request)
        else get_case_unverified(pk, key)
    )

    location = visit.case.location

    return ResultInformation.objects.filter(
        locations=location,
    ).select_related("option")


@router.post("/case/{pk}/publish/", response=StatusSchema)
@inject_language
def publish_case_results(request, pk: str):
    """Publish case results to the client."""
    visit = get_case(request, pk)
    if visit.status != VisitStatus.RESULTS_RECORDED:
        raise HttpError(
            400,
            "Cannot publish results for a case that is not in RESULTS_RECORDED status",
        )

    test_results = get_test_results(visit)

    if test_results.filter(result_option__information_by_sms=False).exists():
        raise HttpError(
            400, "Cannot publish results that are not marked as information_by_sms"
        )

    with transaction.atomic():
        visit.logs.create(
            action="Results published to client",
            user=request.user,
        )
        visit.status = VisitStatus.RESULTS_SENT
        visit.save(update_fields=["status"])

    send_results_link(visit.case)

    return {"success": True}
