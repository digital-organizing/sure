from django.db import migrations

# Errors the backend returns to clients, which were missing or untranslated.
TEXTS = {
    "client-submit-not-allowed": {
        "context": "ClientFormView - Error when the questionnaire can no longer be submitted",
        "internal": False,
        "content": {
            "en": "Your answers could not be submitted because the questionnaire is already closed. Please contact the staff.",
            "de": "Ihre Antworten konnten nicht übermittelt werden, da der Fragebogen bereits abgeschlossen ist. Bitte wenden Sie sich an das Personal.",
            "fr": "Vos réponses n'ont pas pu être transmises, car le questionnaire est déjà clôturé. Veuillez vous adresser au personnel.",
            "it": "Le sue risposte non hanno potuto essere trasmesse perché il questionario è già chiuso. Si rivolga al personale.",
            "es": "No se han podido enviar sus respuestas porque el cuestionario ya está cerrado. Diríjase al personal.",
            "pt": "Não foi possível enviar as suas respostas porque o questionário já está fechado. Dirija-se ao pessoal.",
        },
    },
    "client-key-not-allowed": {
        "context": "ClientPhoneNumberView - Error when the password can no longer be set",
        "internal": False,
        "content": {
            "en": "The password can no longer be set for this case. Please contact the staff.",
            "de": "Das Passwort kann für diesen Fall nicht mehr gesetzt werden. Bitte wenden Sie sich an das Personal.",
            "fr": "Le mot de passe ne peut plus être défini pour ce cas. Veuillez vous adresser au personnel.",
            "it": "La password non può più essere impostata per questo caso. Si rivolga al personale.",
            "es": "Ya no se puede establecer la contraseña para este caso. Diríjase al personal.",
            "pt": "Já não é possível definir a palavra-passe para este caso. Dirija-se ao pessoal.",
        },
    },
    "recent-token-error": {
        "context": "ClientPhoneNumberView - Error when a new code is requested too soon",
        "internal": False,
        "content": {
            "en": "A code was sent recently. Please wait a few minutes before requesting a new one.",
            "de": "Es wurde kürzlich ein Code gesendet. Bitte warten Sie einige Minuten, bevor Sie einen neuen anfordern.",
            "fr": "Un code a été envoyé récemment. Veuillez patienter quelques minutes avant d'en demander un nouveau.",
            "it": "Un codice è stato inviato di recente. Attenda qualche minuto prima di richiederne uno nuovo.",
            "es": "Se ha enviado un código recientemente. Espere unos minutos antes de solicitar uno nuevo.",
            "pt": "Foi enviado um código recentemente. Aguarde alguns minutos antes de pedir um novo.",
        },
    },
    "case-cannot-be-connected": {
        "context": "ClientPhoneNumberView - Error when the case is already linked to a phone",
        "internal": False,
        "content": {
            "en": "This case is already linked to a phone number.",
            "de": "Dieser Fall ist bereits mit einer Telefonnummer verknüpft.",
            "fr": "Ce cas est déjà associé à un numéro de téléphone.",
            "it": "Questo caso è già collegato a un numero di telefono.",
            "es": "Este caso ya está vinculado a un número de teléfono.",
            "pt": "Este caso já está associado a um número de telefone.",
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
                "internal": text["internal"],
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
        ("texts", "0003_report_forms"),
    ]

    operations = [
        migrations.RunPython(add_texts, remove_texts),
    ]
