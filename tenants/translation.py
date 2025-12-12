import simple_history
from modeltranslation.translator import TranslationOptions, translator

from .models import InformationBanner


class InformationBannerTranslationOptions(TranslationOptions):
    fields = ("content",)


translator.register(InformationBanner, InformationBannerTranslationOptions)
simple_history.register(InformationBanner)
