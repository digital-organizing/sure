from django.db import models


class Text(models.Model):
    slug = models.SlugField(primary_key=True)
    context = models.CharField(max_length=100, blank=True)

    content = models.TextField()
    internal = models.BooleanField(default=False)

    def __str__(self):
        return self.slug
