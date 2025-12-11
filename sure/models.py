"""Models for the sure app

This includes clients, cases, and connections, as well as the questionnaires and the answers."""

import secrets
import uuid
from datetime import timedelta

import phonenumbers
from colorfield.fields import ColorField
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import (
    get_password_validators,
    validate_password,
)
from django.contrib.postgres.fields import ArrayField
from django.core.validators import FileExtensionValidator

from html_sanitizer import Sanitizer
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords
from django.utils.safestring import mark_safe

from markdown import markdown

BASE_34 = "1234567890abcdefghijkmnopqrstuvwxyz"
DIGITS = "0123456789"

CONTACT_ID_LENGTH = 7
CASE_ID_LENGTH = 7


def generate_contact_id():
    """Generate a base 58 client ID of length CLIENT_ID_LENGTH (7)."""
    return "".join(secrets.choice(BASE_34) for _ in range(CONTACT_ID_LENGTH))


def generate_case_id():
    """Generate a base 58 case ID of length CASE_ID_LENGTH (7)."""
    return "".join(secrets.choice(BASE_34) for _ in range(CASE_ID_LENGTH))


class Case(models.Model):
    """A case is one instance of a clients visit and the questions they answer."""

    id = models.CharField(
        max_length=8,
        primary_key=True,
        default=generate_case_id,
        verbose_name=_("Case ID"),
    )
    external_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("External ID"),
        help_text=_("An optional external ID for the case"),
    )
    location = models.ForeignKey(
        "tenants.Location",
        on_delete=models.CASCADE,
        related_name="cases",
        verbose_name=_("Location"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    key = models.TextField(
        blank=True,
        verbose_name=_("Access Key"),
        help_text=_("An optional access key for the case data"),
    )

    history = HistoricalRecords()

    def set_key(self, key: str):
        """Set the access key for the case."""
        validate_password(
            key, password_validators=get_password_validators(settings.KEY_VALIDATORS)
        )
        if len(key) > settings.MAX_KEY_LENGTH:
            raise ValueError(
                f"Key is too long (maximum is {settings.MAX_KEY_LENGTH} characters)"
            )

        key = make_password(key)

        with transaction.atomic():
            if self.key != "":
                raise ValueError("Key is already set and cannot be changed")
            self.key = key
            self.save(update_fields=["key"])

    def check_key(self, key: str) -> bool:
        return check_password(key, self.key) and self.key != ""

    def has_key(self) -> bool:
        """Check if the case has an access key set."""
        return self.key != ""

    @property
    def human_id(self):
        """SUF: Sure 'Fall' or Form/Formulaire"""
        return f"SUF-{self.id}"

    @property
    def show_external_id(self):
        return "EXT-" + self.external_id if self.external_id else ""

    class Meta:
        verbose_name = _("Case")
        verbose_name_plural = _("Cases")


class ConsentChoice(models.TextChoices):
    """Choices for consent to store data."""

    ALLOWED = "allowed", _("Allowed")
    DENIED = "denied", _("Denied")


def generate_token():
    """Generate a secure random token."""
    return "".join(secrets.choice(DIGITS) for _ in range(6))


class Contact(models.Model):
    """Contact model to store contact information for clients, if they choose to provide it."""

    id = models.UUIDField(
        primary_key=True, editable=False, unique=True, default=uuid.uuid4
    )
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=30, unique=True)

    tokens: models.QuerySet["Token"]

    def save(self, *args, **kwargs):
        if not phonenumbers.is_valid_number(
            phonenumbers.parse(self.phone_number, settings.DEFAULT_REGION)
        ):
            raise ValueError("Invalid phone number")
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Contact")
        verbose_name_plural = _("Contacts")

    def has_recent_token(self) -> bool:
        """Check if a recent token has been generated for this contact."""
        recent_token = self.tokens.filter(
            created_at__gte=timezone.now()
            - timedelta(minutes=settings.TOKEN_RESEND_INTERVAL_MINUTES),
            used_at__isnull=True,
            disabled=False,
        ).first()

        return recent_token is not None

    @transaction.atomic
    def generate_token(self, case: Case) -> str:
        """Generate a new token for this contact."""
        # Check if recent token exists
        if self.has_recent_token():
            raise ValueError(
                "A recent token has already been generated, "
                "please wait before requesting a new one."
            )

        self.tokens.filter(used_at__isnull=True).update(disabled=True)

        token = self.tokens.create(case=case)
        return token.token

    @transaction.atomic
    def verify_token(self, token: str, case: Case) -> "Token | None":
        """Verify if the given token is valid for this contact."""
        valid_token = self.tokens.filter(
            token=token,
            used_at__isnull=True,
            disabled=False,
            case=case,
        ).first()

        if valid_token is None:
            return None

        valid_token.used_at = timezone.now()
        valid_token.save(update_fields=["used_at"])
        return valid_token


class Client(models.Model):
    """A client (person seeking help)"""

    id = models.CharField(
        max_length=8,
        primary_key=True,
        default=generate_contact_id,
        verbose_name=_("Client ID"),
    )
    contact = models.OneToOneField(
        Contact, on_delete=models.CASCADE, related_name="client"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    @property
    def human_id(self):
        """SUC: Sure 'Client' or 'Klient'"""
        return f"SUC-{self.id}"


class Connection(models.Model):
    case = models.OneToOneField(
        Case, on_delete=models.CASCADE, related_name="connection"
    )
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="connections"
    )

    consent = models.CharField(
        max_length=10,
        choices=ConsentChoice.choices,
        default=ConsentChoice.DENIED,
        verbose_name=_("Consent"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))


class Token(models.Model):
    """A token to verify the ownership of a contact method (email or phone number).

    A token is generated and sent to the client, to ensure that they own the contact method
    """

    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, related_name="tokens"
    )
    token = models.CharField(
        max_length=64, verbose_name=_("Token"), default=generate_token, unique=True
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    used_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Used At"))

    disabled = models.BooleanField(
        default=False,
        verbose_name=_("Disabled"),
        help_text=_("Whether this token is disabled and cannot be used"),
    )

    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="tokens")


