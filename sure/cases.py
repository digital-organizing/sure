from django.db.models import F, OuterRef, Prefetch, QuerySet, Subquery
from django.db.models.functions import Greatest
from django.utils.timezone import make_naive

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
from tenants.models import Tenant


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


def prefetch_questionnaire(internal=False, excluded_question_ids=None):
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


def case_cohort_by_tenants():
    return {
        "headers": [{"title": status[1]} for status in VisitStatus.choices],
        "rows": [
            {
                "header": {"title": tenant.name},
                "cols": [
                    {
                        "value": Visit.objects.filter(
                            case__location__tenant=tenant, status=status[0]
                        ).count()
                    }
                    for status in VisitStatus.choices
                ],
            }
            for tenant in Tenant.objects.all()
        ],
    }


def case_cohort_by_location(tenant: Tenant):
    return {
        "headers": [{"title": status[1]} for status in VisitStatus.choices],
        "rows": [
            {
                "header": {"title": location.name},
                "cols": [
                    {
                        "value": Visit.objects.filter(
                            case__location=location, status=status[0]
                        ).count()
                    }
                    for status in VisitStatus.choices
                ],
            }
            for location in tenant.locations.all()
        ],
    }
