from unittest import mock

from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class TestRunner(DiscoverRunner):
    """Keep tests independent of the environment they run in:

    - SECURE_SSL_REDIRECT defaults to on whenever DEBUG is off (e.g. in CI) and
      would answer every test client request with a 301 to https.
    - Uploads would be sent to whatever clamd CLAMD_TCP_ADDR points at, and fail
      where there is none. django_clamd reads its settings at import time, so
      the flag is patched on the validator module instead of overridden.
    """

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._overrides = [
            override_settings(SECURE_SSL_REDIRECT=False),
            mock.patch("django_clamd.validators.CLAMD_ENABLED", False),
        ]
        for override in self._overrides:
            override.__enter__()

    def teardown_test_environment(self, **kwargs):
        for override in reversed(self._overrides):
            override.__exit__(None, None, None)
        super().teardown_test_environment(**kwargs)