class Questionnaire(models.Model):
    """A questionnaire is a set of questions to be answered by the client and consultant."""

    name = models.CharField(
        max_length=255, verbose_name=_("Name"), help_text=_("Name of the questionnaire")
    )

    sections: models.QuerySet["Section"]
    consultant_questions: models.QuerySet["ConsultantQuestion"]

    class Meta:
        verbose_name = _("Questionnaire")
        verbose_name_plural = _("Questionnaires")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"


class Section(models.Model):
    """A section is a group of questions in a questionnaire for the client."""

    questionnaire = models.ForeignKey(
        Questionnaire, on_delete=models.CASCADE, related_name="sections"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
        help_text=_("Order of the section in the questionnaire"),
    )
    title = models.CharField(
        max_length=255, verbose_name=_("Title"), help_text=_("Title of the section")
    )
    label = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Label"),
        help_text=_("Short label for the section"),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Description of the section"),
    )

    client_questions: models.QuerySet["ClientQuestion"]

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.questionnaire.name} - {self.title}"


class QuestionFormats(models.TextChoices):
    """Formats for questions."""

    SINGLE_CHOICE = "single choice", _("Single Choice")
    MULTIPLE_CHOICE = "multiple choice", _("Multiple Choice")
    MULTIPLE_CHOICE_WITH_TEXT = (
        "multiple choice + open text field",
        _("Multiple Choice with Open Text Field"),
    )
    OPEN_TEXT = "open text field", _("Open Text")
    LONG_TEXT = "long text field", _("Long Text Field")
    MULTI_CHOICE_MULTI_TEXT = (
        "multiple choice + multiple open text field",
        _("Multi Choice Multi Text"),
    )
    SINGLE_CHOICE_WITH_TEXT = (
        "single choice + open text field",
        _("Single Choice with Text"),
    )


