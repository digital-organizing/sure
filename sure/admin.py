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

from django.utils.translation import gettext_lazy as _
from django.urls import URLPattern, path, reverse
from django_agent_trust.admin import AgentSettings
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
from django_celery_results.admin import TaskResultAdmin as BaseTaskResultAdmin
from django_celery_results.models import TaskResult
from django_otp.plugins.otp_hotp.admin import HOTPDeviceAdmin as BaseHOTPDeviceAdmin
from django_otp.plugins.otp_hotp.models import HOTPDevice
from django_otp.plugins.otp_static.admin import (
    StaticDeviceAdmin as BaseStaticDeviceAdmin,
)
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.admin import TOTPDeviceAdmin as BaseTOTPDeviceAdmin
from django_otp.plugins.otp_totp.models import TOTPDevice
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
from unfold.forms import (
    AdminPasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextInputWidget

from sure.cases import case_cohort_by_location, case_cohort_by_tenants
from sure.forms import CohortFilterForm
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
    Visit,
    VisitExport,
    VisitExportDownload,
    VisitStatus,
)
from sure.views import GenerateCaseBatchView
from sure.tasks import create_export, generate_pdf_task
from labor.models import TestProfile


class TestProfileInline(StackedInline):
    model = TestProfile
    extra = 0
    autocomplete_fields = ("laboratory",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(laboratory__managers=request.user)


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
    filter_vertical = ("locations",)

    readonly_fields = ("client_pdf", "consultant_pdf")

    actions_detail = ["generate_pdf_action", "duplicate_questionnaire_action"]

    fieldsets = (
        (
            "Questionnaire Information",
            {"classes": ["tab"], "fields": ("name", "order", "locations")},
        ),
        (
            "Questionnaire PDFs",
            {
                "classes": ["tab"],
                "fields": (
                    "client_pdf",
                    "consultant_pdf",
                ),
            },
        ),
    )

    @action(description="Generate PDFs")  # ty:ignore[call-non-callable]
    def generate_pdf_action(self, request, object_id):
        generate_pdf_task.delay(object_id)

        return redirect(reverse("admin:sure_questionnaire_change", args=[object_id]))

    def _clone_instance(self, obj, **overrides):
        """
        Helper method to clone a model instance, overriding specified fields.
        Crucially copies all modeltranslation translated fields as they are part of _meta.fields.
        """
        field_values = {}
        for field in obj._meta.fields:
            if field.primary_key:
                continue
            field_values[field.attname] = getattr(obj, field.attname)

        field_values.update(overrides)
        return obj.__class__.objects.create(**field_values)

    def _duplicate_single_questionnaire(self, original):
        """
        Duplicates a single questionnaire including all its sections, questions,
        options, and conditional show logic, while clearing the locations and visits.
        """
        from django.db import transaction

        with transaction.atomic():
            # 1. Clone the Questionnaire instance overriding name/name_* fields
            questionnaire_overrides = {}
            for field in original._meta.fields:
                if field.primary_key:
                    continue
                val = getattr(original, field.attname)
                if (field.name == "name" or field.name.startswith("name_")) and val:
                    questionnaire_overrides[field.attname] = f"{val} (Copy)"

            new_q = self._clone_instance(original, **questionnaire_overrides)

            # Keep mappings to build the show_for_options relations correctly.
            option_mapping = {}  # maps old ClientOption.pk -> new ClientOption instance
            question_mapping = {}  # maps old ClientQuestion.pk -> new ClientQuestion instance

            # 2. Duplicate Sections and their questions/options
            for section in original.sections.all():
                new_section = self._clone_instance(section, questionnaire_id=new_q.id)

                for question in section.client_questions.all():
                    new_question = self._clone_instance(
                        question, section_id=new_section.id
                    )
                    question_mapping[question.pk] = new_question

                    for option in question.options.all():
                        new_option = self._clone_instance(
                            option, question_id=new_question.id
                        )
                        option_mapping[option.pk] = new_option

            # 3. Resolve the show_for_options ManyToMany relations
            for old_question_id, new_question in question_mapping.items():
                old_question = ClientQuestion.objects.get(pk=old_question_id)
                old_show_options = old_question.show_for_options.all()
                if old_show_options.exists():
                    new_show_options = [
                        option_mapping[old_opt.pk]
                        for old_opt in old_show_options
                        if old_opt.pk in option_mapping
                    ]
                    if new_show_options:
                        new_question.show_for_options.set(new_show_options)

            # 4. Duplicate ConsultantQuestions and their options
            for question in original.consultant_questions.all():
                new_c_question = self._clone_instance(
                    question, questionnaire_id=new_q.id
                )
                for option in question.options.all():
                    self._clone_instance(option, question_id=new_c_question.id)

            return new_q

    @action(description=_("Duplicate questionnaire"))  # ty:ignore[call-non-callable,invalid-argument-type]
    def duplicate_questionnaire_action(self, request, object_id):
        if not self.has_add_permission(request):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied

        original = Questionnaire.objects.get(pk=object_id)
        new_q = self._duplicate_single_questionnaire(original)

        self.message_user(request, _("Successfully duplicated the questionnaire."))
        return redirect(reverse("admin:sure_questionnaire_change", args=[new_q.pk]))

    duplicate_questionnaire_action.allowed_permissions = ["add"]

    def has_add_permission(self, request, *args, **kwargs):
        return super().has_add_permission(request)


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


class VisitExportDownloadInline(TabularInline):
    model = VisitExportDownload
    extra = 0
    readonly_fields = ("downloaded_at", "user")
    can_delete = False

    per_page = 10


@admin.register(
    VisitExport,
)
class VisitExportAdmin(ModelAdmin):
    list_display = (
        "created_at",
        "user",
        "status",
        "start_date",
        "end_date",
        "download_url",
    )
    list_filter = ("status", "created_at", "start_date", "end_date", "user")

    readonly_fields = (
        "created_at",
        "status",
        "download_url",
        "error_message",
        "total_visits",
        "progress",
    )
    exclude = ("user", "file")

    actions_detail = ["start_export_obj"]

    actions = ["start_export"]

    date_hierarchy = "created_at"

    inlines = [VisitExportDownloadInline]

    @action
    def start_export(self, request: HttpRequest, queryset):
        for export in queryset.values_list("id", flat=True):
            create_export.delay(export.pk)

    @action(description="Start Export")  # ty:ignore[call-non-callable]
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
    inlines = [TestOptionInline, TestProfileInline]


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
        print(context)
        context["form"] = form
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


class TagListFilter(admin.SimpleListFilter):
    title = _("Tag")
    parameter_name = "tag"

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        tags_set = set()
        for tags in qs.exclude(tags=[]).values_list("tags", flat=True):
            if tags:
                tags_set.update(tags)
        return sorted([(tag, tag) for tag in tags_set if tag])

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(tags__contains=[self.value()])
        return queryset


@admin.register(Visit)
class VisitAdmin(ModelAdmin):
    list_display = (
        "case_human_id",
        "case_external_id",
        "case_location",
        "questionnaire",
        "status",
        "created_at",
        "display_tags",
    )
    list_filter = ("status", "created_at", "questionnaire", TagListFilter)
    search_fields = ("case__id", "case__external_id", "tags")
    readonly_fields = ("created_at",)

    actions_list = ["generate_batch"]
    actions = ["cancel_cases"]

    def case_human_id(self, obj: Visit) -> str:
        return obj.case.human_id

    case_human_id.short_description = "Case ID"  # ty:ignore[unresolved-attribute]

    def case_location(self, obj: Visit) -> str:
        return obj.case.location.name

    def case_external_id(self, obj: Visit) -> str:
        return obj.case.external_id

    case_external_id.short_description = "Internal ID"  # ty:ignore[unresolved-attribute]

    def display_tags(self, obj: Visit) -> str:
        return ", ".join(obj.tags) if obj.tags else ""

    display_tags.short_description = "Tags"  # ty:ignore[unresolved-attribute]

    def get_queryset(self, request: HttpRequest) -> models.QuerySet[Visit]:
        queryset = super().get_queryset(request)
        if getattr(request.user, "is_superuser", False):
            return queryset
        # If staff but not superuser, they must be a tenant admin
        tenants = request.user.tenants.all()  # ty:ignore[unresolved-attribute]
        return queryset.filter(case__location__tenant__in=tenants)

    @action(description="Generate Batch", icon="layers")  # ty:ignore[call-non-callable]
    def generate_batch(self, request: HttpRequest):
        return redirect(reverse("admin:sure_visit_generate_batch_view"))

    def get_urls(self) -> list[URLPattern]:
        generate_view = self.admin_site.admin_view(
            GenerateCaseBatchView.as_view(model_admin=self)
        )
        return [
            path(
                "generate-batch/", generate_view, name="sure_visit_generate_batch_view"
            ),
        ] + super().get_urls()

    @action(description="Cancel cases")  # ty:ignore[call-non-callable]
    def cancel_cases(self, request: HttpRequest, queryset: models.QuerySet[Visit]):
        for visit in queryset:
            visit.status = VisitStatus.CANCELED
            visit.save()

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False
