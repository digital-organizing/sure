# Register your models here.
from axes.admin import AccessAttemptAdmin as BaseAccessAttemptAdmin
from axes.admin import AccessFailureLogAdmin as BaseAccessFailureLogAdmin
from axes.admin import AccessLogAdmin as BaseAccessLogAdmin
from axes.models import AccessAttempt, AccessFailureLog, AccessLog
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.db import models
from django.forms import Form
from django.http.request import HttpRequest
from django.shortcuts import redirect
from django.urls import reverse
from django_agent_trust.admin import AgentSettings
from django_celery_beat.admin import \
    ClockedScheduleAdmin as BaseClockedScheduleAdmin
from django_celery_beat.admin import \
    CrontabScheduleAdmin as BaseCrontabScheduleAdmin
from django_celery_beat.admin import PeriodicTaskAdmin as BasePeriodicTaskAdmin
from django_celery_beat.admin import PeriodicTaskForm, TaskSelectWidget
from django_celery_beat.models import (ClockedSchedule, CrontabSchedule,
                                       IntervalSchedule, PeriodicTask,
                                       SolarSchedule)
from django_celery_results.admin import TaskResultAdmin as BaseTaskResultAdmin
from django_celery_results.models import TaskResult
from django_otp.plugins.otp_hotp.admin import \
    HOTPDeviceAdmin as BaseHOTPDeviceAdmin
from django_otp.plugins.otp_hotp.models import HOTPDevice
from django_otp.plugins.otp_static.admin import \
    StaticDeviceAdmin as BaseStaticDeviceAdmin
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.admin import \
    TOTPDeviceAdmin as BaseTOTPDeviceAdmin
from django_otp.plugins.otp_totp.models import TOTPDevice
from modeltranslation.admin import (TabbedTranslationAdmin,
                                    TranslationStackedInline,
                                    TranslationTabularInline)
from simple_history.admin import SimpleHistoryAdmin
from unfold import widgets
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.components import BaseComponent, register_component
from unfold.decorators import action
from unfold.forms import (AdminPasswordChangeForm, UserChangeForm,
                          UserCreationForm)
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextInputWidget

from sure.cases import case_cohort_by_location, case_cohort_by_tenants
from sure.forms import CohortFilterForm
from sure.models import (ClientOption, ClientQuestion, ConsultantOption,
                         ConsultantQuestion, Questionnaire, ResultInformation,
                         Section, TestBundle, TestCategory, TestKind,
                         TestResultOption, VisitExport)
from sure.tasks import create_export


@admin.register(
    ClientOption,
)
class ClientOptionAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("question", "text", "code", "question__section", "order")
    search_fields = ("question__code", "code", "text", "text_en")
    ordering = (
        "question__section",
        "question",
        "order",
    )


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
    search_fields = ("name", "name_en")
    inlines = [SectionInline, ConsultantQuestionInline]
    ordering = ("name",)


@admin.register(
    Section,
)
class SectionAdmin(SimpleHistoryAdmin, ModelAdmin, TabbedTranslationAdmin):
    list_display = ("title", "questionnaire", "order")
    search_fields = ("title", "questionnaire__name", "title_en")
    list_filter = ("questionnaire",)
    ordering = ("questionnaire__name", "order")
    inlines = [ClientQuestionInline]


@admin.register(
    ClientQuestion,
)
class ClientQuestionAdmin(SimpleHistoryAdmin, ModelAdmin, TabbedTranslationAdmin):
    list_display = ("question_text", "label_en", "section", "order")
    search_fields = ("question_text", "question_text_en")
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
    search_fields = ("question_text", "question_text_en")
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
        if getattr(request.user, "is_superuser", False):
            return queryset
        return queryset.filter(user__consultant__tenant__admins=request.user)

    def save_model(
        self, request: HttpRequest, obj: models.Model, form: Form, change: widgets.Any
    ) -> None:
        if not isinstance(obj, VisitExport):
            raise ValueError("obj must be an instance of VisitExport")
        if not change:
            obj.user = request.user
        super().save_model(request, obj, form, change)

        if not change:
            create_export.delay(obj.pk)

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


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
    search_fields = ("name", "name_en")
    ordering = ("name",)
    inlines = [TestOptionInline]


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
    search_fields = ("name", "name_en")
    ordering = ("name",)
    inlines = [TestKindInline]


