import simple_history
from modeltranslation.translator import TranslationOptions, translator

from .models import InformationBanner, Location


class InformationBannerTranslationOptions(TranslationOptions):
    fields = ("content",)


class LocationTranslationOptions(TranslationOptions):
    fields = ("reminder_text",)


translator.register(InformationBanner, InformationBannerTranslationOptions)
simple_history.register(InformationBanner)

translator.register(Location, LocationTranslationOptions)
