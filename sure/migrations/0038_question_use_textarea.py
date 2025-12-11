from django.db import migrations, models


def set_use_textarea(apps, schema_editor):
    ClientQuestion = apps.get_model("sure", "ClientQuestion")
    ConsultantQuestion = apps.get_model("sure", "ConsultantQuestion")
    HistoricalClientQuestion = apps.get_model("sure", "HistoricalClientQuestion")
    HistoricalConsultantQuestion = apps.get_model(
        "sure", "HistoricalConsultantQuestion"
    )

    ClientQuestion.objects.filter(code="CONSULT-WISH").update(use_textarea=True)
    ConsultantQuestion.objects.filter(code="CONSULT-WISH").update(use_textarea=True)
    HistoricalClientQuestion.objects.filter(code="CONSULT-WISH").update(
        use_textarea=True
    )
    HistoricalConsultantQuestion.objects.filter(code="CONSULT-WISH").update(
        use_textarea=True
    )


def unset_use_textarea(apps, schema_editor):
    ClientQuestion = apps.get_model("sure", "ClientQuestion")
    ConsultantQuestion = apps.get_model("sure", "ConsultantQuestion")
    HistoricalClientQuestion = apps.get_model("sure", "HistoricalClientQuestion")
    HistoricalConsultantQuestion = apps.get_model(
        "sure", "HistoricalConsultantQuestion"
    )

    ClientQuestion.objects.filter(code="CONSULT-WISH").update(use_textarea=False)
    ConsultantQuestion.objects.filter(code="CONSULT-WISH").update(use_textarea=False)
    HistoricalClientQuestion.objects.filter(code="CONSULT-WISH").update(
        use_textarea=False
    )
    HistoricalConsultantQuestion.objects.filter(code="CONSULT-WISH").update(
        use_textarea=False
    )


class Migration(migrations.Migration):
    dependencies = [
        ("sure", "0037_visitexport_progress_visitexport_total_visits"),
    ]

    operations = [
        migrations.AddField(
            model_name="clientquestion",
            name="use_textarea",
            field=models.BooleanField(
                default=False,
                help_text="Use a textarea instead of a single-line input for text responses",
                verbose_name="Use Textarea",
            ),
        ),
        migrations.AddField(
            model_name="consultantquestion",
            name="use_textarea",
            field=models.BooleanField(
                default=False,
                help_text="Use a textarea instead of a single-line input for text responses",
                verbose_name="Use Textarea",
            ),
        ),
        migrations.AddField(
            model_name="historicalclientquestion",
            name="use_textarea",
            field=models.BooleanField(
                default=False,
                help_text="Use a textarea instead of a single-line input for text responses",
                verbose_name="Use Textarea",
            ),
        ),
        migrations.AddField(
            model_name="historicalconsultantquestion",
            name="use_textarea",
            field=models.BooleanField(
                default=False,
                help_text="Use a textarea instead of a single-line input for text responses",
                verbose_name="Use Textarea",
            ),
        ),
        migrations.RunPython(set_use_textarea, unset_use_textarea),
    ]
