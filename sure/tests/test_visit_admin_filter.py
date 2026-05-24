from django.contrib import admin
from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory

from sure.admin import TagListFilter, VisitAdmin
from sure.models import Visit, Questionnaire, Case
from tenants.models import Location, Tenant, Consultant

class VisitAdminFilterTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(username="super", password="password")
        self.tenant_admin_user = User.objects.create_user(username="admin1", password="password")
        self.tenant_admin_user.is_staff = True
        self.tenant_admin_user.save()
        
        self.tenant1 = Tenant.objects.create(name="Tenant 1", owner=self.tenant_admin_user)
        self.tenant1.admins.add(self.tenant_admin_user)
        
        self.location1 = Location.objects.create(name="Loc 1", tenant=self.tenant1)
        
        self.consultant1 = Consultant.objects.create(tenant=self.tenant1, user=self.tenant_admin_user)
        self.consultant1.locations.add(self.location1)

        self.q = Questionnaire.objects.create(name="Test Q")

        # Create cases and visits for tenant 1
        self.case1 = Case.objects.create(location=self.location1)
        self.visit1 = Visit.objects.create(case=self.case1, questionnaire=self.q, tags=["blue", "red"])

        self.case2 = Case.objects.create(location=self.location1)
        self.visit2 = Visit.objects.create(case=self.case2, questionnaire=self.q, tags=["red"])

        # Create another tenant and a visit to verify tenant-scoping of tags list
        self.other_admin = User.objects.create_user(username="other_admin")
        self.tenant2 = Tenant.objects.create(name="Tenant 2", owner=self.other_admin)
        self.location2 = Location.objects.create(name="Loc 2", tenant=self.tenant2)
        self.case3 = Case.objects.create(location=self.location2)
        self.visit3 = Visit.objects.create(case=self.case3, questionnaire=self.q, tags=["green"])

    def test_tag_filter_lookups_superuser(self):
        # Superuser should see all tags across all tenants
        request = self.factory.get("/admin/sure/visit/")
        request.user = self.superuser
        
        visit_admin = VisitAdmin(Visit, admin.site)
        tag_filter = TagListFilter(request, {}, Visit, visit_admin)
        
        choices = tag_filter.lookups(request, visit_admin)
        self.assertEqual(choices, [("blue", "blue"), ("green", "green"), ("red", "red")])

    def test_tag_filter_lookups_tenant_admin(self):
        # Tenant admin should only see tags from visits in their own tenant
        request = self.factory.get("/admin/sure/visit/")
        request.user = self.tenant_admin_user
        
        visit_admin = VisitAdmin(Visit, admin.site)
        tag_filter = TagListFilter(request, {}, Visit, visit_admin)
        
        choices = tag_filter.lookups(request, visit_admin)
        self.assertEqual(choices, [("blue", "blue"), ("red", "red")])

    def test_tag_filter_queryset(self):
        request = self.factory.get("/admin/sure/visit/", {"tag": "red"})
        request.user = self.superuser
        
        visit_admin = VisitAdmin(Visit, admin.site)
        
        # Test filtering by 'red'
        tag_filter = TagListFilter(request, {"tag": ["red"]}, Visit, visit_admin)
        qs = tag_filter.queryset(request, visit_admin.get_queryset(request))
        self.assertEqual(list(qs.order_by("pk")), [self.visit1, self.visit2])

        # Test filtering by 'blue'
        tag_filter_blue = TagListFilter(request, {"tag": ["blue"]}, Visit, visit_admin)
        qs_blue = tag_filter_blue.queryset(request, visit_admin.get_queryset(request))
        self.assertEqual(list(qs_blue), [self.visit1])
