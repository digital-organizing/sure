from django.db.models import F, OuterRef, QuerySet, Subquery
from django.db.models.functions import Greatest

from sure.models import ClientAnswer, ConsultantAnswer, Test, TestResult, Visit


def annotate_last_modified(queryset: QuerySet[Visit]) -> QuerySet[Visit]:
    """
    Annotates each Visit with its last_modified timestamp, which is the
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