@admin.register(
    TestBundle,
)
class TestBundleAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("name",)
    search_fields = ("name", "name_en")
    ordering = ("name",)
    filter_horizontal = ("test_kinds",)


@admin.register(TestResultOption)
class TestResultOptionAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("label", "test_kind", "information_by_sms", "information_text")
    search_fields = ("label", "test_kind__name", "test_kind__name_en", "label_en")

    list_editable = ("information_by_sms", "information_text")

    list_filter = ("label", "test_kind", "test_kind__category")


@admin.register(ResultInformation)
class ResultInformationAdmin(ModelAdmin, TabbedTranslationAdmin):
    list_display = ("option",)
    list_filter = ("locations",)
    search_fields = ("information_text", "information_text_en")
    autocomplete_fields = ("option", "locations")

    fields = ("option", "preview", "information_text", "locations")
    readonly_fields = ("preview",)

    def get_queryset(self, request: HttpRequest) -> models.QuerySet:
        if getattr(request.user, "is_superuser", False):
            return super().get_queryset(request)
        return (
            super().get_queryset(request).filter(locations__tenant__admins=request.user)
        )


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
        if getattr(request.user, "is_superuser", False):
            return super().get_queryset(request)
        if not getattr(request.user, "is_staff", False):
            return User.objects.filter(pk=request.user.pk)
        consultant = getattr(request.user, "consultant", None)
        if not consultant:
            return User.objects.filter(pk=request.user.pk)
        tenant = consultant.tenant
        return super().get_queryset(request).filter(consultant__tenant=tenant)


@admin.register(
    Group,
)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass



admin.site.unregister(StaticDevice)
admin.site.unregister(HOTPDevice)
admin.site.unregister(TOTPDevice)


@admin.register(
    TOTPDevice,
)
class TOTPDeviceAdmin(BaseTOTPDeviceAdmin, ModelAdmin):
    pass


@admin.register(
    StaticDevice,
)
class StaticDeviceAdmin(BaseStaticDeviceAdmin, ModelAdmin):
    pass


@admin.register(
    HOTPDevice,
)
class HOTPDeviceAdmin(BaseHOTPDeviceAdmin, ModelAdmin):
    pass



admin.site.unregister(AccessAttempt)


@admin.register(
    AccessAttempt,
)
class AccessAttemptAdmin(BaseAccessAttemptAdmin, ModelAdmin):
    pass


admin.site.unregister(AccessLog)


@admin.register(
    AccessLog,
)
class AccessLogAdmin(BaseAccessLogAdmin, ModelAdmin):
    pass


admin.site.unregister(AccessFailureLog)


@admin.register(
    AccessFailureLog,
)
class AccessFailureLogAdmin(BaseAccessFailureLogAdmin, ModelAdmin):
    pass



admin.site.unregister(TaskResult)


@admin.register(
    TaskResult,
)
class TaskResultAdmin(BaseTaskResultAdmin, ModelAdmin):
    pass



admin.site.unregister(AgentSettings)


@admin.register(
    AgentSettings,
)
class AgentSettingsAdmin(ModelAdmin):
    pass


@register_component
class CaseCohortComponent(BaseComponent):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = CohortFilterForm(self.request.GET or None, request=self.request)
        filter = None
        if form.is_valid():
            filter = form.get_filter_dict()

        if getattr(self.request.user, "is_superuser", False):
            context["data"] = case_cohort_by_tenants(filter)
        else:
            consultant = getattr(self.request.user, "consultant", None)
            if not consultant:
                context["data"] = []
                return context
            tenant = consultant.tenant
            context["data"] = case_cohort_by_location(tenant, filter)
        return context