class BaseQuestion(models.Model):
    """Base question model to be inherited by ClientQuestion and ConsultantQuestion."""

    question_text = models.TextField(verbose_name=_("Question Text"))
    code = models.CharField(
        max_length=100,
        verbose_name=_("Code"),
        help_text=_("Unique code for the question"),
    )
    format = models.CharField(
        max_length=80,
        choices=QuestionFormats.choices,
        default=QuestionFormats.SINGLE_CHOICE,
        verbose_name=_("Format"),
    )

    label = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Label"),
        help_text=_("Short label for the question"),
    )
    copy_paste = models.BooleanField(
        default=False,
        verbose_name=_("Copy Paste"),
        help_text=_("Allow copy paste for this question"),
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
        help_text=_("Order of the question in the questionnaire"),
    )

    validation = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Validation"),
        help_text=_("Regex validation for open text questions"),
    )

    class Meta:
        abstract = True
        ordering = ["order"]

    def __str__(self):
        return f"{self.question_text[:50]}..."


class BaseOption(models.Model):
    """Base option model to be inherited by ClientOption and ConsultantOption.

    Combine a code and a label, and additional fields for ordering and allowing text input."""

    text = models.CharField(max_length=255, verbose_name=_("Option Text"), blank=True)
    code = models.CharField(
        max_length=100,
        verbose_name=_("Code"),
        help_text=_("Unique code for the option"),
    )
    allow_text = models.BooleanField(
        default=False,
        verbose_name=_("Allow Text"),
        help_text=_("Allow text input for this option"),
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Order"),
        help_text=_("Order of the option in the question"),
    )

    choices = ArrayField(models.CharField(max_length=255), blank=True, default=list)

    class Meta:
        abstract = True
        ordering = ["order"]

    def __str__(self):
        return f"{self.code} ({self.text})"


class ClientQuestion(BaseQuestion):
    """A question to be answered by the client."""

    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name="client_questions"
    )

    do_not_show_directly = models.BooleanField(
        default=False,
        verbose_name=_("Do Not Show Directly"),
        help_text=_("Do not show this question directly to the client"),
    )

    optional_for_centers = models.BooleanField(
        default=False,
        verbose_name=_("Optional for Centers"),
        help_text=_(
            "Whether this question is optional for centers, centers can opt-out of asking it."
        ),
    )

    extra_for_centers = models.BooleanField(
        default=False,
        verbose_name=_("Extra for Centers"),
        help_text=_(
            "Whether this question is extra for centers, centers can opt-in to asking it."
        ),
    )

    show_for_options = models.ManyToManyField(
        "ClientOption",
        blank=True,
        related_name="conditional_questions",
        verbose_name=_("Show For Options"),
        help_text=_("Show this question only if one of these options is selected"),
    )

    options: models.QuerySet["ClientOption"]


class ClientOption(BaseOption):
    """An option for a client question."""

    question = models.ForeignKey(
        ClientQuestion, on_delete=models.CASCADE, related_name="options"
    )

    text_for_consultant = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Text for Consultant"),
        help_text=_("Text to be shown to the consultant when this option is selected"),
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["question", "code"],
                name="client_unique_option_code_per_question",
            )
        ]

    def __str__(self):
        return f"{self.question.code}={self.code}"


class ConsultantQuestion(BaseQuestion):
    """A question to be answered by the consultant."""

    questionnaire = models.ForeignKey(
        Questionnaire, on_delete=models.CASCADE, related_name="consultant_questions"
    )

    options: models.QuerySet["ConsultantOption"]


class ConsultantOption(BaseOption):
    """An option for a consultant question."""

    question = models.ForeignKey(
        ConsultantQuestion, on_delete=models.CASCADE, related_name="options"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["question", "code"],
                name="consultant_unique_option_code_per_question",
            )
        ]


