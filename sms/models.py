from django.db import models

# Create your models here.


class SMSMessage(models.Model):
    to = models.CharField(max_length=15)
    sent_at = models.DateTimeField(auto_now_add=True)
    response = models.JSONField()
