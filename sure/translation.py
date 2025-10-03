from modeltranslation.translator import TranslationOptions, translator

from sure.models import (
    ClientOption,
    ClientQuestion,
    ConsultantOption,
    ConsultantQuestion,
    Questionaire,
    Section,
    TestBundle,
    TestCategory,
    TestKind,
    TestResultOption,
)


class QuestionaireTranslationOptions(TranslationOptions):
    fields = ("name",)


translator.register(Questionaire, QuestionaireTranslationOptions)


class SectionTranslationOptions(TranslationOptions):
    fields = (
        "title",
        "description",
    )


translator.register(Section, SectionTranslationOptions)


class QuestionTranslationOptions(TranslationOptions):
    fields = ("question_text", "label")


translator.register(ClientQuestion, QuestionTranslationOptions)
translator.register(ConsultantQuestion, QuestionTranslationOptions)


class OptionTranslationOptions(TranslationOptions):
    fields = ("text",)


translator.register(ClientOption, OptionTranslationOptions)
translator.register(ConsultantOption, OptionTranslationOptions)


class TestKindTranslationOptions(TranslationOptions):
    fields = ("name",)


translator.register(TestKind, TestKindTranslationOptions)


class TestCategoryTranslationOptions(TranslationOptions):
    fields = ("name",)


translator.register(TestCategory, TestCategoryTranslationOptions)


class TestBundleTranslationOptions(TranslationOptions):
    fields = ("name",)


translator.register(TestBundle, TestBundleTranslationOptions)


class TestResultOptionTranslationOptions(TranslationOptions):
    fields = ("information_text", "label")


translator.register(TestResultOption, TestResultOptionTranslationOptions)
