#!/usr/bin/env python3
"""
Script to generate Markdown questionnaires from JSON data.
Generates two separate markdown files: one for client questions and one for consultant questions.
"""

import io

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.translation import activate, get_language
from markdown_pdf import MarkdownPdf
from markdown_pdf import Section as MDSection

from sure.models import ClientQuestion, ConsultantQuestion, Questionnaire, Section

MD_CSS = """
body {
    font-family: sans-serif;
    }"""


class MarkdownGenerator:
    def __init__(self, title):
        self.title = title
        self.content = []

    def add_title(self):
        """Add main title to the markdown."""
        self.content.append(f"# {self.title} [{get_language()}]\n\n")

    def add_section(self, section: Section):
        """Add a section with its title."""
        if section.title:
            self.content.append(f"## {section.title}\n\n")
        if section.description:
            self.content.append(f"{section.description}\n\n")

    def add_question(self, question: ClientQuestion | ConsultantQuestion):
        """Add a question with its options to the markdown."""
        # Question text
        question_text = question.question_text
        self.content.append(f"### {question_text}\n\n")

        # Question metadata
        format_info = question.format
        if format_info:
            self.content.append(f"*Format: {format_info}*\n\n")

        # Options
        options = question.options

        # Filter out dropdown choices
        valid_options = [opt for opt in options.all() if not opt.choices]

        for option in valid_options:
            option_text = option.text
            allow_text = option.allow_text

            # Skip empty text options that are just for text input
            if not option_text and allow_text:
                # Add free text field
                self.content.append("☐ *Free text response:*\n\n&#xA0;  \n  \n")
                self.content.append(f"{'_' * 80}\n\n")
            elif option_text:
                # Regular option with checkbox
                self.content.append(f"☐ {option_text}\n\n")

                # If this option allows text, add empty line
                if allow_text:
                    self.content.append(f"&#xA0; \n\n{'_' * 80}\n\n")

        self.content.append("\n---\n\n")

    def build_pdf(self) -> io.BytesIO:
        """Build and return the markdown content as a PDF in a BytesIO buffer."""
        pdf = MarkdownPdf(toc_level=1, optimize=True)
        pdf.add_section(MDSection(text="".join(self.content)), user_css=MD_CSS)
        out = io.BytesIO()
        pdf.save_bytes(out)
        out.seek(0)
        return out


def generate_client_markdown(questionnaire: Questionnaire):
    """Generate markdown for client questions."""
    md = MarkdownGenerator(questionnaire.name)
    md.add_title()

    sections = questionnaire.sections
    for section in sections.all():
        client_questions = section.client_questions
        if client_questions:
            md.add_section(section)
            for question in client_questions.all():
                md.add_question(question)

    return md.build_pdf()


def generate_consultant_markdown(questionnaire: Questionnaire):
    """Generate markdown for consultant questions."""
    md = MarkdownGenerator(questionnaire.name)
    md.add_title()

    consultant_questions = questionnaire.consultant_questions
    if consultant_questions:
        for question in consultant_questions.all():
            md.add_question(question)

    return md.build_pdf()


def generate_pdfs(questionnaire: Questionnaire):
    for language in settings.LANGUAGES:
        activate(language[0])
        questionnaire = Questionnaire.objects.get(
            pk=questionnaire.pk
        )  # Reload to get translated fields
        client_pdf = generate_client_markdown(questionnaire)
        consultant_pdf = generate_consultant_markdown(questionnaire)

        client_field = getattr(questionnaire, f"client_pdf_{language[0]}")
        consultant_field = getattr(questionnaire, f"consultant_pdf_{language[0]}")

        client_field.save(
            f"{questionnaire.pk}_client_{language[0]}.pdf",
            ContentFile(client_pdf.read()),
            save=False,
        )
        consultant_field.save(
            f"{questionnaire.pk}_consultant_{language[0]}.pdf",
            ContentFile(consultant_pdf.read()),
            save=False,
        )
        questionnaire.save()
