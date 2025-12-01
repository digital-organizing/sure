from datetime import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from tenants.models import Location, Tenant


class TestLocation(TestCase):
    def test_opening_hours(self):
        user = User.objects.create_user(username="testuser", password="testpass")
        tenant = Tenant.objects.create(
            name="Test Tenant",
            owner=user,
        )
        location = Location.objects.create(
            tenant=tenant,
            name="Test Location",
            opening_hours={
                "monday": [["09:00", "12:00"], ["13:00", "17:00"]],
                "tuesday": [["09:00", "12:00"], ["13:00", "17:00"]],
                "wednesday": [["09:00", "12:00"], ["13:00", "17:00"]],
                "thursday": [["09:00", "12:00"], ["13:00", "17:00"]],
                "friday": [["09:00", "12:00"], ["13:00", "17:00"]],
                "saturday": [],
                "sunday": [],
            },
        )

        date_1 = datetime(2024, 6, 3, 10, 0)  # Monday

        next_opening_1 = location.get_next_opening(date_1)
        self.assertEqual(next_opening_1, datetime(2024, 6, 3, 9, 0))

        date_2 = datetime(2024, 6, 3, 18, 0)  # Monday after hours
        next_opening_2 = location.get_next_opening(date_2)
        self.assertEqual(next_opening_2, datetime(2024, 6, 4, 9, 0))
