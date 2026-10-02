from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tenants.models import (
    INVITIATION_MAIL_TEMPLATE,
    render_invitation_mail,
    validate_invitation_mail_template,
)

VALUES = {
    "first_name": "Ada & Co",
    "tenant.name": "Center",
    "user.get_full_name": "Grace Hopper",
    "activation_link": "https://example.com/setup?a=1&b=2",
}


class InvitationMailTemplateTests(SimpleTestCase):
    def test_default_template_is_valid_and_filled_in(self):
        validate_invitation_mail_template(INVITIATION_MAIL_TEMPLATE)

        message = render_invitation_mail(INVITIATION_MAIL_TEMPLATE, VALUES)

        self.assertIn("Hello Ada & Co,", message)
        self.assertIn("for Center on SURE by Grace Hopper.", message)
        self.assertIn("https://example.com/setup?a=1&b=2", message)
        self.assertNotIn("{{", message)

    def test_spacing_inside_the_braces_does_not_matter(self):
        self.assertEqual(
            render_invitation_mail("{{first_name}}/{{  tenant.name }}", VALUES),
            "Ada & Co/Center",
        )

    def test_other_lookups_are_rejected(self):
        for template in (
            "{{ tenant.owner.password }}",
            "{{ user.email }}",
            "{{ first_name|upper }}",
            "{% for token in tenant.api_tokens.all %}{{ token.token }}{% endfor %}",
            "{% load static %}",
        ):
            with self.subTest(template=template), self.assertRaises(ValidationError):
                validate_invitation_mail_template(template)

    def test_stored_template_with_other_lookups_is_not_evaluated(self):
        template = "{{ tenant.owner.password }} {% debug %} {{ first_name }}"

        self.assertEqual(
            render_invitation_mail(template, VALUES),
            "{{ tenant.owner.password }} {% debug %} Ada & Co",
        )

    def test_values_are_not_expanded_again(self):
        values = {**VALUES, "first_name": "{{ activation_link }}"}

        self.assertEqual(
            render_invitation_mail("{{ first_name }}", values), "{{ activation_link }}"
        )
