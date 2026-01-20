import logging

import phonenumbers
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Func
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import get_language
from django.views.decorators.csrf import csrf_exempt
from ninja import File, Form, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile
from ninja.pagination import PageNumberPagination, paginate

import tenants.auth
from core.auth import auth_2fa_or_trusted
from sure.cases import (
    annotate_last_modified,
    get_case_tests_with_latest_results,
    get_test_results,
    prefetch_questionnaire,
)
from sure.client_service import can_connect_case
from sure.client_service import connect_case as connect_case_service
from sure.client_service import (
    create_case,
    create_visit,
    get_case,
    get_case_link,
    get_case_unverified,
    human_format_phone_number,
    location_can_view_case,
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
    FreeFormTest,
    Questionnaire,
    ResultInformation,
    Test,
    TestCategory,
    TestKind,
    TestResult,
    Visit,
    VisitDocument,
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
from texts.translate import translate

logger = logging.getLogger(__name__)


router = Router()


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

    # Handle authenticated users
    if auth_2fa_or_trusted(request):
        consultant = request.user.consultant
        if not location_can_view_case(
            consultant.locations.all().values_list("id", flat=True), visit.case
        ):
            return 403, {
                "success": False,
                "message": "User does not have access to this case's location",
            }
        return prefetch_questionnaire(location=visit.case.location, internal=False).get(
            pk=visit.questionnaire.pk
        )

    # Handle unauthenticated users, case submitted but key not set
    if visit.status == VisitStatus.CLIENT_SUBMITTED and visit.case.key == "":
        return 302, {
            "success": False,
            "message": "Questionnaire already submitted, key not set",
        }

    # Case is already submitted, deny access
    if visit.status != VisitStatus.CREATED:
        return 403, {
            "success": False,
            "message": "Access denied to the case questionnaire",
        }

    # Get questionnaire for clients
    location = visit.case.location
    questionnaire = prefetch_questionnaire(location=location, internal=False).get(
        pk=visit.questionnaire.pk
    )

    return questionnaire


@router.post(
    "/case/{pk}/send-token/", auth=None, response={200: StatusSchema, 400: StatusSchema}
)
def send_token(request: HttpRequest, pk: str, phone_number: PhoneNumberSchema):
    """Send a token to the given phone number for accessing the case."""
    visit = get_case_unverified(pk)
    if not phone_number.phone_number:
        return 400, StatusSchema(success=False, message="Phone number is required")
    request.session["phone_number"] = phone_number.phone_number

    if not can_connect_case(visit.case):
        return 400, StatusSchema(success=False, message="Case cannot be connected")

    try:
        send_token_service(phone_number.phone_number, visit.case)
    except (ValueError, phonenumbers.NumberParseException) as e:
        return 400, StatusSchema(success=False, message=str(e))

    return StatusSchema(success=True, message=phone_number.phone_number)


@router.post(
    "/case/{pk}/connect/", auth=None, response={200: StatusSchema, 400: StatusSchema}
)
@inject_language
def connect_case(request: HttpRequest, pk: str, data: ConnectSchema):
    visit = get_case_unverified(pk)

    if not can_connect_case(visit.case):
        raise HttpError(400, translate("case-cannot-be-connected"))

    if "phone_number" not in request.session:
        raise HttpError(400, translate("phone-number-not-in-session"))

    if request.session["phone_number"] != data.phone_number:
        raise HttpError(400, translate("phone-number-mismatch"))

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

    questionnaire = prefetch_questionnaire(visit.case.location, internal=True).get(
        pk=visit.questionnaire.pk
    )

    return questionnaire


@router.get("/case/{pk}/phone/", response=StatusSchema)
def get_phone_number(request, pk: str):
    """Get the phone number associated with a case, if the user has access."""
    visit = get_case(request, pk)
    if not verify_access_to_location(visit.case.location, request.user):
        raise PermissionError("User does not have access to this location")

    if not hasattr(visit.case, "connection"):
        return StatusSchema(
            success=False, message=translate("no-phone-number-associated")
        )
    phone_number = visit.case.connection.client.contact.phone_number
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
            success=False, message=translate("no-phone-number-associated")
        )


@router.get("/case/{pk}/visit/", response=CaseListingSchema)
@inject_language
def get_visit(request, pk: str):
    """Get the client answers for a case."""

    visit = get_case(request, pk)
    return visit


