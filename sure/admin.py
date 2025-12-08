# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.db import models
from django.forms import Form
from django.http.request import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django_celery_beat.admin import ClockedScheduleAdmin as BaseClockedScheduleAdmin
from django_celery_beat.admin import CrontabScheduleAdmin as BaseCrontabScheduleAdmin
from django_celery_beat.admin import PeriodicTaskAdmin as BasePeriodicTaskAdmin
from django_celery_beat.admin import PeriodicTaskForm, TaskSelectWidget
from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)
from modeltranslation.admin import (
    TabbedTranslationAdmin,
    TranslationStackedInline,
    TranslationTabularInline,
)
from simple_history.admin import SimpleHistoryAdmin
from unfold import widgets
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.components import BaseComponent, register_component
from unfold.decorators import action
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextInputWidget

from sure.cases import case_cohort_by_location, case_cohort_by_tenants
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
    VisitExport,
)
from sure.tasks import create_export


@admin.register(
    ClientOption,
)
class ClientOptionAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("text", "order")
    search_fields = ("question__code", "code")
    ordering = ("order",)


class ClientOptionInline(TabularInline, TranslationTabularInline):
    model = ClientOption
    extra = 1
    ordering_field = "order"
    hide_ordering_field = True


class ClientQuestionInline(TabularInline, TranslationTabularInline):
    model = ClientQuestion
    extra = 1

    ordering_field = "order"
    hide_ordering_field = True

    formfield_overrides = {
        models.TextField: {
            "widget": widgets.UnfoldAdminTextareaWidget(attrs={"rows": 4})
        },
    }

    show_change_link = True

    autocomplete_fields = ("show_for_options",)


class SectionInline(StackedInline, TranslationStackedInline):
    model = Section
    extra = 1

    ordering_field = "order"
    hide_ordering_field = True

    show_change_link = True


class ConsultantOptionInline(TabularInline, TranslationTabularInline):
    model = ConsultantOption
    extra = 1

    ordering_field = "order"
    hide_ordering_field = True


class ConsultantQuestionInline(TabularInline, TranslationTabularInline):
    model = ConsultantQuestion
    extra = 1
    ordering_field = "order"
    hide_ordering_field = True

    formfield_overrides = {
        models.TextField: {
            "widget": widgets.UnfoldAdminTextareaWidget(attrs={"rows": 4})
        },
    }

    show_change_link = True


