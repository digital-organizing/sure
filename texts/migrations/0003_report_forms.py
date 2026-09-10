from django.db import migrations

TEXTS = {
    "report-forms": {
        "context": "CommunicationView - Title of the prefilled clinical report forms",
        "content": {
            "en": "Clinical reports",
            "de": "Klinische Meldungen",
            "fr": "Déclarations cliniques",
            "it": "Dichiarazioni cliniche",
            "es": "Declaraciones clínicas",
            "pt": "Declarações clínicas",
        },
    },
    "report-forms-info": {
        "context": "CommunicationView - Explanation of the prefilled clinical report forms",
        "content": {
            "en": "Prefilled with the recorded results and the questionnaire. Check and complete the form before sending it to the cantonal doctor.",
            "de": "Vorausgefüllt mit den erfassten Resultaten und dem Fragebogen. Bitte prüfen und vervollständigen, bevor das Formular an die Kantonsärztin oder den Kantonsarzt geht.",
            "fr": "Prérempli avec les résultats saisis et le questionnaire. Veuillez vérifier et compléter le formulaire avant de l'envoyer au médecin cantonal.",
            "it": "Precompilato con i risultati registrati e il questionario. Verificare e completare il modulo prima di inviarlo al medico cantonale.",
            "es": "Rellenado con los resultados registrados y el cuestionario. Revise y complete el formulario antes de enviarlo al médico cantonal.",
            "pt": "Pré-preenchido com os resultados registados e o questionário. Verifique e complete o formulário antes de o enviar ao médico cantonal.",
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
        ("texts", "0002_past_case_warning"),
    ]

    operations = [
        migrations.RunPython(add_texts, remove_texts),
    ]
