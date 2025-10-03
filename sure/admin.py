# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.db import models
from modeltranslation.admin import (
    TabbedTranslationAdmin,
    TranslationStackedInline,
    TranslationTabularInline,
)
from unfold import widgets
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

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

admin.site.unregister(Group)
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    # Forms loaded from `unfold.forms`
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


class ClientOptionInline(TabularInline, TranslationTabularInline):
    model = ClientOption
    extra = 0
    ordering_field = "order"
    hide_ordering_field = True


class ClientQuestionInline(TabularInline, TranslationTabularInline):
    model = ClientQuestion
    extra = 0
    inlines = [ClientOptionInline]

    ordering_field = "order"
    hide_ordering_field = True

    formfield_overrides = {
        models.TextField: {
            "widget": widgets.UnfoldAdminTextareaWidget(attrs={"rows": 4})
        },
    }

    show_change_link = True


class SectionInline(StackedInline, TranslationStackedInline):
    model = Section
    extra = 0
    inlines = [ClientQuestionInline]

    ordering_field = "order"
    hide_ordering_field = True

    show_change_link = True


class ConsultantOptionInline(TabularInline, TranslationTabularInline):
    model = ConsultantOption
    extra = 0

    ordering_field = "order"
    hide_ordering_field = True


class ConsultantQuestionInline(TabularInline, TranslationTabularInline):
    model = ConsultantQuestion
    extra = 0
    ordering_field = "order"
    hide_ordering_field = True

    formfield_overrides = {
        models.TextField: {
            "widget": widgets.UnfoldAdminTextareaWidget(attrs={"rows": 4})
        },
    }

    show_change_link = True


@admin.register(Questionaire)
class QuestionaireAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = [SectionInline, ConsultantQuestionInline]
    ordering = ("name",)


@admin.register(Section)
class SectionAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("title", "questionaire", "order")
    search_fields = ("title", "questionaire__name")
    list_filter = ("questionaire",)
    ordering = ("questionaire__name", "order")
    inlines = [ClientQuestionInline]


@admin.register(ClientQuestion)
class ClientQuestionAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("question_text", "section", "order")
    search_fields = ("question_text", "section__title")
    list_filter = ("section", "section__questionaire")
    ordering = ("section__questionaire__name", "section__order", "order")
    inlines = [ClientOptionInline]


@admin.register(ConsultantQuestion)
class ConsultantQuestionAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("question_text", "order")
    search_fields = ("question_text",)
    list_filter = ("questionaire",)
    ordering = ("order",)
    inlines = [ConsultantOptionInline]


class TestOptionInline(TabularInline, TranslationTabularInline):
    model = TestResultOption
    extra = 0

    ordering_field = "order"
    hide_ordering_field = True


@admin.register(TestKind)
class TestKindAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = (
        "name",
        "category",
    )

    list_filter = ("category",)
    search_fields = ("name",)
    ordering = ("name",)
    inlines = [TestOptionInline]


class TestKindInline(TabularInline, TranslationTabularInline):
    model = TestKind
    extra = 0
    inlines = [TestOptionInline]

    ordering_field = "order"
    hide_ordering_field = True

    show_change_link = True


@admin.register(TestCategory)
class TestCategoryAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
    inlines = [TestKindInline]


@admin.register(TestBundle)
class TestBundleAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
    filter_horizontal = ("test_kinds",)