@admin.register(
    Questionnaire,
)
class QuestionaireAdmin(SimpleHistoryAdmin, ModelAdmin, TabbedTranslationAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    inlines = [SectionInline, ConsultantQuestionInline]
    ordering = ("name",)


@admin.register(
    Section,
)
class SectionAdmin(SimpleHistoryAdmin, ModelAdmin, TabbedTranslationAdmin):
    list_display = ("title", "questionnaire", "order")
    search_fields = ("title", "questionnaire__name")
    list_filter = ("questionnaire",)
    ordering = ("questionnaire__name", "order")
    inlines = [ClientQuestionInline]


@admin.register(
    ClientQuestion,
)
class ClientQuestionAdmin(SimpleHistoryAdmin, ModelAdmin, TabbedTranslationAdmin):
    list_display = ("question_text", "label_en", "section", "order")
    search_fields = ("question_text", "section__title")
    list_filter = ("section", "section__questionnaire")
    ordering = ("section__questionnaire__name", "section__order", "order")
    list_editable = ("label_en",)
    inlines = [ClientOptionInline]

    autocomplete_fields = ("show_for_options",)


@admin.register(
    ConsultantQuestion,
)
class ConsultantQuestionAdmin(SimpleHistoryAdmin, ModelAdmin, TabbedTranslationAdmin):
    list_display = ("question_text", "order")
    search_fields = ("question_text",)
    list_filter = ("questionnaire",)
    ordering = ("order",)
    inlines = [ConsultantOptionInline]


@admin.register(
    VisitExport,
)
class VisitExportAdmin(ModelAdmin):
    list_display = ("created_at", "user", "status", "start_date", "end_date", "file")
    list_filter = ("status", "created_at", "start_date", "end_date", "user")

    readonly_fields = (
        "created_at",
        "status",
        "file",
        "error_message",
        "total_visits",
        "progress",
    )
    exclude = ("user",)

    actions_detail = ["start_export_obj"]

    actions = ["start_export"]

    date_hierarchy = "created_at"

    @action
    def start_export(self, request: HttpRequest, queryset):
        for export in queryset.values_list("id", flat=True):
            create_export(export)

    @action(description="Start Export")
    def start_export_obj(self, request, object_id):
        create_export.delay(object_id)
        return redirect(reverse("admin:sure_visitexport_change", args=[object_id]))

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(user__consultant__tenant=request.user.consultant.tenant)

    def save_model(
        self, request: HttpRequest, obj: VisitExport, form: Form, change: widgets.Any
    ) -> None:
        if not change:
            obj.user = request.user
        super().save_model(request, obj, form, change)

        if not change:
            create_export.delay(obj.pk)


class TestOptionInline(TabularInline, TranslationTabularInline):
    model = TestResultOption
    extra = 1


@admin.register(
    TestKind,
)
class TestKindAdmin(SimpleHistoryAdmin, ModelAdmin, TabbedTranslationAdmin):
    list_display = (
        "name",
        "category",
    )

    list_filter = ("category",)
    search_fields = ("name",)
    ordering = ("name",)
    inlines = [TestOptionInline]

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        print(request.user.is_superuser)
        queryset = super().get_queryset(request)
        print(queryset.count())
        return queryset


class TestKindInline(TabularInline, TranslationTabularInline):
    model = TestKind
    extra = 1
    inlines = [TestOptionInline]

    show_change_link = True


@admin.register(
    TestCategory,
)
class TestCategoryAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
    inlines = [TestKindInline]


@admin.register(
    TestBundle,
)
class TestBundleAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    ordering = ("name",)
    filter_horizontal = ("test_kinds",)


@admin.register(TestResultOption)
class TestResultOptionAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("label", "test_kind", "information_by_sms", "information_text")
    search_fields = ("label", "test_kind__name")

    list_editable = ("information_by_sms", "information_text")

    list_filter = ("label", "test_kind")


@admin.register(ResultInformation)
class ResultInformationAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("option",)
    list_filter = ("locations",)
    search_fields = ("information_text",)
    autocomplete_fields = ("option", "locations")


admin.site.unregister(PeriodicTask)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(SolarSchedule)
admin.site.unregister(ClockedSchedule)


class UnfoldTaskSelectWidget(UnfoldAdminSelectWidget, TaskSelectWidget):
    pass


class UnfoldPeriodicTaskForm(PeriodicTaskForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["task"].widget = UnfoldAdminTextInputWidget()
        self.fields["regtask"].widget = UnfoldTaskSelectWidget()


@admin.register(
    PeriodicTask,
)
class PeriodicTaskAdmin(BasePeriodicTaskAdmin, ModelAdmin):
    form = UnfoldPeriodicTaskForm


@admin.register(
    IntervalSchedule,
)
class IntervalScheduleAdmin(ModelAdmin):
    pass


@admin.register(
    CrontabSchedule,
)
class CrontabScheduleAdmin(BaseCrontabScheduleAdmin, ModelAdmin):
    pass


@admin.register(
    SolarSchedule,
)
class SolarScheduleAdmin(ModelAdmin):
    pass


@admin.register(
    ClockedSchedule,
)
class ClockedScheduleAdmin(BaseClockedScheduleAdmin, ModelAdmin):
    pass


admin.site.unregister(Group)
admin.site.unregister(User)


@admin.register(
    User,
)
class UserAdmin(SimpleHistoryAdmin, BaseUserAdmin, ModelAdmin):
    # Forms loaded from `unfold.forms`
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        if request.user.is_superuser:
            return super().get_queryset(request)
        if not request.user.is_staff:
            return User.objects.filter(pk=request.user.pk)
        tenant = request.user.consultant.tenant
        return super().get_queryset(request).filter(consultant__tenant=tenant)


@admin.register(
    Group,
)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@register_component
class CaseCohortComponent(BaseComponent):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_superuser:
            context["data"] = case_cohort_by_tenants()
        else:
            tenant = self.request.user.consultant.tenant
            context["data"] = case_cohort_by_location(tenant)
        return context