class BaseAnswer(models.Model):
    """Base answer model to be inherited by ClientAnswer and ConsultantAnswer.

    Uses arrays to store multiple choices and texts and single choice."""

    choices = ArrayField(models.IntegerField(), blank=True, default=list)
    texts = ArrayField(models.TextField(max_length=2000), blank=True, default=list)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("User"),
        help_text=_("The user who recorded the answer (consultant)"),
    )

    question: models.ForeignKey[BaseQuestion]

    class Meta:
        abstract = True

    def __str__(self):
        return f"Answer to {self.question}"


class ClientAnswer(BaseAnswer):
    """An answer to a client question."""

    question = models.ForeignKey(
        ClientQuestion, on_delete=models.CASCADE, related_name="answers"
    )
    question_id: int
    visit = models.ForeignKey(
        "Visit", on_delete=models.CASCADE, related_name="client_answers"
    )


class ConsultantAnswer(BaseAnswer):
    """An answer to a consultant question."""

    question = models.ForeignKey(
        ConsultantQuestion, on_delete=models.CASCADE, related_name="answers"
    )
    visit = models.ForeignKey(
        "Visit", on_delete=models.CASCADE, related_name="consultant_answers"
    )


class TestCategory(models.Model):
    number = models.PositiveIntegerField(verbose_name=_("Number"), unique=True)
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Description of the test category"),
    )

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"{self.number} - {self.name}"


class TestKind(models.Model):
    category = models.ForeignKey(
        TestCategory, on_delete=models.CASCADE, related_name="test_kinds"
    )
    number = models.PositiveIntegerField(verbose_name=_("Number"), unique=True)
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    interpretation_needed = models.BooleanField(
        default=False,
        verbose_name=_("Interpretation Needed"),
        help_text=_("Does this test kind need interpretation?"),
    )
    rapid = models.BooleanField(
        default=False,
        verbose_name=_("Rapid"),
        help_text=_("Is this a rapid test?"),
    )

    note = models.TextField(
        max_length=2000,
        blank=True,
        verbose_name=_("Note"),
        help_text=_("Additional notes about the test"),
    )

    test_bundles: models.QuerySet["TestBundle"]
    result_options: models.QuerySet["TestResultOption"]

    class Meta:
        ordering = ["number"]

    def __str__(self):
        return f"{self.number} - {self.name}"


class TestResultOption(models.Model):
    test_kind = models.ForeignKey(
        TestKind, on_delete=models.CASCADE, related_name="result_options"
    )
    label = models.CharField(max_length=255, verbose_name=_("Label"))
    information_by_sms = models.BooleanField(
        default=False,
        verbose_name=_("Information by SMS"),
        help_text=_("Can this result option be sent by SMS?"),
    )
    information_text = models.TextField(
        max_length=2000,
        blank=True,
        verbose_name=_("Information Text"),
        help_text=_("Information text to be sent to the client"),
    )

    color = ColorField(
        max_length=7,
        blank=True,
        verbose_name=_("Color"),
        help_text=_("Color associated with this result option (hex code)"),
    )

    def __str__(self):
        return f"{self.test_kind.name} - {self.label}"

    def save(self, *args, **kwargs):
        sanitizer = Sanitizer({"keep_typographic_whitespace": True})
        self.information_text = sanitizer.sanitize(self.information_text)
        super().save(*args, **kwargs)


