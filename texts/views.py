# Create your views here.

from typing import Any

import polars as pl
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Fieldset, Layout
from django import forms
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.edit import FormView
from unfold import widgets
from unfold.layout import Submit
from unfold.views import UnfoldModelAdminViewMixin


class ImportTextForm(forms.Form):
    texts_file = forms.FileField(
        label="Select excel file to import texts",
        widget=widgets.UnfoldAdminFileFieldWidget(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Fieldset(
                "Import Texts from Excel",
                "texts_file",
            ),
            Div(
                Submit("submit", "Import Texts", css_class="btn btn-primary"),
                css_class="mt-4",
            ),
        )


class ImportTextView(UnfoldModelAdminViewMixin, FormView):
    """Admin view for importing texts."""

    title = "Import Texts"
    permission_required = ("texts.add_text",)
    form_class = ImportTextForm
    template_name = "admin/texts/import_texts.html"

    @transaction.atomic
    def form_valid(self, form: Any) -> HttpResponse:
        from django.contrib import messages

        from texts.models import Text

        file = form.cleaned_data["texts_file"]

        # Read the Excel file with polars
        df = pl.read_excel(file.read()).fill_null("")

        # Track statistics
        created_count = 0
        updated_count = 0

        # Process each row
        for row in df.iter_rows(named=True):
            slug = row.get("slug")
            if not slug:
                continue

            # Prepare the data for update/create
            text_data = {
                "context": row.get("context", ""),
                "internal": row.get("internal", False) or False,
                "content_en": row.get("content_en", ""),
                "content_de": row.get("content_de", ""),
                "content_fr": row.get("content_fr", ""),
                "content_it": row.get("content_it", ""),
                "content_es": row.get("content_es", ""),
                "content_pt": row.get("content_pt", ""),
            }

            # Update or create
            text, created = Text.objects.update_or_create(slug=slug, defaults=text_data)

            if created:
                created_count += 1
            else:
                updated_count += 1

        # Add success message
        messages.success(
            self.request,
            f"Import completed: {created_count} texts created, {updated_count} texts updated.",
        )

        return redirect(reverse("admin:texts_text_changelist"))
