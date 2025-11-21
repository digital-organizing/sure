import pandas as pd
from django.db import transaction

from .models import TestBundle, TestCategory, TestKind, TestResultOption

INTERPRETATION_NEEDED = "Interpretation needed (YES = open text field)"
OPTIONS_RAPID = "Result options (Rapid)"
OPTIONS_LAB = "Result options by lab"


def create_options(row, test: TestKind, options_str: str):
    if options_str.startswith("XXX"):
        options = ["reactive", "negative", "unclear"]
    else:
        options = [opt.strip() for opt in options_str.split("/") if opt.strip()]

    for option in options:
        label = option
        color = "#aaaaaa"  # Default gray color
        text_sms = row.get(f"Information Text ({option})", "").strip()

        TestResultOption.objects.update_or_create(
            test_kind=test,
            label=label,
            defaults={
                "color": color,
                "information_text": text_sms,
                "information_by_sms": text_sms != "",
            },
        )


@transaction.atomic
def import_from_excel(path: str):
    df = pd.read_excel(path, sheet_name="TESTS", skiprows=1)

    columns = list(df.columns)

    bundles_start = 0
    bundles_end = columns.index("Number")

    df_tests = df

    df_tests_only = df_tests.query("`Number` > 10").fillna("")
    df_bundles = df_tests_only.iloc[:, bundles_start : bundles_end + 1]
    crate_categories(df_tests)
    create_tests(df_tests_only)
    create_bundles(df_bundles, df_tests_only)


def crate_categories(df_tests):
    df_categories = df_tests.query("`Number` < 10")

    for _, row in df_categories.iterrows():
        # Create category in database here
        TestCategory.objects.update_or_create(
            number=row["Number"], defaults={"name": row["Test"]}
        )


def create_tests(df_tests_only):
    for _, row in df_tests_only.iterrows():
        # Create test in database here
        category_number = int(str(row["Number"])[0])
        category = TestCategory.objects.get(number=category_number)
        if row[OPTIONS_RAPID]:
            options_str = row[OPTIONS_RAPID]
            rapid = True
        else:
            options_str = row[OPTIONS_LAB]
            rapid = False

        if options_str.startswith("XXX"):
            note = options_str[3:].strip()
        else:
            note = ""

        test, _ = TestKind.objects.update_or_create(
            number=row["Number"],
            defaults={
                "name": row["Test"],
                "category": category,
                "interpretation_needed": row[INTERPRETATION_NEEDED].lower() == "yes",
                "rapid": rapid,
                "note": note,
            },
        )
        create_options(row, test, options_str)


def create_bundles(df_bundles, df_tests_only):
    bundle_names = df_bundles.columns[:-1].tolist()

    for bundle_name in bundle_names:
        bundle = TestBundle.objects.get_or_create(name=bundle_name)[0]
        tests = df_tests_only[df_bundles[bundle_name] == "X"]

        for _, row in tests.iterrows():
            test = TestKind.objects.get(number=row["Number"])
            if test not in bundle.test_kinds.all():
                bundle.test_kinds.add(test)
