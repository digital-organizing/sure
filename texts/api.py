from django.conf import settings
from django.utils import translation
from ninja import ModelSchema, Schema
from ninja.router import Router

from sure.lang import inject_language
from texts.models import Text

router = Router()


class TextSchema(ModelSchema):
    class Meta:
        model = Text
        fields = ["content"]


class TextsSchema(Schema):
    texts: dict[str, str]
    right_to_left: bool
    language: str | None = None


@router.get("texts/", response=TextsSchema, auth=None)
@inject_language
def list_texts(request):
    texts = (
        Text.objects.all()
        if request.user.is_authenticated
        else Text.objects.filter(internal=False)
    )
    return {
        "language": translation.get_language(),
        "right_to_left": translation.get_language_bidi(),
        "texts": dict(list(texts.values_list("slug", "content"))),
    }


@router.get("languages/", response=list[tuple[str, str]], auth=None)
def list_languages(request):
    return settings.LANGUAGES
