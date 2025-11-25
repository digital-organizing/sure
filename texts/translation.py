from modeltranslation.translator import TranslationOptions, translator

from texts.models import Text


class TextTranslationOptions(TranslationOptions):
    fields = ("content",)


translator.register(Text, TextTranslationOptions)
