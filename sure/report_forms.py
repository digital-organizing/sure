"""Prefill clinical report forms with the data of a visit.

A report form (e.g. the BAG report of an HIV infection) is a fillable PDF per
language. It is offered for a visit when the latest result of one of the
visit's tests is linked to the form. Which PDF field gets which value is
configured per language version in the admin, see ``ReportField``: each field
has a source (an answer, the result date, ...) and checkboxes are ticked when
the source has the field's value.
"""

import datetime as dt
import itertools
import re
from dataclasses import dataclass, field

import pymupdf
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from labor.models import LocationToLab
from sure.cases import get_test_results
from sure.models import (
    BaseAnswer,
    ReportField,
    ReportFieldKind,
    ReportForm,
    ReportFormFile,
    ReportSource,
    TestResult,
    Visit,
)

GENDER_QUESTION = "SEDFACT-GENDER"
SEX_QUESTION = "SEDFACT-SEX"

# Option codes of GENDER_QUESTION and SEX_QUESTION
MAN, WOMAN, NON_BINARY = "1", "2", "3"
MALE, FEMALE = "1", "2"

# Texts stored for options without a text input
EMPTY_ANSWER_TEXTS = {"", "-"}

DEFAULT_DATE_FORMAT = "%d.%m.%Y"
_ACROBAT_DATE_FORMAT = re.compile(r'AFDate_FormatEx\("([^"]+)"\)')
_ACROBAT_DATE_TOKENS = re.compile(r"yyyy|yy|dd|mm")
_STRFTIME_TOKENS = {"yyyy": "%Y", "yy": "%y", "dd": "%d", "mm": "%m"}

MAPPED_COLOR = (0.0, 0.55, 0.2)
UNMAPPED_COLOR = (0.9, 0.35, 0.0)
PREVIEW_ZOOM = 1.6

MAX_FONT_SIZE = 10.0
MIN_FONT_SIZE = 5.0
LINE_HEIGHT = 1.25  # relative to the font size
# Joining lines tries 2 ** (lines - 1) layouts, longer texts are left as they are.
MAX_JOINED_LINES = 8


def bag_gender(gender: str | None, sex: str | None) -> str | None:
    """Map gender identity and sex assigned at birth to the gender boxes of the
    BAG forms: w, m, mtf or ftm (the forms' VGE is not asked in SURE).

    Following the forms' footnote, MtF/FtM is the sex assigned at birth
    combined with a different or a non-binary gender identity."""
    if gender == WOMAN:
        return "mtf" if sex == MALE else "w"
    if gender == MAN:
        return "ftm" if sex == FEMALE else "m"
    if gender == NON_BINARY:
        return {MALE: "mtf", FEMALE: "ftm"}.get(sex or "")
    return None


def format_date(date: dt.date, date_format: str) -> str:
    """Format a date with an Acrobat date format like dd/mm/yyyy."""
    if not date_format:
        return date.strftime(DEFAULT_DATE_FORMAT)
    return date.strftime(
        _ACROBAT_DATE_TOKENS.sub(lambda m: _STRFTIME_TOKENS[m.group()], date_format)
    )


@dataclass(frozen=True)
class ReportValue:
    """The value of a source: codes to tick checkboxes by and a text to fill in."""

    codes: frozenset[str] = frozenset()
    text: str = ""


@dataclass
class ReportContext:
    """What a report is filled with."""

    visit: Visit
    #: Latest results linked to the form, newest first
    results: list[TestResult]
    user: User | None
    today: dt.date
    _answers: dict[tuple[str, str], BaseAnswer | None] = field(default_factory=dict)

    def answer(self, source: str, code: str) -> BaseAnswer | None:
        if (source, code) not in self._answers:
            answers = (
                self.visit.client_answers
                if source == ReportSource.CLIENT_ANSWER
                else self.visit.consultant_answers
            )
            self._answers[source, code] = (
                answers.filter(question__code=code).order_by("-created_at").first()
            )
        return self._answers[source, code]

    def answer_code(self, code: str) -> str | None:
        answer = self.answer(ReportSource.CLIENT_ANSWER, code)
        if answer is None or not answer.choices:
            return None
        return str(answer.choices[0])


def _answer_value(answer: BaseAnswer | None) -> ReportValue:
    if answer is None:
        return ReportValue()
    texts = [text.strip() for text in answer.texts]
    return ReportValue(
        codes=frozenset(str(choice) for choice in answer.choices),
        text=", ".join(text for text in texts if text not in EMPTY_ANSWER_TEXTS),
    )


