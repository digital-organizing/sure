import deepl
from celery import shared_task
from django.conf import settings
from django.utils.translation import activate

from .models import Text


@shared_task
def translate_text_task(slug, language):
    text = Text.objects.get(slug=slug)

    client = deepl.Translator(settings.DEEPL_API_KEY)

    activate("en")
    text_orig = text.content

    result = client.translate_text(
        text=text_orig,
        source_lang="EN",
        target_lang=language if language != "pt" else "PT-PT",
        context=text.context or None,
        formality="prefer_more",
    )

    activate(language)
    if isinstance(result, list):
        text.content = result[0].text  # type: ignore
    else:
        text.content = result.text
    text.save()
