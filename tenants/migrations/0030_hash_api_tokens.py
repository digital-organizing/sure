import hashlib

from django.db import migrations, models


def hash_tokens(apps, schema_editor):
    """Existing tokens keep working: they are hashed in place."""
    APIToken = apps.get_model("tenants", "APIToken")
    for api_token in APIToken.objects.all():
        api_token.token_hash = hashlib.sha256(api_token.token.encode()).hexdigest()
        api_token.token_hint = api_token.token[-4:]
        api_token.save(update_fields=["token_hash", "token_hint"])


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0029_invitation_mail_placeholders"),
    ]

    operations = [
        migrations.AddField(
            model_name="apitoken",
            name="token_hash",
            field=models.CharField(default="", editable=False, max_length=64),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="apitoken",
            name="token_hint",
            field=models.CharField(
                default="",
                editable=False,
                help_text="Last characters of the token, to tell tokens apart",
                max_length=4,
            ),
            preserve_default=False,
        ),
        # The plain tokens are gone afterwards, so this cannot be undone.
        migrations.RunPython(hash_tokens, migrations.RunPython.noop),
        migrations.RemoveField(model_name="apitoken", name="token"),
    ]
