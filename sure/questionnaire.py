"""Functions for handling questions: import from excel, get question in different language."""

import logging
import pandas as pd

from sure.models import ClientQuestion, QuestionFormats, Questionnaire, Section


logger = logging.getLogger(__name__)

TEXT_ALLOWED = "__"
YES = "yes"
DO_NOT_SHOW = "// do not show directly //"
FOUR_DIGIT_NUMBER = "four-digit number"


def map_answer_format(answer_format: str) -> tuple[str, str]:
    """Map the answer format from the excel file to the internal representation."""
    answer_format = answer_format.strip().lower()
    if answer_format == FOUR_DIGIT_NUMBER:
        return QuestionFormats.OPEN_TEXT, r"^\d{4}$"

    if answer_format not in QuestionFormats.values:
        raise ValueError(f"Unknown format: {answer_format}")

    return answer_format, ""


def create_section(row, order, questionnaire: Questionnaire) -> Section:
    """Create a section from a row in the excel file."""
    title, _, text = str(row["Question-Text"]).partition("\n")
    section = questionnaire.sections.create(
        title=title.strip(),
        description=text.strip(),
        order=order,
    )
    return section


def create_options(row, question):
    """Create options for a question from a row in the excel file."""
    options = str(row["Answer-Options"]).split("\n")

    for index, option in enumerate(options):
        if option.strip() == "":  # Skip empty options
            continue
        code, _, text = option.partition(": ")
        if not code or not text:
            logger.warning("Invalid option format: %s", option)
            continue
        allow_text = TEXT_ALLOWED in text
        text = text.replace("_", "").strip()
        question.options.update_or_create(
            code=code.strip(),
            defaults={
                "text": text,
                "order": index,
                "allow_text": allow_text,
            },
        )


def create_question(row, order, section) -> ClientQuestion | None:
    """Create a question from a row in the excel file."""
    try:
        answer_format, validation = map_answer_format(str(row["Answer-Format"]))
    except ValueError as e:
        logger.error("Error in question '%s': %s", row["Question-Text"], e)
        return None

    question, _ = section.client_questions.update_or_create(
        section=section,
        code=row["Label"],
        defaults={
            "question_text": row["Question-Text"],
            "format": answer_format,
            "copy_paste": str(row["Export via temporary storage button"]) == YES,
            "validation": validation,
            "order": order,
            "do_not_show_directly": str(row["Shown in Consultant as:"]) == DO_NOT_SHOW,
            "optional_for_centers": str(row["optional for centers"]) == YES,
        },
    )

    create_options(row, question)
    return question


def import_client_questions(df: pd.DataFrame, questionnaire: Questionnaire):
    """Import client questions from a pandas DataFrame."""
    df = df.fillna("")

    columns = list(df.columns)

    question_index = columns.index("Question-Text")
    label_columns = columns[:question_index]

    df["Label"] = df.apply(lambda row: "".join(list(set(row[label_columns]))), axis=1)
    section = None
    section_count = 0
    question_count = 0

    for _, row in df.iterrows():
        if str(row["Label"]) == "":
            # Section
            section = create_section(row, section_count, questionnaire)
            section_count += 1
            question_count = 0
            continue

        if section is None:
            logger.warning(
                "Skipping question outside of section: %s", row["Question-Text"]
            )
            continue
        if str(row["Question-Text"]).strip() == "":
            logger.warning(
                "Skipping question with empty text in section %s", section.title
            )
            continue
        create_question(row, question_count, section)

        question_count += 1


SKIP_QUESTIONS = [
    "TESTS-PERFORMED",
    "TESTS-RESULTS",
    "TAGS",
]


def import_consultant_questions(df: pd.DataFrame, questionnaire: Questionnaire):
    """Import consultant questions from a pandas DataFrame."""
    df = df.fillna("")

    for index, (_, row) in enumerate(df.iterrows()):
        code = str(row["Question-Code"]).strip()
        if code in SKIP_QUESTIONS:
            logger.info("Skipping question %s", code)
            continue
        text = str(row["Question-Text"]).strip()
        answer_format = map_answer_format(str(row["Answer-Format"]).strip())[0]

        question, _ = questionnaire.consultant_questions.update_or_create(
            code=code,
            defaults={
                "question_text": text,
                "format": answer_format,
                "order": index,
            },
        )

        options = str(row["Answer-Options"]).split("\n")
        for opt_index, option in enumerate(options):
            if option.strip() == "":  # Skip empty options
                continue
            option_code, _, text = option.partition(": ")
            if not option_code or not text:
                logger.warning("Invalid option format: %s", option)
                continue
            allow_text = TEXT_ALLOWED in text
            text = text.replace("_", "").strip()
            question.options.update_or_create(
                code=option_code.strip(),
                defaults={
                    "text": text,
                    "order": opt_index,
                    "allow_text": allow_text,
                },
            )
