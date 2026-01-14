from collections.abc import Callable
from functools import wraps
from typing import Any

from django.conf import settings
from django.http import HttpRequest
from django.utils import translation
from django.utils.translation import get_language_from_request
from ninja import Query, Schema
from ninja.utils import contribute_operation_args


def _activate_language_for_request(request, lang: str | None = None):
    if lang is None:
        lang = (
            get_language_from_request(request)
            or settings.MODELTRANSLATION_DEFAULT_LANGUAGE
        )

    if lang:
        translation.activate(lang)


class LangSchema(Schema):
    lang: str | None = settings.MODELTRANSLATION_DEFAULT_LANGUAGE


def inject_language(func: Callable) -> Callable:
    """Inject language parameter into Django Ninja endpoint."""

    @wraps(func)
    def view_with_language(request: HttpRequest, **kwargs: Any) -> Any:
        # Extract the language parameter that Ninja injected
        lang = kwargs.pop("lang", None)

        _activate_language_for_request(request, lang.lang)

        return func(request, **kwargs)

    contribute_operation_args(
        view_with_language,
        arg_name="lang",
        arg_type=LangSchema,
        arg_source=Query(...),  # type: ignore
    )

    return view_with_language
