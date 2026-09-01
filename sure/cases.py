from typing import Any, Dict, List, Optional, Tuple

from django.db.models import Count, F, OuterRef, Prefetch, Q, QuerySet, Subquery
from django.db.models.functions import Greatest
from django.utils.timezone import make_naive

from sure.forms import CohortFilterForm
from sure.models import (
    ClientAnswer,
    ClientOption,
    ClientQuestion,
    ConsultantAnswer,
    ConsultantOption,
    ConsultantQuestion,
    Questionnaire,
    Section,
    Test,
    TestKind,
    TestResult,
    Visit,
    VisitStatus,
)
from tenants.models import Location, Tenant


def annotate_last_modified(queryset: QuerySet[Visit]) -> QuerySet[Visit]:
    """Annotates each Visit with its last_modified timestamp, which is the
    latest created_at among:
    - The Visit itself
    - Related ClientAnswers
    - Related ConsultantAnswers
    - Related Tests
    - Related TestResults (through Tests)

    Returns:
        QuerySet[Visit]: The Visit queryset with last_modified annotation
    """
    latest_client_answer = (
        ClientAnswer.objects.filter(visit=OuterRef("pk"))
        .order_by("-created_at")
        .values("created_at")[:1]
    )

    latest_consultant_answer = (
        ConsultantAnswer.objects.filter(visit=OuterRef("pk"))
        .order_by("-created_at")
        .values("created_at")[:1]
    )

    latest_test = (
        Test.objects.filter(visit=OuterRef("pk"))
        .order_by("-created_at")
        .values("created_at")[:1]
    )

    latest_test_result = (
        TestResult.objects.filter(
            test__visit=OuterRef("pk"), test__deleted_at__isnull=True
        )
        .order_by("-created_at")
        .values("created_at")[:1]
    )

    return queryset.annotate(
        last_modified_at=Greatest(
            F("created_at"),
            Subquery(latest_client_answer),
            Subquery(latest_consultant_answer),
            Subquery(latest_test),
            Subquery(latest_test_result),
        )
    )


def annotate_latest_result(queryset: QuerySet[Test]) -> QuerySet[Test]:
    """Annotates each Test with its latest_result (TestResult).

    Returns:
        QuerySet[Test]: The Test queryset with latest_result annotation
    """
    latest_result_subquery = TestResult.objects.filter(test=OuterRef("pk")).order_by(
        "-created_at"
    )

    return queryset.annotate(latest_result=Subquery(latest_result_subquery[:1]))


