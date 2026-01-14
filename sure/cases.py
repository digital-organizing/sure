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
        TestResult.objects.filter(test__visit=OuterRef("pk"))
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


def get_export_dict(visit: Visit):
    record = {
        "id": visit.pk,
        "created_at": make_naive(visit.created_at),
        "status": visit.status,
        "tags": ", ".join(visit.tags),
        "location": visit.case.location.name,
        "tenant": visit.case.location.tenant.name,
        "questionnaire": visit.questionnaire.name,
    }

    if hasattr(visit.case, "connection"):
        record["client_id"] = visit.case.connection.client_id

    record.update(get_client_answers_export(visit))
    record.update(get_consultant_answers_export(visit))
    record.update(get_test_results_export(visit))

    return record


def show_question(question, answers):
    if not question.show_for_options.exists():
        return True

    for option in question.show_for_options.all():
        option: ClientOption = option
        answer = answers.get(option.question.code, None)
        if not answer:
            continue
        if option.code in answer["codes"]:
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


def get_client_answers_export(visit: Visit):
    answers = {}
    for section in visit.questionnaire.sections.all():
        for question in section.client_questions.all():
            question: ClientQuestion = question

            if not show_question(question, answers):
                continue

            answer_qs = ClientAnswer.objects.filter(
                visit=visit, question=question
            ).order_by("-created_at")
            if not answer_qs.exists():
                answer_record = {
                    "codes": [99],
                    "texts": ["missing"],
                }
            else:
                answer = answer_qs[0]
                answer_record = {
                    "codes": answer.choices,
                    "texts": answer.texts,
                }
            answers[question.code] = answer_record

    output = {}
    for question_code, answer in answers.items():
        output[f"{question_code}_codes"] = get_answer_codes(answer["codes"])
        output[f"{question_code}_texts"] = ";".join(answer["texts"])
    return output


def get_consultant_answers_export(visit: Visit):
    output = {}
    for question in visit.questionnaire.consultant_questions.all():
        question: ConsultantQuestion = question

        answer_qs = ConsultantAnswer.objects.filter(
            visit=visit, question=question
        ).order_by("-created_at")
        if not answer_qs.exists():
            answer_record = {
                "codes": [99],
                "texts": ["missing"],
            }
        else:
            answer = answer_qs[0]
            answer_record = {
                "codes": answer.choices,
                "texts": answer.texts,
            }
        output[f"{question.code}_codes"] = get_answer_codes(answer_record["codes"])
        output[f"{question.code}_texts"] = get_answer_texts(answer_record["texts"])
    return output


def get_test_results_export(visit: Visit):
    output = {}

    for test_kind in TestKind.objects.all():
        test_kind: TestKind = test_kind

        output[f"{test_kind.name}"] = None
        if test_kind.interpretation_needed:
            output[f"{test_kind.name} [{test_kind.note}]"] = None

        test = visit.tests.filter(test_kind=test_kind).first()

        if not test:
            continue

        result = test.results.order_by("-created_at").first()
        if not result:
            output[f"{test_kind.name}"] = "no_result"
            continue
        output[f"{test_kind.name}"] = result.result_option.label
        if test_kind.interpretation_needed:
            output[f"{test_kind.name} [{test_kind.note}]"] = result.note

    return output


def _color_for_status(status):
    match status:
        case VisitStatus.CREATED:
            return "bg-green-100"
        case VisitStatus.CLIENT_SUBMITTED:
            return "bg-yellow-100"
        case VisitStatus.CONSULTANT_SUBMITTED:
            return "bg-blue-600"
        case VisitStatus.TESTS_RECORDED:
            return "bg-blue-100"
        case VisitStatus.RESULTS_RECORDED:
            return "bg-primary-500"
        case VisitStatus.CLOSED:
            return "bg-gray-50"
        case _:
            return "bg-gray-500"


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

        group_data[group_id]["counts"][status] = count
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
                    _get_col(data["counts"].get(status[0], 0), total)
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
