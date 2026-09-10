from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class TestRunner(DiscoverRunner):
    """Keep SECURE_SSL_REDIRECT from answering every test client request with
    a 301 to https. It defaults to on whenever DEBUG is off, e.g. in CI."""

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._no_ssl_redirect = override_settings(SECURE_SSL_REDIRECT=False)
        self._no_ssl_redirect.enable()

    def teardown_test_environment(self, **kwargs):
        self._no_ssl_redirect.disable()
        super().teardown_test_environment(**kwargs)
