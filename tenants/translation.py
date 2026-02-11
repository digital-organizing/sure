import simple_history
from modeltranslation.translator import TranslationOptions, translator

from .models import InformationBanner, Advertisement, Location


class InformationBannerTranslationOptions(TranslationOptions):
    fields = ("content",)


class AdvertisementTranslationOptions(TranslationOptions):
    fields = ("content",)


class LocationTranslationOptions(TranslationOptions):
    fields = ("reminder_text",)


translator.register(InformationBanner, InformationBannerTranslationOptions)
simple_history.register(InformationBanner)

translator.register(Advertisement, AdvertisementTranslationOptions)
simple_history.register(Advertisement)

translator.register(Location, LocationTranslationOptions)
simple_history.register(Location)