class ResultInformation(models.Model):
    option = models.ForeignKey(
        TestResultOption,
        on_delete=models.CASCADE,
        related_name="result_informations",
        limit_choices_to={"information_by_sms": True},
        help_text=_(
            "Select the result for which you want to display additional information"
        ),
    )
    information_text = models.TextField(
        max_length=2000,
        blank=True,
        verbose_name=_("Information Text"),
        help_text=_(
            "Detailed information related to this result option, the information about the result is already displayed, you only need to specify additional information (booking link, ...)"
        ),
    )
    locations = models.ManyToManyField(
        "tenants.Location",
        related_name="result_informations",
        verbose_name=_("Locations"),
        help_text=_(
            "Locations where this information is applicable. To show different texts at different locations create another entry for this location."
        ),
    )

    def preview(self) -> str:
        generic = markdown(self.option.information_text)
        special = markdown(self.information_text)
        sanitizer = Sanitizer()
        sanitized = sanitizer.sanitize(generic + "<br/>" + special)
        return mark_safe(sanitized)  # nosec

    def __str__(self):
        return f"Information for {self.option} @ {', '.join([loc.name for loc in self.locations.all()])}"

    def save(self, *args, **kwargs):
        sanitizer = Sanitizer({"keep_typographic_whitespace": True})
        self.information_text = sanitizer.sanitize(self.information_text)
        super().save(*args, **kwargs)


class TestBundle(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    test_kinds = models.ManyToManyField(TestKind, related_name="test_bundles")

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = _("Test Bundle")
        verbose_name_plural = _("Test Bundles")
        ordering = ["name"]


class VisitStatus(models.TextChoices):
    """Status of a visit."""

    CREATED = "created", _("Created")
    CLIENT_SUBMITTED = "client_submitted", _("Client Submitted")
    CONSULTANT_SUBMITTED = "consultant_submitted", _("Consultant Submitted")
    TESTS_RECORDED = "tests_recorded", _("Tests Recorded")

    RESULTS_RECORDED = "results_recorded", _("Results Recorded")
    RESULTS_SENT = "results_sent", _("Results Sent")
    RESULTS_MISSED = "results_missed", _("Client missed results")
    RESULTS_SEEN = "results_seen", _("Client accessed results")
    CLOSED = "closed", _("Closed")

    CANCELED = "canceled", _("Canceled")


class Visit(models.Model):
    """A visit links a case to a questionnaire."""

    case = models.OneToOneField(Case, on_delete=models.CASCADE, related_name="visit")
    questionnaire = models.ForeignKey(
        Questionnaire, on_delete=models.CASCADE, related_name="visits"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    published_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Published At")
    )
    consultant = models.ForeignKey(
        "tenants.Consultant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visits",
    )

    status = models.CharField(
        max_length=20,
        choices=VisitStatus.choices,
        default=VisitStatus.CREATED,
        verbose_name=_("Status"),
    )

    @property
    def results_visible_for_client(self) -> bool:
        return self.status in [VisitStatus.RESULTS_SENT, VisitStatus.RESULTS_SEEN]

    def save(self, *args, **kwargs):
        if self.status == VisitStatus.RESULTS_SENT and self.published_at is None:
            self.published_at = timezone.now()
            if "update_fields" in kwargs:
                kwargs["update_fields"].append("published_at")

        if self.published_at is not None and self.status not in [
            VisitStatus.RESULTS_SENT,
            VisitStatus.CLOSED,
        ]:
            self.published_at = None
            if "update_fields" in kwargs:
                kwargs["update_fields"].append("published_at")

        return super().save(*args, **kwargs)

    tags = ArrayField(models.CharField(max_length=50), blank=True, default=list)

    client_answers: models.QuerySet[ClientAnswer]
    consultant_answers: models.QuerySet[ConsultantAnswer]
    tests: models.QuerySet["Test"]
    documents: models.QuerySet["VisitDocument"]
    notes: models.QuerySet["VisitNote"]
    free_form_tests: models.QuerySet["FreeFormTest"]
    logs: models.QuerySet["VisitLog"]

    history = HistoricalRecords()


class VisitNote(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="notes")
    note = models.TextField(
        max_length=2000,
        verbose_name=_("Note"),
        help_text=_("Note content"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("User"),
        help_text=_("The user who created the note"),
    )
    hidden = models.BooleanField(
        default=False,
        verbose_name=_("Hidden"),
        help_text=_("Whether this note is hidden from clients"),
    )

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        sanitizer = Sanitizer({"keep_typographic_whitespace": True})
        self.note = sanitizer.sanitize(self.note)
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = _("Visit Note")
        verbose_name_plural = _("Visit Notes")
        ordering = ["created_at"]


class VisitLog(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="logs")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("Timestamp"))
    action = models.CharField(
        max_length=255,
        verbose_name=_("Action"),
        help_text=_("Description of the action taken"),
    )
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("User"),
        help_text=_("The user who performed the action"),
    )