def _doctor_lines(context: ReportContext) -> list[str]:
    location = context.visit.case.location
    user_name = context.user.get_full_name() if context.user else ""
    lines = [location.name, location.address, location.phone_number, user_name]
    return [line.strip() for line in lines if line and line.strip()]


def resolve(context: ReportContext, report_field: ReportField) -> ReportValue:
    """The value of a report field's source for the context."""
    match report_field.source:
        case ReportSource.GENDER:
            gender = bag_gender(
                context.answer_code(GENDER_QUESTION), context.answer_code(SEX_QUESTION)
            )
            return ReportValue(frozenset({gender}), gender) if gender else ReportValue()
        case ReportSource.CLIENT_ANSWER | ReportSource.CONSULTANT_ANSWER:
            return _answer_value(
                context.answer(report_field.source, report_field.question_code)
            )
        case ReportSource.RESULT_DATE:
            if not context.results:
                return ReportValue()
            date = timezone.localtime(context.results[0].created_at).date()
            return ReportValue(text=format_date(date, report_field.date_format))
        case ReportSource.RESULT_OPTION:
            return ReportValue(
                codes=frozenset(str(r.result_option_id) for r in context.results),
                text=", ".join(r.result_option.label for r in context.results),
            )
        case ReportSource.LABORATORY:
            link = (
                LocationToLab.objects.filter(location=context.visit.case.location)
                .select_related("labor")
                .first()
            )
            return ReportValue(text=link.labor.name) if link else ReportValue()
        case ReportSource.DOCTOR:
            return ReportValue(text="\n".join(_doctor_lines(context)))
        case ReportSource.TODAY:
            return ReportValue(
                text=format_date(context.today, report_field.date_format)
            )
        case ReportSource.FIXED:
            return ReportValue(text=report_field.value)
    return ReportValue()


def is_ticked(report_field: ReportField, value: ReportValue) -> bool:
    if report_field.source == ReportSource.FIXED:
        return True
    if report_field.value:
        wanted = {code.strip() for code in report_field.value.split(",")}
        return bool(wanted & value.codes)
    return bool(value.codes or value.text)


def report_results(form: ReportForm, visit: Visit) -> list[TestResult]:
    """Latest results of the visit's tests that are linked to the form, newest first."""
    return list(
        get_test_results(visit)
        .filter(result_option__report_forms=form)
        .select_related("result_option")
        .order_by("-created_at")
    )


def available_report_forms(visit: Visit) -> QuerySet[ReportForm]:
    """Forms with a PDF that are linked to one of the visit's latest results."""
    latest_results = get_test_results(visit).values("id")
    return (
        ReportForm.objects.filter(
            result_options__test_results__in=latest_results, files__isnull=False
        )
        .distinct()
        .prefetch_related("files")
    )


def _font_size(lines: list[str], rect: pymupdf.Rect) -> float:
    """The largest font size up to MAX_FONT_SIZE at which the lines fit into rect."""
    widest = max(
        pymupdf.get_text_length(line, fontname="helv", fontsize=1) for line in lines
    )
    by_height = (rect.height - 2) / (len(lines) * LINE_HEIGHT)
    by_width = (rect.width - 4) / widest if widest else MAX_FONT_SIZE
    return min(MAX_FONT_SIZE, by_height, by_width)


def fit_text(text: str, rect: pymupdf.Rect) -> tuple[str, float]:
    """Lay out the lines of text to fit into rect at the largest font size.

    PyMuPDF's automatic size (0) does not shrink multiline text, the lines that
    do not fit would be cut off. When joining consecutive lines with commas
    allows a larger font, e.g. an address in a low box, they are joined."""
    lines = text.splitlines() or [""]
    best_lines, best_size = lines, _font_size(lines, rect)
    if len(lines) <= MAX_JOINED_LINES:
        for count in range(1, len(lines)):
            for splits in itertools.combinations(range(1, len(lines)), count - 1):
                bounds = (0, *splits, len(lines))
                joined = [", ".join(lines[a:b]) for a, b in itertools.pairwise(bounds)]
                size = _font_size(joined, rect)
                if size > best_size:
                    best_lines, best_size = joined, size
    return "\n".join(best_lines), max(MIN_FONT_SIZE, best_size)


def _open_pdf(file: ReportFormFile) -> pymupdf.Document:
    with file.pdf.open("rb") as pdf:
        return pymupdf.open(stream=pdf.read(), filetype="pdf")


