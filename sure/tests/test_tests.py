from django.test import TestCase


class TestTests(TestCase):
    def test_import(self):
        from sure.health_test import import_from_excel

        import_from_excel("sure/tests/data/SURE_Q.xlsx")