class VisitDocument(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="documents")
    name = models.CharField(
        max_length=255,
        verbose_name=_("Document Name"),
        help_text=_("Name of the document"),
    )
    document = models.FileField(
        upload_to="visit_documents/",
        verbose_name=_("Document"),
        help_text=_("Document related to the visit"),
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "doc", "docx", "jpg", "png"]
            )
        ],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Uploaded At"))
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("User"),
        help_text=_("The user who uploaded the document"),
    )

    hidden = models.BooleanField(
        default=False,
        verbose_name=_("Hidden"),
        help_text=_("Whether this document is hidden from clients"),
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = _("Visit Document")
        verbose_name_plural = _("Visit Documents")
        ordering = ["uploaded_at"]


class Test(models.Model):
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="tests")
    test_kind = models.ForeignKey(
        TestKind, on_delete=models.CASCADE, related_name="test_results"
    )
    note = models.TextField(
        max_length=2000,
        blank=True,
        verbose_name=_("Note"),
        help_text=_("Additional notes about the test result"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("User"),
        help_text=_("The user who recorded the test"),
    )

    results: models.QuerySet["TestResult"]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["visit", "test_kind"],
                name="unique_test_per_visit_and_kind",
            )
        ]


class FreeFormTest(models.Model):
    visit = models.ForeignKey(
        Visit, on_delete=models.CASCADE, related_name="free_form_tests"
    )

    name = models.CharField(max_length=255, verbose_name=_("Test Name"))

    result = models.CharField(
        max_length=255,
        verbose_name=_("Test Result"),
        help_text=_("Result of the free form test"),
        blank=True,
    )

    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("User"),
        help_text=_("The user who recorded the free form test"),
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    result_recorded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Result Recorded At"),
        help_text=_("Timestamp when the result was recorded"),
    )

    history = HistoricalRecords()


class TestResult(models.Model):
    result_option = models.ForeignKey(
        TestResultOption, on_delete=models.CASCADE, related_name="test_results"
    )
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="results")
    note = models.TextField(
        max_length=2000,
        blank=True,
        verbose_name=_("Note"),
        help_text=_("Additional notes about the test result"),
    )
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("User"),
        help_text=_("The user who recorded the test result (consultant)"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))


class ExportStatus(models.TextChoices):
    """Status of a visit export."""

    PENDING = "pending", _("Pending")
    IN_PROGRESS = "in_progress", _("In Progress")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")


class VisitExport(models.Model):
    user = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="visit_exports",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    status = models.CharField(
        max_length=20,
        choices=ExportStatus.choices,
        default=ExportStatus.PENDING,
        verbose_name=_("Status"),
    )

    start_date = models.DateField(verbose_name=_("Start Date"))
    end_date = models.DateField(verbose_name=_("End Date"))

    file = models.FileField(
        upload_to="visit_exports/",
        null=True,
        blank=True,
        verbose_name=_("Exported File"),
        help_text=_("The exported file containing visit data"),
    )

    error_message = models.TextField(
        blank=True,
        verbose_name=_("Error Message"),
        help_text=_("Error message if the export failed"),
    )

    total_visits = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Total Visits"),
        help_text=_("Total number of visits included in the export"),
    )

    progress = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Progress"),
        help_text=_("Progress of the export in percentage"),
    )

    def __str__(self):
        return f"Visit Export {self.pk} by {self.user.get_full_name()} ({self.status})"