@router.get("/case/{pk}/language/", response=str, auth=None)
def get_case_language(request, pk: str):
    """Get the language for a case."""
    case = get_object_or_404(Case.objects.all(), pk=strip_id(pk))
    return case.language


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

    client_answers = (
        visit.client_answers.all().order_by("-created_at").select_related("question")
    )
    consultant_answers = (
        visit.consultant_answers.all()
        .order_by("-created_at")
        .select_related("question")
    )
    tests = visit.tests.all().order_by("-created_at").select_related("test_kind")

    results = (
        TestResult.objects.filter(test__visit=visit)
        .order_by("-created_at")
        .select_related("result_option", "test", "test__test_kind")
    )
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
            raise PermissionError(translate("no-access-location"))

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
@inject_language
def get_case_tests(request, pk: str):
    visit = get_case(request, pk)
    return get_case_tests_with_latest_results(visit)


@router.get("/case/{pk}/free-form-tests/", response=list[FreeFormTestSchema])
@inject_language
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

    if status == VisitStatus.RESULTS_SENT.value:
        raise ValueError(translate("cannot-set-results-sent"))

    with transaction.atomic():
        visit.logs.create(
            action=f"Status changed to {status}",
            user=request.user,
        )
        visit.status = status
        visit.save(update_fields=["status"])
    return {"success": True}


@router.post("/case/{pk}/update-internal-id/", response=StatusSchema)
@inject_language
def update_case_internal_id(request, pk: str, internal_id: Form[str]):
    visit = get_case(request, pk)
    old_id = visit.case.external_id
    visit.case.external_id = internal_id
    visit.case.save(update_fields=["external_id"])
    visit.logs.create(
        action=f"Internal ID updated from  {old_id} to {internal_id}",
        user=request.user,
    )
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
                translate("no-test-found-for-number").format(
                    number=nr, case=visit.case.human_id
                )
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


@router.post(
    "/case/{pk}/documents/create", response={400: StatusSchema, 200: StatusSchema}
)
@inject_language
def upload_document(request, pk: str, file: File[UploadedFile], name: Form[str]):
    """Update documents for a case."""
    visit = get_case(request, pk)
    document = VisitDocument(
        visit=visit,
        document=file,
        name=name,
        user=request.user,
        hidden=False,
    )
    try:
        document.full_clean()
    except ValidationError as e:
        return 400, {
            "success": False,
            "message": " ".join(e.messages),
        }
    document.save()
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
@inject_language
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
@inject_language
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
@inject_language
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
    visit.case.language = get_language()
    visit.case.save(update_fields=["language"])
    return {"success": True}


@router.post(
    "/case/create/",
    response=CreateCaseResponse,
    auth=[
        auth_2fa_or_trusted,
        tenants.auth.auth_tenant_api_token,
    ],
)
@csrf_exempt
@inject_language
def create_case_view(request, data: CreateCaseSchema):
    """Create a new case from a questionnaire."""
    case = create_case(data.location_id, request.user, data.external_id, data.language)
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


@router.post(
    "/cases/",
    response=list[CaseListingSchema],
    auth=[auth_2fa_or_trusted, tenants.auth.auth_tenant_api_token],
)
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
        {"label": translate(str(value)), "value": str(value)}
        for value, _ in VisitStatus.choices
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
    client_id = strip_id(pk)

    return Case.objects.filter(
        connection__client__id=client_id,
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
        "test_kinds__result_options",
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
        test__test_kind__rapid=False,
    ).exists():
        if visit.status == VisitStatus.CLOSED and not auth_2fa_or_trusted(request):
            return {"label": visit.get_status_display(), "value": visit.status}

        return {"label": translate("results-not-available"), "value": "not_available"}

    return {"label": visit.get_status_display(), "value": visit.status}


@router.get("/results/{pk}/non-sms/", response=list[TestSchema])
@inject_language
def get_non_sms_results(request, pk: str):
    visit = get_case(request, pk)

    return get_case_tests_with_latest_results(visit, filter_client=False).filter(
        test_kind__rapid=False
    )


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
    as_client = as_client or not auth_2fa_or_trusted(request)

    if as_client and not visit.results_visible_for_client:
        raise HttpError(400, "Results not ready for this case yet")

    if as_client and visit.status != VisitStatus.RESULTS_SEEN:
        visit.status = VisitStatus.RESULTS_SEEN
        visit.save(update_fields=["status"])

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
    if not auth_2fa_or_trusted(request) and not visit.results_visible_for_client:
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
    if visit.status not in [VisitStatus.RESULTS_RECORDED, VisitStatus.TESTS_RECORDED]:
        raise HttpError(
            400,
            translate("cannot-publish-results-status"),
        )

    test_results = get_test_results(visit)

    if test_results.filter(
        result_option__information_by_sms=False, test__test_kind__rapid=False
    ).exists():
        raise HttpError(400, translate("cannot-publish-non-sms-results"))

    with transaction.atomic():
        visit.logs.create(
            action="Results published to client",
            user=request.user,
        )
        visit.status = VisitStatus.RESULTS_SENT
        visit.save(update_fields=["status"])

    send_results_link(visit.case)

    return {"success": True}