def prefetch_questionnaire(location: Location, internal=False):
    client_questions_qs = ClientQuestion.objects.order_by("order").prefetch_related(
        Prefetch("options", queryset=ClientOption.objects.order_by("order"))
    )
    excluded_question_ids = location.excluded_questions.values_list("id", flat=True)
    included_question_ids = location.included_questions.values_list("id", flat=True)

    client_questions_qs = client_questions_qs.exclude(
        id__in=excluded_question_ids, optional_for_centers=True
    ).filter(Q(extra_for_centers=False) | Q(id__in=included_question_ids))

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
        TestResult.objects.filter(test__visit=visit, test__deleted_at__isnull=True)
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
            result_option__information_by_sms=False,
            test__test_kind__rapid=False,
        ).exists():
            return Test.objects.none()
    if filter_client is False:  # Return only results that are not information_by_sms
        test_latest_result_ids = test_latest_result_ids.filter(
            result_option__information_by_sms=False
        )

    test_latest_result_ids = test_latest_result_ids.values_list("id", flat=True)
    tests = Test.objects.all()
    if filter_client:
        tests = tests.filter(test_kind__rapid=False)

    visit_with_latest = (
        Visit.objects.filter(pk=visit.pk)
        .prefetch_related(
            Prefetch(
                "tests",
                queryset=tests.prefetch_related(
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


def get_export_dict(visit: Visit, test_kinds=None):
    record = {
        "id": visit.pk,
        "case_id": visit.case.human_id,
        "created_at": make_naive(visit.created_at),
        "internal_id": visit.case.external_id,
        "status": visit.status,
        "tags": ", ".join(visit.tags),
        "location": visit.case.location.name,
        "tenant": visit.case.location.tenant.name,
        "questionnaire": visit.questionnaire.name,
        "language": visit.case.language,
    }

    if hasattr(visit.case, "connection"):
        record["client_id"] = visit.case.connection.client_id

    record.update(get_client_answers_export(visit))
    record.update(get_consultant_answers_export(visit))
    record.update(get_test_results_export(visit, test_kinds=test_kinds))

    return record


def show_question(question, answers):
    # Use prefetched show_for_options if available to avoid .exists() query
    show_for_options = question.show_for_options.all()
    if not show_for_options:
        return True

    for option in show_for_options:
        option: ClientOption = option
        # answer record in answers dict contains 'codes' list
        answer = answers.get(option.question.code, None)
        if not answer:
            continue
        # Convert choice integers to strings to match option.code (a CharField)
        if any(str(choice) == option.code for choice in answer["codes"]):
            return True

    return False


def get_answer_codes(codes):
    if len(codes) == 0:
        return 99

    if len(codes) == 1:
        return codes[0]

    return ";".join(map(str, codes))


def get_answer_texts(texts):
    if len(texts) == 0 or all(text.strip() == "" for text in texts):
        return "missing"

    if len(texts) == 1:
        return texts[0]

    return ";".join(map(str, texts))


def _translate_answer_choices(choices, texts, options, lang):
    """
    Translates answer choices back to English using option metadata and language mapping.
    """
    answers_en = []
    for code, text in zip(choices, texts):
        option = options.get(str(code))
        if not option:
            text_en = text
        elif option.choices_en:
            original_choices = getattr(option, f"choices_{lang}", [])
            try:
                idx = original_choices.index(text)
                text_en = option.choices_en[idx]
            except ValueError:
                text_en = text
        elif option.allow_text:
            text_en = option.text_en + ": " + text if option.text_en else text
        else:
            text_en = option.text_en if option.text_en else text
        answers_en.append(text_en)
    return answers_en


def get_client_answers_export(visit: Visit):
    # Pre-group answers by question_id to avoid N queries per visit
    all_answers = list(visit.client_answers.all())
    all_answers.sort(key=lambda x: x.created_at, reverse=True)
    lang = visit.case.language
    answers_map = {}
    for ans in all_answers:
        if ans.question_id not in answers_map:
            answers_map[ans.question_id] = ans

    answers = {}

    for section in visit.questionnaire.sections.all():
        for question in section.client_questions.all():
            question: ClientQuestion = question

            if not show_question(question, answers):
                continue

            answer = answers_map.get(question.pk)
            if not answer:
                answer_record = {
                    "codes": [99],
                    "texts": ["missing"],
                }
            else:
                # Use prefetched options from the question
                options = {opt.code: opt for opt in question.options.all()}
                answers_en = _translate_answer_choices(
                    answer.choices, answer.texts, options, lang
                )

                answer_record = {
                    "codes": answer.choices,
                    "texts": answers_en,
                }

            answers[question.code] = answer_record

    output = {}
    for question_code, answer in answers.items():
        output[f"{question_code}_codes"] = get_answer_codes(answer["codes"])
        output[f"{question_code}_texts"] = ";".join(answer["texts"])  # ty: ignore[no-matching-overload]
    return output


def get_consultant_answers_export(visit: Visit):
    # Pre-group answers by question_id
    all_answers = list(visit.consultant_answers.all())
    all_answers.sort(key=lambda x: x.created_at, reverse=True)
    lang = visit.case.language
    answers_map = {}
    for ans in all_answers:
        if ans.question_id not in answers_map:  # type: ignore
            answers_map[ans.question_id] = ans  # type: ignore

    output = {}
    for question in visit.questionnaire.consultant_questions.all():
        question: ConsultantQuestion = question

        answer = answers_map.get(question.pk)
        if not answer:
            answer_record = {
                "codes": [99],
                "texts": ["missing"],
            }
        else:
            # Use prefetched options from the question
            options: dict[str, ClientOption] = {
                opt.code: opt for opt in question.options.all()
            }  # type: ignore
            answers_en = _translate_answer_choices(
                answer.choices, answer.texts, options, lang
            )

            answer_record = {
                "codes": answer.choices,
                "texts": answers_en,
            }
        output[f"{question.code}_codes"] = get_answer_codes(answer_record["codes"])
        output[f"{question.code}_texts"] = get_answer_texts(answer_record["texts"])
    return output


def get_test_results_export(visit: Visit, test_kinds=None):
    output = {}

    if test_kinds is None:
        test_kinds = TestKind.objects.all()

    # Pre-map visit tests for faster lookup
    visit_tests = {t.test_kind.pk: t for t in visit.tests.all()}

    for test_kind in test_kinds:
        test_kind: TestKind = test_kind

        output[f"{test_kind.name}"] = None
        if test_kind.interpretation_needed:
            output[f"{test_kind.name} [{test_kind.note}]"] = None

        test = visit_tests.get(test_kind.pk)

        if not test:
            continue

        # Use prefetched results, ordered by created_at desc
        results = list(test.results.all())
        results.sort(key=lambda x: x.created_at, reverse=True)
        result = results[0] if results else None

        if not result:
            output[f"{test_kind.name}"] = "no_result"
            continue
        output[f"{test_kind.name}"] = result.result_option.label_en
        if test_kind.interpretation_needed:
            output[f"{test_kind.name} [{test_kind.note}]"] = result.note

    return output


def _color_for_status(status):
    status_colors = {
        VisitStatus.CREATED: "bg-green-100",
        VisitStatus.CLIENT_SUBMITTED: "bg-yellow-100",
        VisitStatus.CONSULTANT_SUBMITTED: "bg-blue-600",
        VisitStatus.TESTS_RECORDED: "bg-blue-100",
        VisitStatus.RESULTS_RECORDED: "bg-primary-500",
        VisitStatus.CLOSED: "bg-gray-50",
    }
    return status_colors.get(status, "bg-gray-500")


def color_for_percentage(percentage: float) -> str:
    return f"bg-primary-{int(percentage * 9) * 100}" + (
        " text-white" if percentage > 0.5 else ""
    )


def dashboard_callback(request, context):
    context["form"] = CohortFilterForm(request.GET or None, request=request)
    return context


def _get_col(count: int, total: int) -> Dict[str, Any]:
    """Helper to format a single cell in the cohort table."""
    return {
        "value": count,
        "subtitle": f"{(count / total * 100):.1f}%" if total > 0 else "0.0%",
        "color": (color_for_percentage(count / total) if total > 0 else "bg-gray-500")
        + " text-right",
    }


def _build_cohort_data(
    query,
    group_by_fields: List[str],
    status_choices: List[Tuple],
    all_groups: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Generic cohort data builder that aggregates visits by status and a grouping field.

    Args:
        query: Base queryset of Visit objects
        group_by_fields: List of fields to group by (e.g., ['case__location__tenant__id', 'case__location__tenant__name'])
        status_choices: List of status choices (e.g., VisitStatus.choices)
        all_groups: Optional list of all possible groups (for including zero-count groups)
    """
    # Get total count once
    total = query.count()

    # Build the grouping fields for the query
    group_fields = group_by_fields + ["status"]

    # Aggregate counts per group and status in a single query
    grouped_counts = query.values(*group_fields).annotate(count=Count("id"))

    # Get status totals
    status_totals = query.values("status").annotate(count=Count("id"))
    status_totals_dict = {item["status"]: item["count"] for item in status_totals}

    # Organize the data by group
    group_data = {}

    for row in grouped_counts:
        # Extract group identifier (first field) and name (second field)
        group_id = row[group_by_fields[0]]
        group_name = (
            row[group_by_fields[1]] if len(group_by_fields) > 1 else str(group_id)
        )
        status = row["status"]
        count = row["count"]

        if group_id not in group_data:
            group_data[group_id] = {
                "name": group_name,
                "counts": {s[0]: 0 for s in status_choices},
                "total": 0,
            }

        group_data[group_id]["counts"][status] = count  # ty: ignore[invalid-assignment]
        group_data[group_id]["total"] += count

    # If all_groups provided, ensure all groups are included (even with 0 counts)
    if all_groups:
        rows = []
        for group in all_groups:
            group_id = group["id"]
            group_name = group["name"]

            if group_id in group_data:
                data = group_data[group_id]
            else:
                data = {
                    "name": group_name,
                    "counts": {s[0]: 0 for s in status_choices},
                    "total": 0,
                }

            rows.append(
                {
                    "header": {
                        "title": data["name"],
                        "subtitle": f"Total {data['total']}",
                    },
                    "cols": [
                        _get_col(data["counts"].get(status[0], 0), total)  # type: ignore
                        for status in status_choices
                    ],
                }
            )
    else:
        # Use only groups that have data
        rows = [
            {
                "header": {
                    "title": data["name"],
                    "subtitle": f"Total {data['total']}",
                },
                "cols": [
                    _get_col(data["counts"].get(status[0], 0), total)  # ty: ignore[unresolved-attribute]
                    for status in status_choices
                ],
            }
            for _, data in group_data.items()
        ]

    return {
        "headers": [
            {
                "title": status[1],
                "subtitle": f"Total {status_totals_dict.get(status[0], 0)}",
            }
            for status in status_choices
        ],
        "rows": rows,
    }


def case_cohort_by_tenants(filter: Optional[Dict] = None) -> Dict[str, Any]:
    """Generate cohort data grouped by tenants."""
    if filter is None:
        filter = {}

    query = Visit.objects.filter(**filter).select_related("case__location__tenant")

    # Get all tenants (optional - if you want to include tenants with 0 visits)
    all_tenants = list(Tenant.objects.values("id", "name"))

    return _build_cohort_data(
        query=query,
        group_by_fields=["case__location__tenant__id", "case__location__tenant__name"],
        status_choices=VisitStatus.choices,
        all_groups=all_tenants,  # Remove this if you only want tenants with visits
    )


def case_cohort_by_location(
    tenant: Tenant, filter: Optional[Dict] = None
) -> Dict[str, Any]:
    """Generate cohort data grouped by locations for a specific tenant."""
    if filter is None:
        filter = {}

    query = (
        Visit.objects.filter(case__location__tenant=tenant)
        .filter(**filter)
        .select_related("case__location")
    )

    # Get all locations for the tenant (to include those with 0 visits)
    all_locations = list(tenant.locations.values("id", "name"))

    return _build_cohort_data(
        query=query,
        group_by_fields=["case__location__id", "case__location__name"],
        status_choices=VisitStatus.choices,
        all_groups=all_locations,
    )
