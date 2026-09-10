from django.db import migrations

TEXTS = {
    "past-case-warning": {
        "context": "CaseView - Warning on closed cases of other tenants or older than a month",
        "content": {
            "en": "This is a closed case from {date} at {location}. Be careful when changing the data retroactively.",
            "de": "Das ist ein abgeschlossener Fall vom {date} in {location}. Vorsicht bei rückwirkender Änderung der Daten.",
            "fr": "Il s'agit d'un cas clôturé du {date} à {location}. Prudence en cas de modification rétroactive des données.",
            "it": "Questo è un caso chiuso del {date} a {location}. Attenzione alle modifiche retroattive dei dati.",
            "es": "Este es un caso cerrado del {date} en {location}. Tenga cuidado al modificar los datos de forma retroactiva.",
            "pt": "Este é um caso encerrado de {date} em {location}. Cuidado ao alterar os dados retroativamente.",
        },
    },
    "past-case-warning-open": {
        "context": "CaseView - Warning on open cases of other tenants or older than a month",
        "content": {
            "en": 'This is a case from {date} at {location} with status "{status}". Be careful when changing the data retroactively.',
            "de": "Das ist ein Fall vom {date} in {location} mit Status «{status}». Vorsicht bei rückwirkender Änderung der Daten.",
            "fr": "Il s'agit d'un cas du {date} à {location} avec le statut « {status} ». Prudence en cas de modification rétroactive des données.",
            "it": "Questo è un caso del {date} a {location} con stato «{status}». Attenzione alle modifiche retroattive dei dati.",
            "es": "Este es un caso del {date} en {location} con el estado «{status}». Tenga cuidado al modificar los datos de forma retroactiva.",
            "pt": "Este é um caso de {date} em {location} com o estado «{status}». Cuidado ao alterar os dados retroativamente.",
        },
    },
}


def add_texts(apps, schema_editor):
    Text = apps.get_model("texts", "Text")
    for slug, text in TEXTS.items():
        # Leave texts that were already created or edited in the admin untouched.
        Text.objects.get_or_create(
            slug=slug,
            defaults={
                "context": text["context"],
                "content": text["content"]["en"],
                "internal": True,
                **{
                    f"content_{lang}": content
                    for lang, content in text["content"].items()
                },
            },
        )


def remove_texts(apps, schema_editor):
    apps.get_model("texts", "Text").objects.filter(slug__in=TEXTS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("texts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_texts, remove_texts),
    ]
