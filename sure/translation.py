from modeltranslation.translator import TranslationOptions, translator
import simple_history

from sure.models import (
    ClientOption,
    ClientQuestion,
    ConsultantOption,
    ConsultantQuestion,
    Questionnaire,
    ResultInformation,
    Section,
    TestBundle,
    TestCategory,
    TestKind,
    TestResultOption,
)


class QuestionaireTranslationOptions(TranslationOptions):
    fields = ("name",)


translator.register(Questionnaire, QuestionaireTranslationOptions)
simple_history.register(Questionnaire)


class SectionTranslationOptions(TranslationOptions):
    fields = (
        "title",
        "description",
    )


translator.register(Section, SectionTranslationOptions)
simple_history.register(Section)


class QuestionTranslationOptions(TranslationOptions):
    fields = ("question_text", "label")


translator.register(ClientQuestion, QuestionTranslationOptions)
translator.register(ConsultantQuestion, QuestionTranslationOptions)
simple_history.register(ClientQuestion)
simple_history.register(ConsultantQuestion)


class OptionTranslationOptions(TranslationOptions):
    fields = ("text",)


translator.register(ClientOption, OptionTranslationOptions)
translator.register(ConsultantOption, OptionTranslationOptions)
simple_history.register(ClientOption)
simple_history.register(ConsultantOption)


class TestKindTranslationOptions(TranslationOptions):
    fields = ("name",)


translator.register(TestKind, TestKindTranslationOptions)
simple_history.register(TestKind)


class TestCategoryTranslationOptions(TranslationOptions):
    fields = ("name",)


translator.register(TestCategory, TestCategoryTranslationOptions)


class TestBundleTranslationOptions(TranslationOptions):
    fields = ("name",)


translator.register(TestBundle, TestBundleTranslationOptions)


class TestResultOptionTranslationOptions(TranslationOptions):
    fields = ("information_text", "label")


translator.register(TestResultOption, TestResultOptionTranslationOptions)
simple_history.register(TestResultOption)


class TestResultInformationTranslationOptions(TranslationOptions):
    fields = ("information_text",)
    
translator.register(ResultInformation, TestResultInformationTranslationOptions)
simple_history.register(ResultInformation)