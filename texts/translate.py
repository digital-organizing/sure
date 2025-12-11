from django.utils.translation import get_language, activate
from .models import Text


def translate(slug, language=None):
    old_language = get_language()
    try:
        if language:
            activate(language)
        text = Text.objects.filter(slug=slug).first()
        if not text:
            return slug
        return text.content
    finally:
        activate(old_language)
