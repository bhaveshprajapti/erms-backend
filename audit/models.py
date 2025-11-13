from django.db import models
from accounts.models import User

class AuditLog(models.Model):
    entity_type = models.CharField(max_length=50)
    entity_id = models.PositiveIntegerField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20)
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['entity_type', 'entity_id', 'created_at'])]

    def __str__(self):
        return f"{self.action} on {self.entity_type} ({self.entity_id}) by {self.user.username if self.user else 'System'}"