def _field_kind(widget: pymupdf.Widget) -> str:
    # pymupdf copies its constants from the mupdf bindings at runtime, ty can't see them.
    if widget.field_type == pymupdf.PDF_WIDGET_TYPE_CHECKBOX:  # ty: ignore[unresolved-attribute]
        return ReportFieldKind.CHECKBOX
    if widget.field_type in (
        pymupdf.PDF_WIDGET_TYPE_TEXT,  # ty: ignore[unresolved-attribute]
        pymupdf.PDF_WIDGET_TYPE_COMBOBOX,  # ty: ignore[unresolved-attribute]
    ):
        return ReportFieldKind.TEXT
    return ReportFieldKind.UNSUPPORTED


def _date_format(widget: pymupdf.Widget) -> str:
    match = _ACROBAT_DATE_FORMAT.search(widget.script_format or "")
    return match.group(1) if match else ""


def sync_fields(file: ReportFormFile) -> None:
    """Read the fields of the file's PDF into its ReportField rows.

    Fields are numbered in reading order: by page, top to bottom, left to right.
    Fields that keep their name keep their mapping, fields that are gone are
    deleted."""
    found: dict[str, tuple[tuple[int, int, float], str, str]] = {}
    with _open_pdf(file) as document:
        page_count = document.page_count
        for page in document:
            for widget in page.widgets():
                if widget.field_name in found:
                    continue
                position = (page.number, int(widget.rect.y0 // 10), widget.rect.x0)
                found[widget.field_name] = (
                    position,
                    _field_kind(widget),
                    _date_format(widget),
                )

    ordered = sorted(found.items(), key=lambda item: item[1][0])
    with transaction.atomic():
        file.report_fields.exclude(name__in=found).delete()
        existing = {f.name: f for f in file.report_fields.all()}
        for number, (name, (_position, kind, date_format)) in enumerate(ordered, 1):
            report_field = existing.get(name) or ReportField(file=file, name=name)
            report_field.number = number
            report_field.kind = kind
            report_field.date_format = date_format
            report_field.save()
        file.page_count = page_count
        file.save(update_fields=["page_count"])


def render_preview(file: ReportFormFile, page_number: int) -> bytes:
    """A PNG of a page with every field boxed and numbered, mapped fields green."""
    report_fields = {f.name: f for f in file.report_fields.all()}
    with _open_pdf(file) as document:
        page = document[page_number]
        for widget in list(page.widgets()):
            report_field = report_fields.get(widget.field_name)
            if report_field is None:
                continue
            color = MAPPED_COLOR if report_field.source else UNMAPPED_COLOR
            page.draw_rect(widget.rect, color=color, width=0.8)
            page.insert_text(
                (widget.rect.x0, widget.rect.y0 - 1),
                str(report_field.number),
                fontsize=6.5,
                color=color,
            )
        return page.get_pixmap(
            matrix=pymupdf.Matrix(PREVIEW_ZOOM, PREVIEW_ZOOM)
        ).tobytes("png")


def fill_report(
    file: ReportFormFile,
    visit: Visit,
    user: User | None,
    results: list[TestResult] | None = None,
) -> bytes:
    """The file's PDF filled with the data of the visit."""
    context = ReportContext(
        visit=visit,
        results=report_results(file.form, visit) if results is None else results,
        user=user,
        today=timezone.localdate(),
    )
    mapped = {f.name: f for f in file.report_fields.exclude(source="")}

    with _open_pdf(file) as document:
        for page in document:
            for widget in list(page.widgets()):
                report_field = mapped.get(widget.field_name)
                if report_field is None:
                    continue
                value = resolve(context, report_field)
                if report_field.kind == ReportFieldKind.CHECKBOX:
                    if not is_ticked(report_field, value):
                        continue
                    widget.field_value = widget.on_state()
                elif report_field.kind == ReportFieldKind.TEXT and value.text:
                    if widget.field_flags & pymupdf.PDF_TX_FIELD_IS_MULTILINE:  # ty: ignore[unresolved-attribute]
                        text, widget.text_fontsize = fit_text(value.text, widget.rect)
                        widget.field_value = text
                    else:
                        widget.field_value = value.text.replace("\n", ", ")
                else:
                    continue
                widget.update()
        return document.tobytes(garbage=3, deflate=True)


def copy_mapping(source: ReportFormFile, target: ReportFormFile) -> int:
    """Copy the mapping of fields with the same name, returns how many were copied."""
    mappings = {f.name: f for f in source.report_fields.all()}
    copied = []
    for report_field in target.report_fields.all():
        origin = mappings.get(report_field.name)
        if origin is None:
            continue
        report_field.source = origin.source
        report_field.question_code = origin.question_code
        report_field.value = origin.value
        copied.append(report_field)
    ReportField.objects.bulk_update(copied, ["source", "question_code", "value"])
    return len(copied)
