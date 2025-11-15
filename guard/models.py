from django.db import models

class ProtectedEndpoint(models.Model):
    path_matcher = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField()
    status_code = models.IntegerField(default=404)
    
    max_errors = models.IntegerField(default=5)
    window = models.IntegerField(default=900)
    block_duration = models.IntegerField(default=3600)
    
    def __str__(self):
        return self.description
    

class BlockedEndpointHit(models.Model):
    endpoint = models.ForeignKey(
        ProtectedEndpoint,
        on_delete=models.CASCADE,
        related_name="hits",
    )
    
    identifier = models.CharField(max_length=255)
    hit_at = models.DateTimeField(auto_now_add=True)


class BlockedIdentifier(models.Model):
    identifier = models.CharField(max_length=255)
    blocked_at = models.DateTimeField(auto_now_add=True)
    
    reason = models.ForeignKey(
        ProtectedEndpoint,
        on_delete=models.CASCADE,
        related_name="blocks",
    )
    
    disabled_at = models.DateTimeField(null=True, blank=True)
    disabled_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="disabled_blocks",
    )
    

    def __str__(self):
        return self.identifier
    
    