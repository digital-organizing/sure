"""Models for the sure app

This includes clients, cases, and connections, as well as the questionnaires and the answers."""

import secrets
import uuid

import phonenumbers
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _

BASE_58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

CONTACT_ID_LENGTH = 6
CASE_ID_LENGTH = 6


def generate_contact_id():
    """Generate a base 58 client ID of length CLIENT_ID_LENGTH (6)."""
    return "".join(secrets.choice(BASE_58) for _ in range(CONTACT_ID_LENGTH))


def generate_case_id():
    """Generate a base 58 case ID of length CASE_ID_LENGTH (6)."""
    return "".join(secrets.choice(BASE_58) for _ in range(CASE_ID_LENGTH))


class Case(models.Model):
    """A case is one instance of a clients visit and the questions they answer."""

    id = models.CharField(
        max_length=6,
        primary_key=True,
        default=generate_case_id,
        verbose_name=_("Case ID"),
    )
    location = models.ForeignKey(
        "tenants.Location",
        on_delete=models.CASCADE,
        related_name="cases",
        verbose_name=_("Location"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    @property
    def human_id(self):
        """SUF: Sure 'Fall' or Form/Formulaire"""
        return f"SUF-{self.id}"

    class Meta:
        verbose_name = _("Case")
        verbose_name_plural = _("Cases")


class ConsentChoice(models.TextChoices):
    """Choices for consent to store data."""

    ALLOWED = "allowed", _("Allowed")
    DENIED = "denied", _("Denied")


def generate_token():
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


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

    def generate_token(self) -> str:
        """Generate a new token for this contact."""
        token = Token.objects.create(contact=self)
        return token.token


class Client(models.Model):
    """A client (person seeking help)"""

    id = models.CharField(
        max_length=6,
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
        help_text=_("Whether this question is optional for centers"),
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
    texts = ArrayField(models.TextField(), blank=True, default=list)
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


class ConsultantAnswer(BaseAnswer):
    """An answer to a consultant question."""

    question = models.ForeignKey(
        ConsultantQuestion, on_delete=models.CASCADE, related_name="answers"
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
        blank=True,
        verbose_name=_("Note"),
        help_text=_("Additional notes about the test"),
    )

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
        blank=True,
        verbose_name=_("Information Text"),
        help_text=_("Information text to be sent to the client"),
    )

    def __str__(self):
        return f"{self.test_kind.name} - {self.label}"


class TestBundle(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    test_kinds = models.ManyToManyField(TestKind, related_name="test_bundles")

    def __str__(self):
        return f"{self.name}"


class Visit(models.Model):
    """A visit links a case to a questionnaire."""

    case = models.OneToOneField(Case, on_delete=models.CASCADE, related_name="visit")
    questionnaire = models.ForeignKey(
        Questionnaire, on_delete=models.CASCADE, related_name="visits"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    consultant = models.ForeignKey(
        "tenants.Consultant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visits",
    )


class Test(models.Model):
    visit = models.ForeignKey(
        Visit, on_delete=models.CASCADE, related_name="test_results"
    )
    test_kind = models.ForeignKey(
        TestKind, on_delete=models.CASCADE, related_name="test_results"
    )
    note = models.TextField(
        blank=True,
        verbose_name=_("Note"),
        help_text=_("Additional notes about the test result"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))


class TestResult(models.Model):
    result_option = models.ForeignKey(
        TestResultOption, on_delete=models.CASCADE, related_name="test_results"
    )
    note = models.TextField(
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
