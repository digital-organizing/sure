from django.db import models
from html_sanitizer import Sanitizer


class Text(models.Model):
    slug = models.SlugField(primary_key=True)
    context = models.CharField(max_length=100, blank=True)

    content = models.TextField()
    internal = models.BooleanField(default=False)

    def __str__(self):
        return self.slug

    def save(self, *args, **kwargs):
        sanitizer = Sanitizer({"keep_typographic_whitespace": True})
        self.content = sanitizer.sanitize(self.content)
        super().save(*args, **kwargs)
